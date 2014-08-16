'''Autogenerated by get_gl_extensions script, do not edit!'''
from OpenGL import platform as _p, constants as _cs, arrays
from OpenGL.GL import glget
import ctypes
EXTENSION_NAME = 'GL_VERSION_GL_3_2'
def _f( function ):
    return _p.createFunction( function,_p.GL,'GL_VERSION_GL_3_2',False)
_p.unpack_constants( """GL_CONTEXT_CORE_PROFILE_BIT 0x1
GL_CONTEXT_COMPATIBILITY_PROFILE_BIT 0x2
GL_LINES_ADJACENCY 0xA
GL_LINE_STRIP_ADJACENCY 0xB
GL_TRIANGLES_ADJACENCY 0xC
GL_TRIANGLE_STRIP_ADJACENCY 0xD
GL_PROGRAM_POINT_SIZE 0x8642
GL_MAX_GEOMETRY_TEXTURE_IMAGE_UNITS 0x8C29
GL_FRAMEBUFFER_ATTACHMENT_LAYERED 0x8DA7
GL_FRAMEBUFFER_INCOMPLETE_LAYER_TARGETS 0x8DA8
GL_GEOMETRY_SHADER 0x8DD9
GL_GEOMETRY_VERTICES_OUT 0x8916
GL_GEOMETRY_INPUT_TYPE 0x8917
GL_GEOMETRY_OUTPUT_TYPE 0x8918
GL_MAX_GEOMETRY_UNIFORM_COMPONENTS 0x8DDF
GL_MAX_GEOMETRY_OUTPUT_VERTICES 0x8DE0
GL_MAX_GEOMETRY_TOTAL_OUTPUT_COMPONENTS 0x8DE1
GL_MAX_VERTEX_OUTPUT_COMPONENTS 0x9122
GL_MAX_GEOMETRY_INPUT_COMPONENTS 0x9123
GL_MAX_GEOMETRY_OUTPUT_COMPONENTS 0x9124
GL_MAX_FRAGMENT_INPUT_COMPONENTS 0x9125
GL_CONTEXT_PROFILE_MASK 0x9126""", globals())
@_f
@_p.types(None,_cs.GLenum,_cs.GLuint,arrays.GLint64Array)
def glGetInteger64i_v( target,index,data ):pass
@_f
@_p.types(None,_cs.GLenum,_cs.GLenum,arrays.GLint64Array)
def glGetBufferParameteri64v( target,pname,params ):pass
@_f
@_p.types(None,_cs.GLenum,_cs.GLenum,_cs.GLuint,_cs.GLint)
def glFramebufferTexture( target,attachment,texture,level ):pass

