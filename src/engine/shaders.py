import os

from OpenGL.GL import *
from OpenGL.GL import shaders


class Shader:
	def __init__(self, vsrc, fsrc, csrc = None):
		path = os.path.dirname(os.path.realpath(__file__)) + "/shaders/"

		with open(path+fsrc, 'r') as fin:
			src = fin.read()
		fragment = shaders.compileShader(src, GL_FRAGMENT_SHADER)
		with open(path+vsrc, 'r') as fin:
			src = fin.read()
		vertex = shaders.compileShader(src, GL_VERTEX_SHADER)
		if csrc:
			with open(path+csrc, 'r') as fin:
				src = fin.read()
				print(src)
			compute = shaders.compileShader(src, GL_COMPUTE_SHADER)
			self.program = shaders.compileProgram(fragment, vertex, compute)
			glDeleteShader(compute)
		else:
			self.program = shaders.compileProgram(fragment, vertex)

		glDeleteShader(fragment)
		glDeleteShader(vertex)

		self._delete_prog = glDeleteProgram

		self.locations = {}

	def __del__(self):
		self._delete_prog(self.program)

	def get_location(self, name):
		if name in self.locations:
			return self.locations[name]

		location = glGetUniformLocation(self.program, name.encode())
		self.locations[name] = location

		return location