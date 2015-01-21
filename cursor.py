import math, ctypes
import numpy as np
from OpenGL import GL

"""
reference diagram:

    0       0.2             0.8      1.0
    A--------B               *--------*
    |        |               |        |
0.1 |  D-----C               *-----*  |
    |  |                           |  |
    |  |                           |  |
0.2 F--E                           *--*

etc
"""

OUTSIDE_EDGE_SIZE = 0.2
THICKNESS = 0.1

corner_verts = [
                    0, 0,                  # A/0
    OUTSIDE_EDGE_SIZE, 0,                  # B/1
    OUTSIDE_EDGE_SIZE, -THICKNESS,         # C/2
            THICKNESS, -THICKNESS,         # D/3
            THICKNESS, -OUTSIDE_EDGE_SIZE, # E/4
                    0, -OUTSIDE_EDGE_SIZE  # F/5
]

# vert indices for the above
corner_elems = [
    0, 1, 2,
    0, 2, 3,
    0, 3, 4,
    0, 5, 4
]

# X/Y flip transforms to make all 4 corners
# (top left, top right, bottom left, bottom right)
corner_transforms = [
    ( 1,  1),
    (-1,  1),
    ( 1, -1),
    (-1, -1)
]

# offsets to translate the 4 corners by
corner_offsets = [
    (0, 0),
    (1, 0),
    (0, -1),
    (1, -1)
]

BASE_COLOR = (0.8, 0.8, 0.8, 1)

# why do we use the weird transforms and offsets?
# because a static vertex list wouldn't be able to adjust to different
# character set aspect ratios.

class Cursor:
    
    vert_shader_source = 'cursor_v.glsl'
    frag_shader_source = 'cursor_f.glsl'
    
    logg = False
    
    def __init__(self, app):
        self.app = app
        self.camera = self.app.camera
        self.x, self.y, self.z = 0, 0, 0
        self.scale_x, self.scale_y, self.scale_z = 1, 1, 1
        # offsets to render the 4 corners at
        self.mouse_x, self.mouse_y = 0, 0
        self.color = np.array(BASE_COLOR, dtype=np.float32)
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
        # vert positions
        self.pos_attrib = self.shader.get_attrib_location('vertPosition')
        GL.glEnableVertexAttribArray(self.pos_attrib)
        offset = ctypes.c_void_p(0)
        GL.glVertexAttribPointer(self.pos_attrib, 2,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, offset)
        # uniforms
        self.proj_matrix_uniform = self.shader.get_uniform_location('projection')
        self.view_matrix_uniform = self.shader.get_uniform_location('view')
        self.position_uniform = self.shader.get_uniform_location('objectPosition')
        self.scale_uniform = self.shader.get_uniform_location('objectScale')
        self.color_uniform = self.shader.get_uniform_location('baseColor')
        self.quad_size_uniform = self.shader.get_uniform_location('quadSize')
        self.xform_uniform = self.shader.get_uniform_location('vertTransform')
        self.offset_uniform = self.shader.get_uniform_location('vertOffset')
        # finish
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)
    
    def move(self, delta_x, delta_y):
        self.x += delta_x
        self.y += delta_y
        if self.logg:
            self.app.log('Cursor: %s,%s,%s scale %.2f,%.2f' % (self.x, self.y, self.z, self.scale_x, self.scale_y))
    
    def get_tile(self):
        return self.x, -self.y
    
    def update(self, elapsed_time):
        self.scale_x = 1.5 + (math.sin(elapsed_time / 100) / 25 - 0.5)
        self.scale_y = self.scale_x
    
    def render(self, elapsed_time):
        GL.glUseProgram(self.shader.program)
        GL.glUniformMatrix4fv(self.proj_matrix_uniform, 1, GL.GL_FALSE, self.camera.projection_matrix)
        GL.glUniformMatrix4fv(self.view_matrix_uniform, 1, GL.GL_FALSE, self.camera.view_matrix)
        GL.glUniform3f(self.position_uniform, self.x, self.y, self.z)
        GL.glUniform3f(self.scale_uniform, self.scale_x, self.scale_y, self.scale_z)
        GL.glUniform4fv(self.color_uniform, 1, self.color)
        GL.glUniform2f(self.quad_size_uniform, self.app.active_art.quad_width, self.app.active_art.quad_height)
        GL.glBindVertexArray(self.vao)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        # draw 4 corners
        for i in range(4):
            tx,ty = corner_transforms[i][0], corner_transforms[i][1]
            ox,oy = corner_offsets[i][0], corner_offsets[i][1]
            GL.glUniform2f(self.xform_uniform, tx, ty)
            GL.glUniform2f(self.offset_uniform, ox, oy)
            GL.glDrawElements(GL.GL_TRIANGLES, self.vert_count,
                              GL.GL_UNSIGNED_INT, self.elem_array)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)
