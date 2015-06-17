import ctypes
import math
import time

import os
import sys
from OpenGL.raw.GL.ARB.internalformat_query2 import GL_TEXTURE_2D

path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(path)

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *
from OpenGL.GL import shaders

from .shaders import Shader


class VERTEX(ctypes.Structure):
	_fields_ = [
		("vx", ctypes.c_float),
		("vy", ctypes.c_float),
		("vz", ctypes.c_float),
		("vw", ctypes.c_float),

		("nx", ctypes.c_float),
		("ny", ctypes.c_float),
		("nz", ctypes.c_float),
		("nw", ctypes.c_float),
	]

	def __repr__(self):
		s = "["
		for field in self._fields_:
			s += str(getattr(self, field[0])) + ", "
		s +="]"
		return s


class TRIANGLE(ctypes.Structure):
	_fields_ = [
		("v0", ctypes.c_uint),
		("v1", ctypes.c_uint),
		("v2", ctypes.c_uint),
		("pad", ctypes.c_uint),
	]

	def __init__(self, v0, v1, v2):
		self.v0 = v0
		self.v1 = v1
		self.v2 = v2


class Mesh:
	__slots__ = ["tri_list", "vert_list"]

	def __init__(self, tri_list, vert_list):
		self.tri_list = tri_list
		self.vert_list = vert_list


def _mat_to_gl(matrix):
	return [i for col in matrix.col for i in col]


class Engine:
	def __init__(self):
		self._scene_texid = glGenTextures(1)
		self._link_list_texid = glGenTextures(1)
		self._counter_texid = glGenTextures(1)

		self._scene_vert_buffer = glGenBuffers(1)
		self._scene_vert_data = (VERTEX * 0)()
		self._scene_tri_buffer = glGenBuffers(1)
		self._scene_tri_data = (TRIANGLE * 0)()
		self._scene_count = 0
		self._scene_dirty = False

		self._meshes = []

		# Setup voxel clear computer shader
		cshader = glCreateShader(GL_COMPUTE_SHADER)
		with open(os.path.dirname(os.path.realpath(__file__)) + "/shaders/comp_clear_voxels.glsl", 'r') as fin:
			src = fin.read()
		comp = shaders.compileShader(src, GL_COMPUTE_SHADER)
		self._shader_prog_clear = shaders.compileProgram(comp)
		glDeleteShader(cshader)

		# Setup voxel grid
		self._voxel_res = 32
		self._voxel_aabb = aabb = ((-8, -8, -8), (8, 8, 8))
		self._voxel_size = (
			aabb[1][0] - aabb[0][0],
			aabb[1][1] - aabb[0][1],
			aabb[1][2] - aabb[0][2]
		)

		glBindTexture(GL_TEXTURE_3D, self._scene_texid)
		glTexImage3D(GL_TEXTURE_3D, 0, GL_R32UI, self._voxel_res, self._voxel_res,
			self._voxel_res, 0, GL_RED_INTEGER, GL_UNSIGNED_INT, None)
		glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
		glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
		glBindTexture(GL_TEXTURE_3D, 0)
		glBindImageTexture(0, self._scene_texid, 0, GL_FALSE, 0, GL_READ_WRITE, GL_R32UI)

		# Setup ray trace shader
		self._shader_fsq = Shader("fsq.vert", "fsq.frag")
		glUseProgram(self._shader_fsq.program)
		loc = self._shader_fsq.get_location("u_res")
		glUniform1f(loc, self._voxel_res)
		loc = self._shader_fsq.get_location("u_size")
		glUniform1f(loc, self._voxel_size[0])
		loc = self._shader_fsq.get_location("u_aabb[0]")
		glUniform3f(loc, *self._voxel_aabb[0])
		loc = self._shader_fsq.get_location("u_aabb[1]")
		glUniform3f(loc, *self._voxel_aabb[1])

		# Setup voxelize computer shader
		cshader = glCreateShader(GL_COMPUTE_SHADER)
		with open(os.path.dirname(os.path.realpath(__file__)) + "/shaders/comp_voxelize.glsl", 'r') as fin:
			src = fin.read()
		comp = shaders.compileShader(src, GL_COMPUTE_SHADER)
		self._shader_prog_voxel = shaders.compileProgram(comp)
		glDeleteShader(cshader)
		glUseProgram(self._shader_prog_voxel)
		loc = glGetUniformLocation(self._shader_prog_voxel, "u_res")
		glUniform1f(loc, self._voxel_res)
		loc = glGetUniformLocation(self._shader_prog_voxel, "u_size")
		glUniform1f(loc, self._voxel_size[0])
		loc = glGetUniformLocation(self._shader_prog_voxel, "u_aabb[0]")
		glUniform3f(loc, *self._voxel_aabb[0])
		loc = glGetUniformLocation(self._shader_prog_voxel, "u_aabb[1]")
		glUniform3f(loc, *self._voxel_aabb[1])

		# Setup texture counter data
		glBindTexture(GL_TEXTURE_2D, self._counter_texid)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_R32UI, 1, 1, 0, GL_RED_INTEGER, GL_UNSIGNED_INT, None)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
		glBindImageTexture(2, self._counter_texid, 0, GL_FALSE, 0, GL_READ_WRITE, GL_R32UI)

		# Setup linked list data
		glBindTexture(GL_TEXTURE_2D, self._link_list_texid)
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RG32UI, 4096, 4096, 0, GL_RG_INTEGER, GL_UNSIGNED_INT, None)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
		glBindImageTexture(1, self._link_list_texid, 0, GL_FALSE, 0, GL_READ_WRITE, GL_RG32UI)

	def __del__(self):
		glDeleteTextures([self._scene_texid])
		glDeleteBuffers(2, [self._scene_tri_buffer, self._scene_vert_buffer])

	def voxelize_scene(self, resolution, half_width):
		# start = time.perf_counter()
		glUseProgram(self._shader_prog_clear)
		glDispatchCompute(resolution, resolution, resolution)
		glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

		data = (ctypes.c_uint32*1)(0)
		glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 1, 1, GL_RED_INTEGER,
						GL_UNSIGNED_INT, data)

		glUseProgram(self._shader_prog_voxel)
		dimension = math.ceil(math.sqrt(self._scene_count))
		loc = glGetUniformLocation(self._shader_prog_voxel, "u_count")
		glUniform1i(loc, self._scene_count)
		glDispatchCompute(dimension, dimension, 1)
		glMemoryBarrier(GL_TEXTURE_FETCH_BARRIER_BIT)

		# glGetTexImage(GL_TEXTURE_2D, 0, GL_RED_INTEGER, GL_UNSIGNED_INT, data)
		# print("Voxelization time: %.2fms\n" % (time.perf_counter() - start) * 1000)
		# print(data[0])

	def add_mesh(self, triangles, vertices):
		mesh = Mesh(triangles, vertices)
		self._meshes.append(mesh)

	def update_scene_buffers(self):
		if len(self._meshes) == 0:
			self._scene_count = 0
			return

		tri_size = vert_size = 0
		for mesh in self._meshes:
			tri_size += ctypes.sizeof(mesh.tri_list)
			vert_size += ctypes.sizeof(mesh.vert_list)
		glBindBuffer(GL_SHADER_STORAGE_BUFFER, self._scene_tri_buffer)
		glBufferData(GL_SHADER_STORAGE_BUFFER, tri_size, None, GL_STREAM_DRAW)
		glBindBuffer(GL_SHADER_STORAGE_BUFFER, self._scene_vert_buffer)
		glBufferData(GL_SHADER_STORAGE_BUFFER, vert_size, None, GL_STREAM_DRAW)

		tri_offset = vert_offset = idx_offset = 0
		for mesh in self._meshes:
			# Tri SSBO
			size = ctypes.sizeof(mesh.tri_list)
			glBindBuffer(GL_SHADER_STORAGE_BUFFER, self._scene_tri_buffer)
			glBufferSubData(GL_SHADER_STORAGE_BUFFER, tri_offset, size, mesh.tri_list)
			tri_offset += size
			for tri in mesh.tri_list:
				tri.pad = idx_offset

			# Vert SSBO
			size = ctypes.sizeof(mesh.vert_list)
			glBindBuffer(GL_SHADER_STORAGE_BUFFER, self._scene_vert_buffer)
			glBufferSubData(GL_SHADER_STORAGE_BUFFER, vert_offset, size, mesh.vert_list)
			vert_offset += size

			idx_offset += len(mesh.vert_list)

		self._scene_count = tri_size // ctypes.sizeof(TRIANGLE)

	def draw(self, view_mat, proj_mat):
		glClearColor(0.2, 0.2, 0.2, 1.0)
		glClear(GL_COLOR_BUFFER_BIT)

		glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self._scene_tri_buffer)
		glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, self._scene_vert_buffer)

		glActiveTexture(GL_TEXTURE0)
		glBindTexture(GL_TEXTURE_3D, self._scene_texid)

		glActiveTexture(GL_TEXTURE1)
		glBindTexture(GL_TEXTURE_2D, self._link_list_texid)

		glActiveTexture(GL_TEXTURE2)
		glBindTexture(GL_TEXTURE_2D, self._counter_texid)

		self.update_scene_buffers()
		self.voxelize_scene(self._voxel_res, self._voxel_size[0])

		glUseProgram(self._shader_fsq.program)

		loc = self._shader_fsq.get_location("view_matrix")
		glUniformMatrix4fv(loc, 1, GL_FALSE, view_mat)

		loc = self._shader_fsq.get_location("proj_matrix")
		glUniformMatrix4fv(loc, 1, GL_FALSE, proj_mat)

		loc = self._shader_fsq.get_location("num_triangles")
		glUniform1i(loc, self._scene_count)

		glBegin(GL_TRIANGLE_STRIP)
		glVertex2i(-1, -1)
		glVertex2i(1, -1)
		glVertex2i(-1, 1)
		glVertex2i(1, 1)
		glEnd()

		glUseProgram(0)
