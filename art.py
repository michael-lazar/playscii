import json
import numpy as np
from OpenGL import GL

from random import randint
from random import choice


class ArtFrame:
    
    "a single animation frame from an Art, containing multiple ArtLayers"
    layer_offset = 0.1
    
    def __init__(self, art, delay=0.1):
        self.art = art
        # time to wait after this frame starts displaying before displaying next
        self.delay = delay
        self.layers = []
        z = 0
        for i in range(self.art.layers):
            self.layers.append(ArtLayer(self, z))
            z += self.layer_offset
    
    def serialize(self):
        "returns our data in a form that can be easily written to json"
        pass


class ArtLayer:
    
    "a single layer from an ArtFrame, containing char + fg/bg color data"
    
    def __init__(self, frame, z, init_random=False):
        self.art = frame.art
        self.z = z
        self.chars, self.fg_colors, self.bg_colors = [], [], []
        for y in range(self.art.height):
            char_line, fg_line, bg_line = [], [], []
            for x in range(self.art.width):
                new_char_index = 0
                new_fg_color = (1, 1, 1, 1)
                new_bg_color = (0, 0, 0, 1)
                if init_random:
                    new_char_index = randint(0, 255)
                    new_fg_color = choice(self.art.palette.colors)
                    new_bg_color = choice(self.art.palette.colors)
                char_line.append(new_char_index)
                fg_line.append(new_fg_color)
                bg_line.append(new_bg_color)
            self.chars.append(char_line)
            self.fg_colors.append(fg_line)
            self.bg_colors.append(bg_line)


class Art:
    
    quad_width,quad_height = 0.1, 0.1
    vert_length = 3 # X, Y, Z
    
    def __init__(self, charset, palette, width, height):
        self.charset, self.palette = charset, palette
        self.width, self.height = width, height
        # initialize char/fg/bg data: 1 frame containing 1 layer
        self.frames = []
        # track # of layers here so new frames know how many layers to create
        self.layers = 1
        self.frames.append(ArtFrame(self))
        # list of Renderables using us - each new Renderable adds itself
        self.renderables = []
        # generate the geo our renderables will refer to
        self.generate_arrays()
        self.print_test()
    
    def generate_quads(self):
        tiles = len(self.frames) * self.layers * self.width * self.height
        # 4 verts in a quad
        vert_size = tiles * 4 * self.vert_length
        self.vert_array = np.empty(shape=vert_size)
        # elements: 3 verts per tri * 2 tris in a quad
        elem_size = tiles * 6
        self.elem_array = np.empty(shape=elem_size)
        for f,frame in enumerate(self.frames):
            for l,layer in enumerate(frame.layers):
                for tile_y in range(self.height):
                    for tile_x in range(self.width):
                        self.vert_array
                        #self.get_char_index_at(tile_x, tile_y)
                        #self.set_char_index_at(f, l, x, y, 0)
    
    def generate_arrays(self):
        # uvs: 2 coordinates per vert * 4 verts in a quad
        uv_size = tiles * 2 * 4
        self.uv_array = np.empty(shape=uv_size)
        # colors: 4 channels (RGBA) per vert
        color_size = tiles * 4 * 4
        self.fg_color_array = np.empty(shape=color_size)
        self.bg_color_array = np.empty(shape=color_size)
        for f,frame in enumerate(self.frames):
            for layer in frame.layers:
                tile_index = 0
                for tile_y in range(self.height):
                    for tile_x in range(self.width):
                        # vertices
                        left_x = tile_x * self.quad_width
                        top_y = tile_y * -self.quad_height
                        right_x = left_x + self.quad_width
                        bottom_y = top_y - self.quad_height
                        x0,y0 = left_x, top_y
                        x1,y1 = right_x, top_y
                        x2,y2 = left_x, bottom_y
                        x3,y3 = right_x, bottom_y
                        vert_index = tile_index * self.vert_length
                        quad_length = 4 * self.vert_length
                        verts = [x0, y0, layer.z]
                        verts += [x1, y1, layer.z]
                        verts += [x2, y2, layer.z]
                        verts += [x3, y3, layer.z]
                        self.vert_array[vert_index:vert_index+quad_length] = verts
                        # elements
                        elem_index = tile_index * 2
                        elem_length = 3 * 2
                        elems = [tile_index, tile_index+1, tile_index+2]
                        elems += [tile_index+1, tile_index+2, tile_index+3]
                        self.elem_array[elem_index:elem_index+elem_length] = elems
                        # uvs
                        tile_index += 1
    
    def generate_arraysX(self):
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
    def set_char_index_at(self, frame, layer, x, y, char_index):
        self.frames[frame].layers[layer].chars[y][x] = char_index
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
                                     GL.GL_ARRAY_BUFFER, GL.GL_DYNAMIC_DRAW, None, None)
    
    def set_color_at(self, frame, layer, x, y, color, fg=True):
        # no functional differences between fg and bg color update,
        # so use the same code path with different parameters
        update_list = self.frames[frame].layers[layer].fg_colors
        array = self.fg_color_array
        if not fg:
            update_list = self.frames[frame].layers[layer].bg_colors
            array = self.bg_color_array
        update_list[y][x] = color
        r,g,b,a = color[0], color[1], color[2], color[3]
        index = (y * self.width) + x
        index *= 16
        array[index:index+16] = [r,g,b,a, r,g,b,a, r,g,b,a, r,g,b,a]
        for renderable in self.renderables:
            update_buffer = renderable.fg_color_buffer
            if not fg:
                update_buffer = renderable.bg_color_buffer
            renderable.update_buffer(update_buffer, array, GL.GL_ARRAY_BUFFER,
                                     GL.GL_DYNAMIC_DRAW, None, None)
    
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
    
    def save_to_file(self):
        savefile = open('dump.json', 'w')
        json.dump(self, savefile)
        # TODO: save char/fg/bg lists (frames w/ layers), charset/palette, size,
        # camera loc/zoom
    
    def mutate(self):
        "change a random character"
        x = randint(0, self.width-1)
        y = randint(0, self.height-1)
        char = randint(1, 128)
        color = choice(self.palette.colors)
        self.set_char_index_at(0, 0, x, y, char)
        self.set_color_at(0, 0, x, y, color)
        color = choice(self.palette.colors)
        self.set_color_at(0, 0, x, y, color, False)
        self.print_test()
    
    def print_test(self):
        self.set_char_index_at(0, 0, 1, 1, self.charset.get_char_index('H'))
        self.set_char_index_at(0, 0, 2, 1, self.charset.get_char_index('e'))
        self.set_char_index_at(0, 0, 3, 1, self.charset.get_char_index('l'))
        self.set_char_index_at(0, 0, 4, 1, self.charset.get_char_index('l'))
        self.set_char_index_at(0, 0, 5, 1, self.charset.get_char_index('o'))
        self.set_char_index_at(0, 0, 6, 1, self.charset.get_char_index('!'))
