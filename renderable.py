import ctypes
from OpenGL import GL

class Renderable:
    
    # TODO: move geo generation out of init so renderables can be resized on the fly
    
    # vertex shader: includes view projection matrix, XYZ camera uniforms
    vert_shader_source = 'renderable_v.glsl'
    # pixel shader: handles FG/BG colors
    frag_shader_source = 'renderable_f.glsl'
    vert_length = 3
    
    def __init__(self, app):
        self.app = app
        self.art = self.app.art
        self.art.renderables.append(self)
        # world space position
        # TODO: translation/rotation/scale matrices
        self.x, self.y, self.z = 0, 0, 0
        self.camera = self.app.camera
        # bind VAO etc before doing shaders etc
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)
        self.shader = self.app.sl.new_shader(self.vert_shader_source, self.frag_shader_source)
        self.tex_unit_uniform = self.shader.get_uniform_location('texUnit')
        self.proj_matrix_uniform = self.shader.get_uniform_location('projection')
        self.view_matrix_uniform = self.shader.get_uniform_location('view')
        #
        # create GL objects
        #
        # determine vertex count for render
        self.vert_count = int(len(self.art.elem_array))
        # vertex positions
        self.vert_buffer = GL.glGenBuffers(1)
        self.update_buffer(self.vert_buffer, self.art.vert_array, GL.GL_ARRAY_BUFFER,
                           GL.GL_STATIC_DRAW, 'vertPosition', self.vert_length)
        # elements
        self.elem_buffer = GL.glGenBuffers(1)
        self.update_buffer(self.elem_buffer, self.art.elem_array,
                           GL.GL_ELEMENT_ARRAY_BUFFER, GL.GL_STATIC_DRAW, None, None)
        # vertex UVs
        self.uv_buffer = GL.glGenBuffers(1)
        # GL_DYNAMIC_DRAW because UVs change every time a char is changed
        self.update_buffer(self.uv_buffer, self.art.uv_array, GL.GL_ARRAY_BUFFER,
                           GL.GL_DYNAMIC_DRAW, 'texCoords', 2)
        # foreground colors
        self.fg_color_buffer = GL.glGenBuffers(1)
        self.update_buffer(self.fg_color_buffer, self.art.fg_color_array, GL.GL_ARRAY_BUFFER,
                           GL.GL_DYNAMIC_DRAW, 'fgColor', 4)
        # background colors
        self.bg_color_buffer = GL.glGenBuffers(1)
        self.update_buffer(self.bg_color_buffer, self.art.bg_color_array, GL.GL_ARRAY_BUFFER,
                           GL.GL_DYNAMIC_DRAW, 'bgColor', 4)
        # finish
        GL.glBindVertexArray(0)
    
    def update_buffer(self, buffer_index, array, target, buffer_type,
                      attrib_name, attrib_size):
        GL.glBindBuffer(target, buffer_index)
        GL.glBufferData(target, array.nbytes, array, buffer_type)
        if attrib_name:
            attrib = self.shader.get_attrib_location(attrib_name)
            GL.glEnableVertexAttribArray(attrib)
            GL.glVertexAttribPointer(attrib, attrib_size, GL.GL_FLOAT,
                                     GL.GL_FALSE, 0, ctypes.c_void_p(0))
        # unbind each buffer before binding next
        GL.glBindBuffer(target, 0)
    
    def destroy(self):
        GL.glDeleteVertexArrays(1, [self.vao])
        GL.glDeleteBuffers(5, [self.vert_buffer, self.elem_buffer, self.uv_buffer, self.fg_color_buffer, self.bg_color_buffer])
    
    def render(self, elapsed_time):
        GL.glUseProgram(self.shader.program)
        GL.glUniform1i(self.tex_unit_uniform, 0)
        # camera uniforms
        GL.glUniformMatrix4fv(self.proj_matrix_uniform, 1, GL.GL_FALSE, self.camera.projection_matrix)
        GL.glUniformMatrix4fv(self.view_matrix_uniform, 1, GL.GL_FALSE, self.camera.view_matrix)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.app.charset.texture.gltex)
        #GL.glBindTexture(GL.GL_TEXTURE_2D, self.app.palette.texture.gltex)
        GL.glBindVertexArray(self.vao)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDrawElements(GL.GL_TRIANGLES, self.vert_count,
                          GL.GL_UNSIGNED_INT, self.art.elem_array)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)
