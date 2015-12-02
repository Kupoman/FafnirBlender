import ctypes
import math
import struct
import time

import os
import sys

path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(path)

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GL.ARB.bindless_texture import *

from .shaders import Shader
from .gpu_types import *
from .voxelizer import Voxelizer


class Node:
    def __init__(self, model_matrix):
        self.model_matrix = model_matrix
        self.meshes = []


class Mesh:
    def __init__(self, vert_count, element_count, positions, normals, indices):
        self.buf_positions = positions
        self.buf_normals = normals
        self.buf_indices = indices

        self.is_dirty = True

        self.aabb = [
            [0, 0, 0],
            [0, 0, 0]
        ]

        self.aabb[0][0] = min(positions, key=lambda p: p.x).x * 1.001
        self.aabb[0][1] = min(positions, key=lambda p: p.y).y * 1.001
        self.aabb[0][2] = min(positions, key=lambda p: p.z).z * 1.001
        self.aabb[1][0] = max(positions, key=lambda p: p.x).x * 1.001
        self.aabb[1][1] = max(positions, key=lambda p: p.y).y * 1.001
        self.aabb[1][2] = max(positions, key=lambda p: p.z).z * 1.001

        self.dimensions = (
            self.aabb[1][0] - self.aabb[0][0],
            self.aabb[1][1] - self.aabb[0][1],
            self.aabb[1][2] - self.aabb[0][2]
        )

        self.count = element_count // 3

        # Voxels
        res_factor = self.count / (self.dimensions[0] * self.dimensions[1] * self.dimensions[2])
        res_factor = res_factor ** (1/3)
        self.voxel_resolution = (
            math.ceil(self.dimensions[0] * res_factor),
            math.ceil(self.dimensions[1] * res_factor),
            math.ceil(self.dimensions[2] * res_factor),
        )
        self.tex_voxel_data, self.tex_voxel_list = glGenTextures(2)

        glBindTexture(GL_TEXTURE_3D, self.tex_voxel_data)
        glTexImage3D(GL_TEXTURE_3D, 0, GL_R32UI,
                    self.voxel_resolution[0], self.voxel_resolution[1],
                    self.voxel_resolution[2], 0, GL_RED_INTEGER, GL_UNSIGNED_INT,
                    None)
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        self.hnd_voxel_data = glGetImageHandleARB(self.tex_voxel_data, 0,
                                                GL_FALSE, 0, GL_R32UI)
        glMakeImageHandleResidentARB(self.hnd_voxel_data, GL_READ_WRITE)

        glBindTexture(GL_TEXTURE_2D, self.tex_voxel_list)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RG32UI, 1024, 1024, 0, GL_RG_INTEGER,
                        GL_UNSIGNED_INT, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glBindTexture(GL_TEXTURE_2D, 0)
        self.hnd_voxel_list = glGetImageHandleARB(self.tex_voxel_list, 0,
                                                GL_FALSE, 0, GL_RG32UI)
        glMakeImageHandleResidentARB(self.hnd_voxel_list, GL_READ_WRITE)

        # Vertex Data
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo_positions, self.vbo_normals, self.vbo_indices = glGenBuffers(3)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_positions)
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(self.buf_positions),
            self.buf_positions, GL_STATIC_DRAW)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals)
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(self.buf_normals),
            self.buf_normals, GL_STATIC_DRAW)
        glEnableClientState(GL_NORMAL_ARRAY)
        glNormalPointer(GL_FLOAT, 0, ctypes.c_void_p(0))

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vbo_indices)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, ctypes.sizeof(self.buf_indices),
            self.buf_indices, GL_STATIC_DRAW)

        glBindVertexArray(0)

        self.tbo_positions, self.tbo_normals, self.tbo_indices = glGenTextures(3)

        glBindTexture(GL_TEXTURE_BUFFER, self.tbo_positions)
        glTexBuffer(GL_TEXTURE_BUFFER, GL_RGB32F, self.vbo_positions)
        self.hnd_positions = glGetTextureHandleARB(self.tbo_positions)
        glMakeTextureHandleResidentARB(self.hnd_positions)

        glBindTexture(GL_TEXTURE_BUFFER, self.tbo_normals)
        glTexBuffer(GL_TEXTURE_BUFFER, GL_RGB32F, self.vbo_normals)
        self.hnd_normals = glGetTextureHandleARB(self.tbo_normals)
        glMakeTextureHandleResidentARB(self.hnd_normals)

        glBindTexture(GL_TEXTURE_BUFFER, self.tbo_indices)
        glTexBuffer(GL_TEXTURE_BUFFER, GL_R16UI, self.vbo_indices)
        self.hnd_indices = glGetTextureHandleARB(self.tbo_indices)
        glMakeTextureHandleResidentARB(self.hnd_indices)

        glBindTexture(GL_TEXTURE_BUFFER, 0)

        self.gpu_data = GPU_MESH()
        self.gpu_data.voxel_resolution = VEC4(
            self.voxel_resolution[0],
            self.voxel_resolution[1],
            self.voxel_resolution[2],
            self.count
        )
        self.gpu_data.aabb[0] = VEC4(*self.aabb[0])
        self.gpu_data.aabb[1] = VEC4(*self.aabb[1])
        self.gpu_data.voxel_data = self.hnd_voxel_data
        self.gpu_data.voxel_list = self.hnd_voxel_list
        self.gpu_data.tri_buffer = self.hnd_indices
        self.gpu_data.vert_buffer = self.hnd_positions
        self.gpu_data.norm_buffer = self.hnd_normals

    def update_voxels(self):
        if self.is_dirty:
            Voxelizer.voxelize_mesh(self)
            self.is_dirty = False

    def __del__(self):
        print("Delete mesh")
        glDeleteBuffers((
            self.vbo_positions,
            self.vbo_normals,
            self.vbo_indices,
        ))


def _mat_to_gl(matrix):
    return [i for col in matrix.col for i in col]


class Engine:
    def __init__(self):
        self.mesh_buffer = glGenBuffers(1)

        self.draw_width = 1
        self.draw_height = 1

        self._objects = {}
        self._meshes = {}

        Voxelizer.init()

        # Setup ray trace shader
        self._shader_fsq = Shader("fsq.vert", "fsq.frag")
        self.ray_hit_buffer = glGenBuffers(1)

    def __del__(self):
        glDeleteTextures([self._scene_texid])
        glDeleteBuffers(2, [self._scene_tri_buffer, self._scene_vert_buffer])

    def resize(self, width, height):
        self.draw_width = width
        self.draw_height = height

        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ray_hit_buffer)
        glBufferData(GL_SHADER_STORAGE_BUFFER, width*height*ctypes.sizeof(RAY_HIT),
            None, GL_STREAM_DRAW)

        print("Resizing to {} x {}".format(width, height))

    def add_or_update_mesh(self, name, mesh):
        self._meshes[name] = mesh

    def draw(self, width, height, view_mat, proj_mat):
        if self.draw_width != width or self.draw_height != height:
            self.resize(width, height)

        glClearColor(0.2, 0.2, 0.2, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        glMatrixMode(GL_MODELVIEW)
        glLoadMatrixf(view_mat)
        glMatrixMode(GL_PROJECTION)
        glLoadMatrixf(proj_mat)

        for mesh in self._meshes.values():
            mesh.update_voxels()
            glBindVertexArray(mesh.vao)
            # glDrawElements(GL_TRIANGLES, mesh.count, GL_UNSIGNED_SHORT, ctypes.c_void_p(0))

        mesh_count = len(self._meshes.values())
        mesh_data = (GPU_MESH * mesh_count)(
            *[m.gpu_data for m in self._meshes.values()]
        )
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.mesh_buffer)
        glBufferData(GL_SHADER_STORAGE_BUFFER, ctypes.sizeof(GPU_MESH) * mesh_count,
                    mesh_data, GL_STREAM_READ)

        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.mesh_buffer)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self.ray_hit_buffer)

        Voxelizer.voxelize_scene(self._meshes.values())

        glUseProgram(self._shader_fsq.program)

        loc = self._shader_fsq.get_location("out_width")
        glUniform1i(loc, self.draw_width)

        loc = self._shader_fsq.get_location("view_matrix")
        glUniformMatrix4fv(loc, 1, GL_FALSE, view_mat)

        loc = self._shader_fsq.get_location("proj_matrix")
        glUniformMatrix4fv(loc, 1, GL_FALSE, proj_mat)

        loc = self._shader_fsq.get_location("num_meshes")
        glUniform1i(loc, mesh_count)

        loc = self._shader_fsq.get_location("scene_aabb[0]")
        glUniform3f(loc, *Voxelizer.scene_aabb[0])

        loc = self._shader_fsq.get_location("scene_aabb[1]")
        glUniform3f(loc, *Voxelizer.scene_aabb[1])

        loc = self._shader_fsq.get_location("scene_resolution")
        glUniform3f(loc, *Voxelizer.scene_resolution)

        loc = self._shader_fsq.get_location("scene_voxels")
        glUniformHandleui64ARB(loc, Voxelizer.hnd_scene_voxel_data)

        loc = self._shader_fsq.get_location("scene_list")
        glUniformHandleui64ARB(loc, Voxelizer.hnd_scene_voxel_list)

        glBegin(GL_TRIANGLE_STRIP)
        glVertex2i(-1, -1)
        glVertex2i(1, -1)
        glVertex2i(-1, 1)
        glVertex2i(1, 1)
        glEnd()

        glUseProgram(0)
