import os


import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GL.ARB.bindless_texture import *


class Voxelizer:
    src_dir = os.path.dirname(os.path.realpath(__file__))

    shader_clear = 0
    shader_voxelize = 0
    shader_voxelize_scene = 0

    tex_counter = 0
    tex_scene_voxel_data = 0
    tex_scene_voxel_list = 0

    scene_aabb = [[0, 0, 0], [0, 0, 0]]
    scene_resolution = [1, 1, 1]

    @classmethod
    def init(cls):
        # Setup voxel clear computer shader
        cshader = glCreateShader(GL_COMPUTE_SHADER)
        src = cls.src_dir + "/shaders/comp_clear_voxels.glsl"
        with open(src, 'r') as fin:
            src = fin.read()
        comp = shaders.compileShader(src, GL_COMPUTE_SHADER)
        cls.shader_clear = shaders.compileProgram(comp)
        glDeleteShader(cshader)

        # Setup voxelize computer shader
        cshader = glCreateShader(GL_COMPUTE_SHADER)
        src = cls.src_dir + "/shaders/comp_voxelize.glsl"
        with open(src, 'r') as fin:
            src = fin.read()
        comp = shaders.compileShader(src, GL_COMPUTE_SHADER)
        cls.shader_voxelize = shaders.compileProgram(comp)
        glDeleteShader(cshader)

        # Setup voxelize scene computer shader
        cshader = glCreateShader(GL_COMPUTE_SHADER)
        src = cls.src_dir + "/shaders/comp_voxelize_scene.glsl"
        with open(src, 'r') as fin:
            src = fin.read()
        comp = shaders.compileShader(src, GL_COMPUTE_SHADER)
        cls.shader_voxelize_scene = shaders.compileProgram(comp)
        glDeleteShader(cshader)

        # Setup texture counter data
        cls.tex_counter = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, cls.tex_counter)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_R32UI, 1, 1, 0, GL_RED_INTEGER,
                        GL_UNSIGNED_INT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glBindTexture(GL_TEXTURE_2D, 0)

        # Setup textures for scene voxel data
        cls.tex_scene_voxel_data, cls.tex_scene_voxel_list = glGenTextures(2)

        glBindTexture(GL_TEXTURE_3D, cls.tex_scene_voxel_data)
        glTexImage3D(GL_TEXTURE_3D, 0, GL_R32UI,
                    cls.scene_resolution[0], cls.scene_resolution[1],
                    cls.scene_resolution[2], 0, GL_RED_INTEGER, GL_UNSIGNED_INT, None)
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        cls.hnd_scene_voxel_data = glGetImageHandleARB(cls.tex_scene_voxel_data, 0,
                                                GL_FALSE, 0, GL_R32UI)
        glMakeImageHandleResidentARB(cls.hnd_scene_voxel_data, GL_READ_WRITE)

        glBindTexture(GL_TEXTURE_2D, cls.tex_scene_voxel_list)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RG32UI, 1024, 1024, 0, GL_RG_INTEGER,
                        GL_UNSIGNED_INT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glBindTexture(GL_TEXTURE_2D, 0)
        cls.hnd_scene_voxel_list = glGetImageHandleARB(cls.tex_scene_voxel_list, 0,
                                                GL_FALSE, 0, GL_RG32UI)
        glMakeImageHandleResidentARB(cls.hnd_scene_voxel_list, GL_READ_WRITE)

    @classmethod
    def voxelize_scene(cls, meshes):
        '''Assumes the mesh buffer is bound to buffer base 0'''
        glBindImageTexture(2, cls.tex_counter, 0, GL_FALSE, 0,
                            GL_READ_WRITE, GL_R32UI)

        glBindTexture(GL_TEXTURE_2D, cls.tex_counter)
        data = (ctypes.c_uint32*1)(0)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 1, 1, GL_RED_INTEGER,
                        GL_UNSIGNED_INT, data)

        glUseProgram(cls.shader_clear)

        loc = glGetUniformLocation(cls.shader_clear, "voxels")
        glUniformHandleui64ARB(loc, cls.hnd_scene_voxel_data)

        glDispatchCompute(*cls.scene_resolution)
        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        mesh_bounds = [mesh.aabb for mesh in meshes]
        cls.scene_aabb[0][0] = min(mesh_bounds, key=lambda b: b[0][0])[0][0] * 1.1
        cls.scene_aabb[0][1] = min(mesh_bounds, key=lambda b: b[0][1])[0][1] * 1.1
        cls.scene_aabb[0][2] = min(mesh_bounds, key=lambda b: b[0][2])[0][2] * 1.1
        cls.scene_aabb[1][0] = max(mesh_bounds, key=lambda b: b[1][0])[1][0] * 1.1
        cls.scene_aabb[1][1] = max(mesh_bounds, key=lambda b: b[1][1])[1][1] * 1.1
        cls.scene_aabb[1][2] = max(mesh_bounds, key=lambda b: b[1][2])[1][2] * 1.1

        dimensions = (
            cls.scene_aabb[1][0] - cls.scene_aabb[0][0],
            cls.scene_aabb[1][1] - cls.scene_aabb[0][1],
            cls.scene_aabb[1][2] - cls.scene_aabb[0][2]
        )

        glUseProgram(cls.shader_voxelize_scene)
        loc = glGetUniformLocation(cls.shader_voxelize_scene, "u_res")
        glUniform3f(loc, *cls.scene_resolution)
        loc = glGetUniformLocation(cls.shader_voxelize_scene, "u_size")
        glUniform3f(loc, *dimensions)
        loc = glGetUniformLocation(cls.shader_voxelize_scene, "u_aabb[0]")
        glUniform3f(loc, *cls.scene_aabb[0])
        loc = glGetUniformLocation(cls.shader_voxelize_scene, "u_aabb[1]")
        glUniform3f(loc, *cls.scene_aabb[1])
        loc = glGetUniformLocation(cls.shader_voxelize_scene, "num_meshes")
        glUniform1i(loc, len(meshes))

        loc = glGetUniformLocation(cls.shader_voxelize_scene, "voxels")
        glUniformHandleui64ARB(loc, cls.hnd_scene_voxel_data)

        loc = glGetUniformLocation(cls.shader_voxelize_scene, "link_list")
        glUniformHandleui64ARB(loc, cls.hnd_scene_voxel_list)

        glDispatchCompute(len(meshes), 1, 1)
        glMemoryBarrier(GL_TEXTURE_FETCH_BARRIER_BIT)

        # glBindTexture(GL_TEXTURE_3D, cls.tex_scene_voxel_data);
        # data = (ctypes.c_uint32*8)()
        # glGetTexImage(GL_TEXTURE_3D, 0, GL_RED_INTEGER, GL_UNSIGNED_INT, data)
        # print('ures:', cls.scene_resolution)
        # print('u_size:', dimensions)
        # print('u_aabb', cls.scene_aabb)
        # print(['END' if i == 4294967295 else i for i in data])

        glUseProgram(0)


    @classmethod
    def voxelize_mesh(cls, mesh):
        # start = time.perf_counter()

        glBindImageTexture(2, cls.tex_counter, 0, GL_FALSE, 0,
                            GL_READ_WRITE, GL_R32UI)

        glBindTexture(GL_TEXTURE_2D, cls.tex_counter)
        data = (ctypes.c_uint32*1)(0)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 1, 1, GL_RED_INTEGER,
                        GL_UNSIGNED_INT, data)

        glUseProgram(cls.shader_clear)

        loc = glGetUniformLocation(cls.shader_clear, "voxels")
        glUniformHandleui64ARB(loc, mesh.hnd_voxel_data)

        glDispatchCompute(*mesh.voxel_resolution)
        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        glUseProgram(cls.shader_voxelize)
        loc = glGetUniformLocation(cls.shader_voxelize, "u_res")
        glUniform3f(loc, *mesh.voxel_resolution)
        loc = glGetUniformLocation(cls.shader_voxelize, "u_size")
        glUniform3f(loc, *mesh.dimensions)
        loc = glGetUniformLocation(cls.shader_voxelize, "u_aabb[0]")
        glUniform3f(loc, *mesh.aabb[0])
        loc = glGetUniformLocation(cls.shader_voxelize, "u_aabb[1]")
        glUniform3f(loc, *mesh.aabb[1])
        loc = glGetUniformLocation(cls.shader_voxelize, "u_count")
        glUniform1i(loc, mesh.count)

        loc = glGetUniformLocation(cls.shader_voxelize, "tri_buffer")
        glUniformHandleui64ARB(loc, mesh.hnd_indices)

        loc = glGetUniformLocation(cls.shader_voxelize, "vert_buffer")
        glUniformHandleui64ARB(loc, mesh.hnd_positions)

        loc = glGetUniformLocation(cls.shader_voxelize, "voxels")
        glUniformHandleui64ARB(loc, mesh.hnd_voxel_data)

        loc = glGetUniformLocation(cls.shader_voxelize, "link_list")
        glUniformHandleui64ARB(loc, mesh.hnd_voxel_list)

        glDispatchCompute(mesh.count, 1, 1)
        glMemoryBarrier(GL_TEXTURE_FETCH_BARRIER_BIT)

        glUseProgram(0)

        # glActiveTexture(GL_TEXTURE2)
        # glGetTexImage(GL_TEXTURE_2D, 0, GL_RED_INTEGER, GL_UNSIGNED_INT, data)
        # print("Voxelization time: %.2fms\n" % (time.perf_counter() - start) * 1000)
        # print(data[0])
