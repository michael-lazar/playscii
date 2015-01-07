import ctypes
from OpenGL import GL
from art import VERT_LENGTH


class Renderable:
    
    # vertex shader: includes view projection matrix, XYZ camera uniforms
    vert_shader_source = 'renderable_v.glsl'
    # pixel shader: handles FG/BG colors
    frag_shader_source = 'renderable_f.glsl'
    log_animation = False
    log_buffer_updates = False
    
    def __init__(self, app):
        self.app = app
        self.art = self.app.art
        self.art.renderables.append(self)
        # frame of our art's animation we're on
        self.frame = 0
        # world space position
        # TODO: object translation/rotation/scale matrices
        self.x, self.y, self.z = 0, 0, 0
        self.camera = self.app.camera
        # bind VAO etc before doing shaders etc
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.shader = self.app.sl.new_shader(self.vert_shader_source, self.frag_shader_source)
        self.proj_matrix_uniform = self.shader.get_uniform_location('projection')
        self.view_matrix_uniform = self.shader.get_uniform_location('view')
        self.charset_width_uniform = self.shader.get_uniform_location('charMapWidth')
        self.charset_height_uniform = self.shader.get_uniform_location('charMapHeight')
        self.char_uv_width_uniform = self.shader.get_uniform_location('charUVWidth')
        self.char_uv_height_uniform = self.shader.get_uniform_location('charUVHeight')
        self.charset_unit_uniform = self.shader.get_uniform_location('charset')
        #self.palette_unit_uniform = self.shader.get_uniform_location('palette')
        self.create_buffers()
        # finish
        GL.glBindVertexArray(0)
    
    def create_buffers(self):
        # vertex positions and elements
        # determine vertex count needed for render
        self.vert_count = int(len(self.art.elem_array))
        self.vert_buffer, self.elem_buffer = GL.glGenBuffers(2)
        self.update_buffer(self.vert_buffer, self.art.vert_array,
                           GL.GL_ARRAY_BUFFER, GL.GL_STATIC_DRAW, GL.GL_FLOAT, 'vertPosition', VERT_LENGTH)
        self.update_buffer(self.elem_buffer, self.art.elem_array,
                           GL.GL_ELEMENT_ARRAY_BUFFER, GL.GL_STATIC_DRAW, GL.GL_UNSIGNED_INT, None, None)
        # tile data buffers
        # use GL_DYNAMIC_DRAW given they change every time a char/color changes
        self.char_buffer, self.uv_buffer = GL.glGenBuffers(2)
        # character indices (which become vertex UVs)
        self.update_buffer(self.char_buffer, self.art.chars[self.frame],
                           GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW, GL.GL_FLOAT, 'charIndex', 1)
        # UV "mods" - modify UV derived from character index
        self.update_buffer(self.uv_buffer, self.art.uv_mods[self.frame],
                           GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW, GL.GL_FLOAT, 'uvMod', 2)
        #self.fg_buffer, self.bg_buffer = GL.glGenBuffers(2)
        """
        # foreground/background color indices (which become rgba colors)
        self.update_buffer(self.fg_buffer, self.art.fg_colors[self.frame],
                           GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW, GL.GL_FLOAT, 'fgColorIndex', 1)
        self.update_buffer(self.bg_buffer, self.art.bg_colors[self.frame],
                           GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW, GL.GL_FLOAT, 'bgColorIndex', 1)
        """
    
    def update_geo_buffers(self):
        self.update_buffer(self.vert_buffer, self.art.vert_array, GL.GL_ARRAY_BUFFER, GL.GL_STATIC_DRAW, GL.GL_FLOAT, None, None)
        self.update_buffer(self.elem_buffer, self.art.elem_array, GL.GL_ELEMENT_ARRAY_BUFFER, GL.GL_STATIC_DRAW, GL.GL_UNSIGNED_INT, None, None)
        # total vertex count probably changed
        self.vert_count = int(len(self.art.elem_array))
    
    def update_tile_buffers(self, update_chars, update_uvs, update_fg, update_bg):
        updates = {}
        if update_chars:
            updates[self.char_buffer] = self.art.chars
        if update_uvs:
            updates[self.uv_buffer] = self.art.uv_mods
        """
        if update_fg:
            updates[self.fg_buffer] = self.art.fg_colors
        if update_bg:
            updates[self.bg_buffer] = self.art.bg_colors
        """
        for update in updates:
            self.update_buffer(update, updates[update][self.frame],
                               GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW,
                               GL.GL_FLOAT, None, None)
    
    def update_buffer(self, buffer_index, array, target, buffer_type, data_type,
                      attrib_name, attrib_size):
        if self.log_buffer_updates:
            print('update_buffer: %s, %s, %s, %s, %s, %s, %s' % (buffer_index, array, target, buffer_type, data_type, attrib_name, attrib_size))
        GL.glBindBuffer(target, buffer_index)
        GL.glBufferData(target, array.nbytes, array, buffer_type)
        if attrib_name:
            attrib = self.shader.get_attrib_location(attrib_name)
            GL.glEnableVertexAttribArray(attrib)
            GL.glVertexAttribPointer(attrib, attrib_size, data_type,
                                     GL.GL_FALSE, 0, ctypes.c_void_p(0))
        # unbind each buffer before binding next
        GL.glBindBuffer(target, 0)
    
    def advance_frame(self):
        self.set_frame(self.frame + 1)
    
    def rewind_frame(self):
        self.set_frame(self.frame - 1)
    
    def set_frame(self, new_frame_index):
        old_frame = self.frame
        self.frame = new_frame_index % self.art.frames
        self.update_tile_buffers(True, True, True, True)
        if self.log_animation:
            print('%s animating from frames %s to %s' % (self, old_frame, self.frame))
    
    def destroy(self):
        GL.glDeleteVertexArrays(1, [self.vao])
        GL.glDeleteBuffers(3, [self.vert_buffer, self.elem_buffer, self.char_buffer])#, self.fg_buffer, self.bg_buffer])
    
    def render(self, elapsed_time):
        GL.glUseProgram(self.shader.program)
        GL.glUniform1i(self.charset_unit_uniform, 0)
        #GL.glUniform1i(self.palette_unit_uniform, 1)
        GL.glUniform1i(self.charset_width_uniform, self.art.charset.map_width)
        GL.glUniform1i(self.charset_height_uniform, self.art.charset.map_height)
        GL.glUniform1f(self.char_uv_width_uniform, self.art.charset.u_width)
        GL.glUniform1f(self.char_uv_height_uniform, self.art.charset.v_height)
        # camera uniforms
        GL.glUniformMatrix4fv(self.proj_matrix_uniform, 1, GL.GL_FALSE, self.camera.projection_matrix)
        GL.glUniformMatrix4fv(self.view_matrix_uniform, 1, GL.GL_FALSE, self.camera.view_matrix)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.art.charset.texture.gltex)
        #GL.glBindTexture(GL.GL_TEXTURE_2D, self.art.palette.texture.gltex)
        GL.glBindVertexArray(self.vao)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDrawElements(GL.GL_TRIANGLES, self.vert_count,
                          GL.GL_UNSIGNED_INT, self.art.elem_array)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)
