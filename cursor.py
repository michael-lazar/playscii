import ctypes
import numpy as np
from OpenGL import GL

"""
0.2 F--E                           *--*
    |  |                           |  |
    |  |                           |  |
0.1 |  D-----C               *-----*  |
    |        |               |        |
    A--------B               *--------*
    0       0.2             0.8      1.0
"""

corner_verts = [
      0, 0,   # A/0
    0.2, 0,   # B/1
    0.2, 0.1, # C/2
    0.1, 0.1, # D/3
    0.1, 0.2, # E/4
      0, 0.2  # F/5
]

corner_elems = [
    0, 1, 2,
    0, 2, 3,
    0, 3, 4,
    0, 5, 4
]

class Cursor:
    
    vert_shader_source = 'cursor_v.glsl'
    frag_shader_source = 'cursor_f.glsl'
    
    color = np.array([0.8, 0.8, 0.8, 1], dtype=np.float32)
    
    def __init__(self, app):
        self.app = app
        self.camera = self.app.camera
        self.x, self.y, self.z = 0, 0, 0
        self.mouse_x, self.mouse_y = 0, 0
        # GL objects
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.vert_buffer, self.elem_buffer = GL.glGenBuffers(2)
        self.vert_array = np.array(corner_verts, dtype=np.float32)
        self.elem_array = np.array(corner_elems, dtype=np.uint32)
        self.vert_count = int(len(self.elem_array))
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vert_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vert_array.nbytes,
                        self.vert_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_array.nbytes,
                        self.elem_array, GL.GL_STATIC_DRAW)
        # shader, attributes
        self.shader = self.app.sl.new_shader(self.vert_shader_source, self.frag_shader_source)
        self.pos_attrib = self.shader.get_attrib_location('vertPosition')
        GL.glEnableVertexAttribArray(self.pos_attrib)
        offset = ctypes.c_void_p(0)
        GL.glVertexAttribPointer(self.pos_attrib, 2,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, offset)
        # uniforms
        self.proj_matrix_uniform = self.shader.get_uniform_location('projection')
        self.view_matrix_uniform = self.shader.get_uniform_location('view')
        self.position_uniform = self.shader.get_uniform_location('objectPosition')
        self.color_uniform = self.shader.get_uniform_location('baseColor')
        # finish
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)
    
    def update(self, elapsed_time):
        pass
    
    def render(self, elapsed_time):
        GL.glUseProgram(self.shader.program)
        GL.glUniformMatrix4fv(self.proj_matrix_uniform, 1, GL.GL_FALSE, self.camera.projection_matrix)
        GL.glUniformMatrix4fv(self.view_matrix_uniform, 1, GL.GL_FALSE, self.camera.view_matrix)
        GL.glUniform3f(self.position_uniform, self.x, self.y, self.z)
        GL.glUniform4fv(self.color_uniform, 1, self.color)
        GL.glBindVertexArray(self.vao)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDrawElements(GL.GL_TRIANGLES, self.vert_count,
                          GL.GL_UNSIGNED_INT, self.elem_array)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)
