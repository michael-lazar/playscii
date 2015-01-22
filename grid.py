import ctypes
import numpy as np
from OpenGL import GL

# grid that displays as guide for Cursor

AXIS_COLOR = (0.8, 0.8, 0.8, 0.5)
BASE_COLOR = (0.5, 0.5, 0.5, 0.25)
EXTENTS_COLOR = (0, 0, 0, 1)

class Grid:
    
    vert_shader_source = 'grid_v.glsl'
    frag_shader_source = 'grid_f.glsl'
    # squares to show past extents of active Art
    art_margin = 4
    visible = True
    draw_axes = False
    
    def __init__(self, app):
        self.app = app
        self.x, self.y, self.z = 0, 0, 0
        self.scale_x, self.scale_y, self.scale_z = 1, 1, 0
        self.build_geo()
        self.reset_loc()
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.shader = self.app.sl.new_shader(self.vert_shader_source, self.frag_shader_source)
        # uniforms
        self.proj_matrix_uniform = self.shader.get_uniform_location('projection')
        self.view_matrix_uniform = self.shader.get_uniform_location('view')
        self.position_uniform = self.shader.get_uniform_location('objectPosition')
        self.scale_uniform = self.shader.get_uniform_location('objectScale')
        self.quad_size_uniform = self.shader.get_uniform_location('quadSize')
        # vert buffers
        self.vert_buffer, self.elem_buffer = GL.glGenBuffers(2)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vert_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vert_array.nbytes,
                        self.vert_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_array.nbytes,
                        self.elem_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        self.vert_count = int(len(self.elem_array))
        self.pos_attrib = self.shader.get_attrib_location('vertPosition')
        GL.glEnableVertexAttribArray(self.pos_attrib)
        offset = ctypes.c_void_p(0)
        GL.glVertexAttribPointer(self.pos_attrib, 2,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, offset)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        # vert colors
        self.color_buffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.color_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.color_array.nbytes,
                        self.color_array, GL.GL_STATIC_DRAW)
        self.color_attrib = self.shader.get_attrib_location('vertColor')
        GL.glEnableVertexAttribArray(self.color_attrib)
        GL.glVertexAttribPointer(self.color_attrib, 4,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, offset)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)
    
    def build_geo(self):
        "build vert, element, and color arrays for"
        w, h = self.app.ui.active_art.width, self.app.ui.active_art.height
        ew, eh = w + (self.art_margin * 2), h + (self.art_margin * 2)
        # frame
        v = [(0, 0), (ew, 0), (0, -eh), (ew, -eh)]
        e = [0, 1, 1, 3, 3, 2, 2, 0]
        color = EXTENTS_COLOR
        c = color * 4
        index = 4
        # axes - Y and X
        if self.draw_axes:
            v += [(ew/2, -eh), (ew/2, 0), (0, -eh/2), (ew, -eh/2)]
            e += [4, 5, 6, 7]
            color = AXIS_COLOR
            c += color * 4
            index = 8
        # vertical lines
        color = BASE_COLOR
        for x in range(1, ew):
            # skip middle line
            if not self.draw_axes or x != ew/2:
                v += [(x, -eh), (x, 0)]
                e += [index, index+1]
                c += color * 2
                index += 2
        for y in range(1, eh):
            if not self.draw_axes or y != eh/2:
                v += [(0, -y), (ew, -y)]
                e += [index, index+1]
                c += color * 2
                index += 2
        self.vert_array = np.array(v, dtype=np.float32)
        self.elem_array = np.array(e, dtype=np.uint32)
        self.color_array = np.array(c, dtype=np.float32)
    
    def reset_loc(self):
        self.x = -self.art_margin
        self.y = self.art_margin
    
    def rebind_buffers(self):
        # resend verts
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vert_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vert_array.nbytes,
                        self.vert_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_array.nbytes,
                        self.elem_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        self.vert_count = int(len(self.elem_array))
        # resend color
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.color_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.color_array.nbytes,
                        self.color_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
    
    def update(self):
        # TODO: if active_art has changed, adjust position and size accordingly,
        # then self.rebind_buffers()
        pass
    
    def render(self, elapsed_time):
        GL.glUseProgram(self.shader.program)
        GL.glUniformMatrix4fv(self.proj_matrix_uniform, 1, GL.GL_FALSE, self.app.camera.projection_matrix)
        GL.glUniformMatrix4fv(self.view_matrix_uniform, 1, GL.GL_FALSE, self.app.camera.view_matrix)
        GL.glUniform3f(self.position_uniform, self.x, self.y, self.z)
        GL.glUniform3f(self.scale_uniform, self.scale_x, self.scale_y, self.scale_z)
        GL.glUniform2f(self.quad_size_uniform, self.app.ui.active_art.quad_width, self.app.ui.active_art.quad_height)
        GL.glBindVertexArray(self.vao)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDrawElements(GL.GL_LINES, self.vert_count,
                          GL.GL_UNSIGNED_INT, self.elem_array)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)
