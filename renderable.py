import ctypes
import numpy
from OpenGL import GL

class Renderable:
    
    origin_x,origin_y,origin_z = 0, 0, 0
    quad_width,quad_height = 0.1, 0.1
    # vertex shader: includes view projection matrix, XYZ camera uniforms
    vert_shader_source = 'renderable_v.glsl'
    # pixel shader: handles FG/BG colors
    frag_shader_source = 'renderable_f.glsl'
    vert_length = 3
    
    def __init__(self, shader_lord, camera, charset, palette):
        # world space position
        # TODO: translation/rotation/scale matrices
        self.x, self.y, self.z = 0, 0, 0
        self.camera = camera
        # bind VAO etc before doing shaders etc
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.shader = shader_lord.new_shader(self.vert_shader_source, self.frag_shader_source)
