import time, ctypes
import numpy as np
from OpenGL import GL
from renderable import TileRenderable

class LineRenderable():
    
    "Renderable comprised of GL_LINES"
    
    vert_shader_source = 'lines_v.glsl'
    vert_shader_source_3d = 'lines_3d_v.glsl'
    frag_shader_source = 'lines_f.glsl'
    log_create_destroy = False
    line_width = 1
    # items in vert array: 2 for XY-only renderables, 3 for ones that include Z
    vert_items = 2
    
    def __init__(self, app, quad_size_ref):
        self.app = app
        self.unique_name = '%s_%s' % (int(time.time()), self.__class__.__name__)
        self.quad_size_ref = quad_size_ref
        self.x, self.y, self.z = 0, 0, 0
        self.scale_x, self.scale_y = 1, 1
        # handle Z differently if verts are 2D vs 3D
        self.scale_z = 0 if self.vert_items == 2 else 1
        self.build_geo()
        self.reset_loc()
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        if self.vert_items == 3:
            self.vert_shader_source = self.vert_shader_source_3d
        self.shader = self.app.sl.new_shader(self.vert_shader_source, self.frag_shader_source)
        # uniforms
        self.proj_matrix_uniform = self.shader.get_uniform_location('projection')
        self.view_matrix_uniform = self.shader.get_uniform_location('view')
        self.position_uniform = self.shader.get_uniform_location('objectPosition')
        self.scale_uniform = self.shader.get_uniform_location('objectScale')
        self.quad_size_uniform = self.shader.get_uniform_location('quadSize')
        self.color_uniform = self.shader.get_uniform_location('objectColor')
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
        GL.glVertexAttribPointer(self.pos_attrib, self.vert_items,
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
        if self.log_create_destroy:
            self.app.log('created: %s' % self)
    
    def __str__(self):
        "for debug purposes, return a unique name"
        return self.unique_name
    
    def build_geo(self):
        """
        create self.vert_array, self.elem_array, self.color_array
        """
        pass
    
    def reset_loc(self):
        pass
    
    def set_transform_from_object(self, obj):
        TileRenderable.set_transform_from_object(self, obj)
    
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
    
    def get_projection_matrix(self):
        return np.eye(4, 4)
    
    def get_view_matrix(self):
        return np.eye(4, 4)
    
    def get_quad_size(self):
        return self.quad_size_ref.quad_width, self.quad_size_ref.quad_height
    
    def get_color(self, elapsed_time):
        return (1, 1, 1, 1)
    
    def destroy(self):
        GL.glDeleteVertexArrays(1, [self.vao])
        GL.glDeleteBuffers(3, [self.vert_buffer, self.elem_buffer, self.color_buffer])
        if self.log_create_destroy:
            self.app.log('destroyed: %s' % self)
    
    def render(self):
        GL.glUseProgram(self.shader.program)
        GL.glUniformMatrix4fv(self.proj_matrix_uniform, 1, GL.GL_FALSE, self.get_projection_matrix())
        GL.glUniformMatrix4fv(self.view_matrix_uniform, 1, GL.GL_FALSE, self.get_view_matrix())
        GL.glUniform3f(self.position_uniform, self.x, self.y, self.z)
        GL.glUniform3f(self.scale_uniform, self.scale_x, self.scale_y, self.scale_z)
        GL.glUniform2f(self.quad_size_uniform, *self.get_quad_size())
        GL.glUniform4f(self.color_uniform, *self.get_color(self.app.elapsed_time))
        GL.glBindVertexArray(self.vao)
        # bind elem array - see similar behavior in Cursor.render
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glLineWidth(self.line_width)
        GL.glDrawElements(GL.GL_LINES, self.vert_count,
                          GL.GL_UNSIGNED_INT, None)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)


class UIRenderableX(LineRenderable):
    
    "Red X used to denote transparent color in various places"
    color = (1, 0, 0, 1)
    line_width = 2
    
    def build_geo(self):
        self.vert_array = np.array([(0, 0), (1, 1), (1, 0), (0, 1)], dtype=np.float32)
        self.elem_array = np.array([0, 1, 2, 3], dtype=np.uint32)
        self.color_array = np.array([self.color * 4], dtype=np.float32)


class SwatchSelectionBoxRenderable(LineRenderable):
    
    "used for UI selection boxes etc"
    
    color = (0.5, 0.5, 0.5, 1)
    line_width = 2
    
    def __init__(self, app, quad_size_ref):
        LineRenderable.__init__(self, app, quad_size_ref)
        # track tile X and Y for cursor movement
        self.tile_x, self.tile_y = 0,0
    
    def get_color(self, elapsed_time):
        return self.color
    
    def build_geo(self):
        self.vert_array = np.array([(0, 0), (1, 0), (1, 1), (0, 1)], dtype=np.float32)
        self.elem_array = np.array([0, 1, 1, 2, 2, 3, 3, 0], dtype=np.uint32)
        self.color_array = np.array([self.color * 4], dtype=np.float32)


class OriginIndicatorRenderable(LineRenderable):
    
    "classic 3-axis thingy showing location/rotation/scale"
    
    red   = (1.0, 0.1, 0.1, 1.0)
    green = (0.1, 1.0, 0.1, 1.0)
    blue  = (0.1, 0.1, 1.0, 1.0)
    origin = (0, 0, 0)
    x_axis = (1, 0, 0)
    y_axis = (0, 1, 0)
    z_axis = (0, 0, 1)
    vert_items = 3
    line_width = 3
    
    def __init__(self, app):
        LineRenderable.__init__(self, app, None)
    
    def get_quad_size(self):
        return 1, 1
    
    def get_projection_matrix(self):
        return self.app.camera.projection_matrix
    
    def get_view_matrix(self):
        return self.app.camera.view_matrix
    
    def build_geo(self):
        self.vert_array = np.array([self.origin, self.x_axis,
                                    self.origin, self.y_axis,
                                    self.origin, self.z_axis],
                                    dtype=np.float32)
        self.elem_array = np.array([0, 1, 2, 3, 4, 5], dtype=np.uint32)
        self.color_array = np.array([self.red, self.red, self.green, self.green,
                                     self.blue, self.blue], dtype=np.float32)
