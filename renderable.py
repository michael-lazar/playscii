import ctypes
import numpy as np
from OpenGL import GL

class Renderable:
    
    # TODO: move geo generation out of init so renderables can be resized on the fly
    
    base_x,base_y,base_z = 0, 0, 0
    quad_width,quad_height = 0.1, 0.1
    # vertex shader: includes view projection matrix, XYZ camera uniforms
    vert_shader_source = 'renderable_v.glsl'
    # pixel shader: handles FG/BG colors
    frag_shader_source = 'renderable_f.glsl'
    vert_length = 3
    
    def __init__(self, app):
        self.app = app
        self.art = self.app.art
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
        # generate arrays of verts, elements, and UVs, each in separate buffers
        #
        vert_pos_list = []
        vert_elem_list = []
        vert_uv_list = []
        i = 0
        for tile_y in range(self.art.height):
            for tile_x in range(self.art.width):
                # vertex positions
                left_x = self.base_x + (tile_x * self.quad_width)
                top_y = self.base_y - (tile_y * self.quad_height)
                right_x = left_x + self.quad_width
                bottom_y = top_y - self.quad_height
                x0,y0 = left_x, top_y
                x1,y1 = right_x, top_y
                x2,y2 = left_x, bottom_y
                x3,y3 = right_x, bottom_y
                # vert position format: XYZW (W used only for view projection)
                vert_pos_list += [x0, y0, self.base_z]
                vert_pos_list += [x1, y1, self.base_z]
                vert_pos_list += [x2, y2, self.base_z]
                vert_pos_list += [x3, y3, self.base_z]
                # vertex elements
                vert_elem_list += [  i, i+1, i+2]
                vert_elem_list += [i+1, i+2, i+3]
                i += 4
                # vertex UVs
                # get this tile's value from world data
                char_value = self.art.get_char_at(tile_x, tile_y)
                # get tile value's UVs from sprite data
                u0,v0 = self.app.charset.get_uvs(char_value)
                u1,v1 = u0 + self.app.charset.u_width, v0
                u2,v2 = u0, v0 - self.app.charset.v_height
                u3,v3 = u1, v2
                vert_uv_list += [u0, v0, u1, v1, u2, v2, u3, v3]
        self.vert_pos_array = np.array(vert_pos_list, dtype=np.float32)
        self.vert_elem_array = np.array(vert_elem_list, dtype=np.uint32)
        self.vert_uv_array = np.array(vert_uv_list, dtype=np.float32)
        #
        # create GL objects
        #
        # determine vertex count for render
        self.vert_count = int(len(vert_elem_list))
        # vertex positions
        self.vert_buffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vert_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vert_pos_array.nbytes,
                        self.vert_pos_array, GL.GL_STATIC_DRAW)
        # vertex position attrib
        self.pos_attrib = self.shader.get_attrib_location('vertPosition')
        GL.glEnableVertexAttribArray(self.pos_attrib)
        offset = ctypes.c_void_p(0)
        GL.glVertexAttribPointer(self.pos_attrib, self.vert_length,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, offset)
        # unbind each buffer before binding next
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        # elements
        self.elem_buffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elem_buffer)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, self.vert_elem_array.nbytes,
                        self.vert_elem_array, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        # vertex UVs
        self.uv_buffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.uv_buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vert_uv_array.nbytes,
                        self.vert_uv_array, GL.GL_STATIC_DRAW)
        self.coord_attrib = self.shader.get_attrib_location('texCoords')
        GL.glEnableVertexAttribArray(self.coord_attrib)
        GL.glVertexAttribPointer(self.coord_attrib, 2,
                                 GL.GL_FLOAT, GL.GL_FALSE, 0, offset)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        # finish
        GL.glBindVertexArray(0)
    
    def destroy(self):
        GL.glDeleteVertexArrays(1, [self.vao])
        GL.glDeleteBuffers(3, [self.vert_buffer, self.elem_buffer, self.uv_buffer])
    
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
        # TODO: re-enable once characters show up correctly
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDrawElements(GL.GL_TRIANGLES, self.vert_count,
                          GL.GL_UNSIGNED_INT, self.vert_elem_array)
        GL.glDisable(GL.GL_BLEND)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)
