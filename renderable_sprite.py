import ctypes, time
import numpy as np

from OpenGL import GL
from PIL import Image
from texture import Texture

class SpriteRenderable:
    
    "basic renderable object using an image for a texture"
    
    vert_array = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32)
    vert_shader_source = 'sprite_v.glsl'
    frag_shader_source = 'sprite_f.glsl'
    texture_filename = 'ui/icon.png'
    alpha = 1
    tex_scale_x, tex_scale_y = 1, 1
    blend = True
    flip_y = True
    tex_wrap = False
    
    def __init__(self, app, texture_filename=None, image_data=None):
        self.app = app
        self.unique_name = '%s_%s' % (int(time.time()), self.__class__.__name__)
        self.x, self.y, self.z = self.get_initial_position()
        self.scale_x, self.scale_y, self.scale_z = self.get_initial_scale()
        if self.app.use_vao:
            self.vao = GL.glGenVertexArrays(1)
            GL.glBindVertexArray(self.vao)
        # support loading texture from file or from provided data
        # (remember the filename for later use)
        if texture_filename:
            self.texture_filename = texture_filename
        if not image_data:
            image_data = Image.open(self.texture_filename)
        image_data = image_data.convert('RGBA')
        if self.flip_y:
            image_data = image_data.transpose(Image.FLIP_TOP_BOTTOM)
        w, h = image_data.size
        self.texture = Texture(image_data.tobytes(), w, h)
        self.shader = self.app.sl.new_shader(self.vert_shader_source, self.frag_shader_source)
        self.proj_matrix_uniform = self.shader.get_uniform_location('projection')
        self.view_matrix_uniform = self.shader.get_uniform_location('view')
        self.position_uniform = self.shader.get_uniform_location('objectPosition')
        self.scale_uniform = self.shader.get_uniform_location('objectScale')
        self.tex_uniform = self.shader.get_uniform_location('texture0')
        self.tex_scale_uniform = self.shader.get_uniform_location('texScale')
        self.alpha_uniform = self.shader.get_uniform_location('alpha')
        self.vert_buffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vert_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vert_array.nbytes,
                        self.vert_array, GL.GL_STATIC_DRAW)
        self.vert_count = 4
        self.pos_attrib = self.shader.get_attrib_location('vertPosition')
        GL.glEnableVertexAttribArray(self.pos_attrib)
        offset = ctypes.c_void_p(0)
        GL.glVertexAttribPointer(self.pos_attrib, 2,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, offset)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        if self.app.use_vao:
            GL.glBindVertexArray(0)
        self.texture.set_wrap(self.tex_wrap)
    
    def get_initial_position(self):
        return 0, 0, 0
    
    def get_initial_scale(self):
        return 1, 1, 1
    
    def get_projection_matrix(self):
        return self.app.camera.projection_matrix
    
    def get_view_matrix(self):
        return self.app.camera.view_matrix
    
    def get_texture_scale(self):
        return self.tex_scale_x, self.tex_scale_y
    
    def destroy(self):
        if self.app.use_vao:
            GL.glDeleteVertexArrays(1, [self.vao])
        GL.glDeleteBuffers(1, [self.vert_buffer])
    
    def render(self):
        GL.glUseProgram(self.shader.program)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glUniform1i(self.tex_uniform, 0)
        GL.glUniform2f(self.tex_scale_uniform, *self.get_texture_scale())
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture.gltex)
        GL.glUniformMatrix4fv(self.proj_matrix_uniform, 1, GL.GL_FALSE, self.get_projection_matrix())
        GL.glUniformMatrix4fv(self.view_matrix_uniform, 1, GL.GL_FALSE, self.get_view_matrix())
        GL.glUniform3f(self.position_uniform, self.x, self.y, self.z)
        GL.glUniform3f(self.scale_uniform, self.scale_x, self.scale_y, self.scale_z)
        GL.glUniform1f(self.alpha_uniform, self.alpha)
        if self.app.use_vao:
            GL.glBindVertexArray(self.vao)
        else:
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vert_buffer)
            GL.glVertexAttribPointer(self.pos_attrib, 2,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(0))
            GL.glEnableVertexAttribArray(self.pos_attrib)
        if self.blend:
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, self.vert_count)
        if self.blend:
            GL.glDisable(GL.GL_BLEND)
        if self.app.use_vao:
            GL.glBindVertexArray(0)
        GL.glUseProgram(0)


class UISpriteRenderable(SpriteRenderable):
    
    def get_projection_matrix(self):
        return self.app.ui.view_matrix
    
    def get_view_matrix(self):
        return self.app.ui.view_matrix


class UIBGTextureRenderable(UISpriteRenderable):
    alpha = 0.8
    tex_wrap = True
    texture_filename = 'ui/bgnoise_alpha.png'
    tex_scale_x, tex_scale_y = 8, 8
    
    def get_initial_position(self):
        return -1, -1, 0
    
    def get_initial_scale(self):
        return 2, 2, 1
