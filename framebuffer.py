import numpy as np
from OpenGL import GL


class Framebuffer:
    
    start_crt_enabled = False
    disable_crt = False
    clear_color = (0, 0, 0, 1)
    # declared as an option here in case people want to sub their own via CFG
    crt_fragment_shader_filename = 'framebuffer_f_crt.glsl'
    
    def __init__(self, app, width=None, height=None):
        self.app = app
        self.width, self.height = width or self.app.window_width, height or self.app.window_height
        # bind vao before compiling shaders
        if self.app.use_vao:
            self.vao = GL.glGenVertexArrays(1)
            GL.glBindVertexArray(self.vao)
        self.vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        fb_verts = np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype=np.float32)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, fb_verts.nbytes, fb_verts,
                        GL.GL_STATIC_DRAW)
        # texture, depth buffer, framebuffer
        self.texture = GL.glGenTextures(1)
        self.depth_buffer = GL.glGenRenderbuffers(1)
        self.framebuffer = GL.glGenFramebuffers(1)
        self.setup_texture_and_buffers()
        # shaders
        self.plain_shader = self.app.sl.new_shader('framebuffer_v.glsl', 'framebuffer_f.glsl')
        if not self.disable_crt:
            self.crt_shader = self.app.sl.new_shader('framebuffer_v.glsl', self.crt_fragment_shader_filename)
        self.crt = self.get_crt_enabled()
        # shader uniforms and attributes
        self.plain_tex_uniform = self.plain_shader.get_uniform_location('fbo_texture')
        self.plain_attrib = self.plain_shader.get_attrib_location('v_coord')
        GL.glEnableVertexAttribArray(self.plain_attrib)
        GL.glVertexAttribPointer(self.plain_attrib, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
        if not self.disable_crt:
            self.crt_tex_uniform = self.crt_shader.get_uniform_location('fbo_texture')
            self.crt_time_uniform = self.crt_shader.get_uniform_location('elapsed_time')
            self.crt_res_uniform = self.crt_shader.get_uniform_location('resolution')
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        if self.app.use_vao:
            GL.glBindVertexArray(0)
    
    def get_crt_enabled(self):
        return self.disable_crt or self.start_crt_enabled
    
    def setup_texture_and_buffers(self):
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)
        GL.glTexParameterf(GL.GL_TEXTURE_2D,
                           GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameterf(GL.GL_TEXTURE_2D,
                           GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameterf(GL.GL_TEXTURE_2D,
                           GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameterf(GL.GL_TEXTURE_2D,
                           GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA,
                        self.width, self.height, 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, self.depth_buffer)
        GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_DEPTH_COMPONENT16,
                                 self.width, self.height)
        GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, 0)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.framebuffer)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0,
                                  GL.GL_TEXTURE_2D, self.texture, 0)
        GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT,
                                     GL.GL_RENDERBUFFER, self.depth_buffer)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
    
    def resize(self, new_width, new_height):
        self.width, self.height = new_width, new_height
        self.setup_texture_and_buffers()
    
    def toggle_crt(self):
        self.crt = not self.crt
    
    def destroy(self):
        if self.app.use_vao:
            GL.glDeleteVertexArrays(1, [self.vao])
        GL.glDeleteBuffers(1, [self.vbo])
        GL.glDeleteRenderbuffers(1, [self.depth_buffer])
        GL.glDeleteTextures([self.texture])
        GL.glDeleteFramebuffers(1, [self.framebuffer])
    
    def render(self):
        if self.crt and not self.disable_crt:
            GL.glUseProgram(self.crt_shader.program)
            GL.glUniform1i(self.crt_tex_uniform, 0)
            GL.glUniform2f(self.crt_res_uniform, self.width, self.height)
            GL.glUniform1f(self.crt_time_uniform, self.app.get_elapsed_time())
        else:
            GL.glUseProgram(self.plain_shader.program)
            GL.glUniform1i(self.plain_tex_uniform, 0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)
        GL.glClearColor(*self.clear_color)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        # VAO vs non-VAO paths
        if self.app.use_vao:
            GL.glBindVertexArray(self.vao)
        else:
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
            GL.glVertexAttribPointer(self.plain_attrib, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            GL.glEnableVertexAttribArray(self.plain_attrib)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        if self.app.use_vao:
            GL.glBindVertexArray(0)
        GL.glUseProgram(0)


class ExportFramebuffer(Framebuffer):
    clear_color = (0, 0, 0, 0)
    def get_crt_enabled(self): return True


class ExportFramebufferNoCRT(Framebuffer):
    clear_color = (0, 0, 0, 0)
    def get_crt_enabled(self): return False
