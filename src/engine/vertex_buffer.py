import ctypes


import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *

from .gpu_types import VERTEX


class VertexBuffer:
    def __init__(self,):
        self.vbo, self.ibo = glGenBuffers(2)
        self.mesh_list = []
        self.is_dirty = True
        self.vertex_count = 0
        self.element_count = 0
        self.vbo_size = 0
        self._resize_vbo(0)
        self.ibo_size = 0
        self._resize_ibo(0)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ibo)
        glEnableVertexAttribArray(0)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, ctypes.sizeof(VERTEX), ctypes.c_void_p(0))
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, ctypes.sizeof(VERTEX), ctypes.c_void_p(16))
        glBindVertexArray(0)

    def add_mesh(self, mesh):
        self.vertex_count += mesh.vert_count
        self.element_count += mesh.element_count
        self.mesh_list.append(mesh)
        self.is_dirty = True

    def remove_mesh(self, mesh):
        pass

    def _resize_vbo(self, size):
        self.vbo_size = size
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, size, ctypes.c_void_p(0), GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def _resize_ibo(self, size):
        self.ibo_size = size
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ibo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, size, ctypes.c_void_p(0), GL_STATIC_DRAW)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def update(self):
        if not self.is_dirty:
            return

        if self.vbo_size < self.vertex_count * ctypes.sizeof(VERTEX):
            self._resize_vbo(self.vertex_count * ctypes.sizeof(VERTEX))

        if self.ibo_size < self.element_count * ctypes.sizeof(ctypes.c_uint32):
            self._resize_ibo(self.element_count * ctypes.sizeof(ctypes.c_uint32))

        vert_index = 0
        element_index = 0
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ibo)
        for mesh in self.mesh_list:
            c_buffer = (VERTEX * mesh.vert_count)()
            for i, data in enumerate(zip(mesh.buf_positions, mesh.buf_normals)):
                c_buffer[i].vx = data[0].x
                c_buffer[i].vy = data[0].y
                c_buffer[i].vz = data[0].z
                c_buffer[i].nx = data[1].x
                c_buffer[i].ny = data[1].y
                c_buffer[i].nz = data[1].z
            glBufferSubData(GL_ARRAY_BUFFER, vert_index * ctypes.sizeof(VERTEX),
                mesh.vert_count * ctypes.sizeof(VERTEX), c_buffer)
            mesh.gpu_data.vert_offset = vert_index
            vert_index += mesh.vert_count

            c_buffer = (ctypes.c_uint32 * mesh.element_count)(
                *[ctypes.c_uint32(i) for i in mesh.buf_indices]
            )
            glBufferSubData(GL_ELEMENT_ARRAY_BUFFER, element_index * ctypes.sizeof(ctypes.c_uint32),
                ctypes.sizeof(c_buffer), c_buffer)
            mesh.gpu_data.element_offset = element_index;
            element_index += mesh.element_count

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        self.is_dirty = False

    def bind(self, vertex_location, element_location):
        glBindVertexArray(self.vao)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, vertex_location, self.vbo)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, element_location, self.ibo)
