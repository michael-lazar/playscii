import numpy as np
from OpenGL import GL

from random import randint
from random import choice

class Art:
    
    init_random = True
    quad_width,quad_height = 0.1, 0.1
    
    def __init__(self, charset, palette, width, height):
        # list of Renderables using us - each Renderable adds itself
        self.renderables = []
        self.charset, self.palette = charset, palette
        self.width, self.height = width, height
        # initialize char table
        # TODO: finalize decision that list-of-row-lists is best format
        self.chars, self.fg_colors, self.bg_colors = [], [], []
        for y in range(self.height):
            char_line, fg_line, bg_line = [], [], []
            for x in range(self.width):
                new_char_index = 0
                new_fg_color = (1, 1, 1, 1)
                new_bg_color = (0, 0, 0, 1)
                if self.init_random:
                    new_char_index = randint(0, 255)
                    new_fg_color = choice(self.palette.colors)
                    new_bg_color = choice(self.palette.colors)
                char_line.append(new_char_index)
                fg_line.append(new_fg_color)
                bg_line.append(new_bg_color)
            self.chars.append(char_line)
            self.fg_colors.append(fg_line)
            self.bg_colors.append(bg_line)
        # generate the geo our renderables will refer to
        self.generate_arrays()
        # test stuff
        self.set_char_index_at(1, 1, self.charset.get_char_index('H'))
        self.set_char_index_at(2, 1, self.charset.get_char_index('e'))
        self.set_char_index_at(3, 1, self.charset.get_char_index('l'))
        self.set_char_index_at(4, 1, self.charset.get_char_index('l'))
        self.set_char_index_at(5, 1, self.charset.get_char_index('o'))
        self.set_char_index_at(6, 1, self.charset.get_char_index('!'))
    
    def generate_arrays(self):
        vert_list = []
        elem_list = []
        uv_list = []
        fg_color_list = []
        bg_color_list = []
        i = 0
        for tile_y in range(self.height):
            for tile_x in range(self.width):
                # TODO: create blank arrays and set their contents directly!
                # vertex positions
                left_x = tile_x * self.quad_width
                top_y = tile_y * -self.quad_height
                right_x = left_x + self.quad_width
                bottom_y = top_y - self.quad_height
                x0,y0 = left_x, top_y
                x1,y1 = right_x, top_y
                x2,y2 = left_x, bottom_y
                x3,y3 = right_x, bottom_y
                # vert position format: XYZW (W used only for view projection)
                # TODO: set different base_z depening on layer
                vert_list += [x0, y0, 0]
                vert_list += [x1, y1, 0]
                vert_list += [x2, y2, 0]
                vert_list += [x3, y3, 0]
                # vertex elements
                elem_list += [  i, i+1, i+2]
                elem_list += [i+1, i+2, i+3]
                i += 4
                # vertex UVs
                # get this tile's value from world data
                char_value = self.get_char_index_at(tile_x, tile_y)
                # get tile value's UVs from sprite data
                u0,v0 = self.charset.get_uvs(char_value)
                u1,v1 = u0 + self.charset.u_width, v0
                u2,v2 = u0, v0 - self.charset.v_height
                u3,v3 = u1, v2
                uv_list += [u0, v0, u1, v1, u2, v2, u3, v3]
                # get fg and bg colors
                fg_color = self.get_fg_color_at(tile_x, tile_y)
                # add color for each vertex
                # TODO: determine if this is too wasteful / bad for perf
                fg_color_list += [fg_color, fg_color, fg_color, fg_color]
                bg_color = self.get_bg_color_at(tile_x, tile_y)
                bg_color_list += [bg_color, bg_color, bg_color, bg_color]
        self.vert_array = np.array(vert_list, dtype=np.float32)
        self.elem_array = np.array(elem_list, dtype=np.uint32)
        self.uv_array = np.array(uv_list, dtype=np.float32)
        self.fg_color_array = np.array(fg_color_list, dtype=np.float32)
        self.bg_color_array = np.array(bg_color_list, dtype=np.float32)
    
    # set methods
    def set_char_index_at(self, x, y, char_index):
        self.chars[y][x] = char_index
        # get tile value's UVs from sprite data
        u0,v0 = self.charset.get_uvs(char_index)
        u1,v1 = u0 + self.charset.u_width, v0
        u2,v2 = u0, v0 - self.charset.v_height
        u3,v3 = u1, v2
        # XY -> index into 1D list of uvs
        uv_index = (y * self.width) + x
        uv_index *= 8
        self.uv_array[uv_index:uv_index+8] = [u0, v0, u1, v1, u2, v2, u3, v3]
        for renderable in self.renderables:
            renderable.update_buffer(renderable.uv_buffer, self.uv_array,
                                     GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW,
                                     None, None)
    
    # get methods
    def get_char_index_at(self, x, y):
        return self.chars[y][x]
    
    def get_fg_color_at(self, x, y):
        # TODO: where's the best place to convert colors from tuple of bytes
        # to tuple of normalized floats?
        # probably palette init so we never have to worry about it again
        c = self.fg_colors[y][x]
        return (c[0] / 255, c[1] / 255, c[2] / 255, c[3] / 255)
    
    def get_bg_color_at(self, x, y):
        c = self.bg_colors[y][x]
        return (c[0] / 255, c[1] / 255, c[2] / 255, c[3] / 255)
    
    def mutate(self):
        "change a random character"
        x = randint(0, self.width-1)
        y = randint(0, self.height-1)
        char = randint(1, 128)
        #color = self.palette(
        self.set_char_index_at(x, y, char)
