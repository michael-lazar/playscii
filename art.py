import json
import numpy as np
from OpenGL import GL

from random import randint
from random import choice

# 4 verts in a quad
VERT_STRIDE = 4 * self.vert_length
# elements: 3 verts per tri * 2 tris in a quad
ELEM_STRIDE = 6
# uvs: 2 coordinates per vert * 4 verts in a quad
UV_STRIDE = 2 * 4
# colors: 4 channels (RGBA) per vert
COLOR_STRIDE = 4 * 4

class ArtFrame:
    
    "a single animation frame from an Art, containing multiple ArtLayers"
    layer_offset = 0.1
    
    def __init__(self, art, delay=0.1):
        self.art = art
        # time to wait after this frame starts displaying before displaying next
        self.delay = delay
        # initialize with one blank layer
        # TODO: accept data from ArtFromDisk, pass into layer constructor
        self.layers = [ArtLayer(self, 0)]
        self.build_arrays()
    
    def build_arrays(self):
        tiles = len(self.layers) * self.art.width * self.art.height
        all_uvs_size = tiles * UV_STRIDE
        self.uv_array = np.empty(shape=all_uvs_size)
        all_colors_size = tiles * COLOR_STRIDE
        self.fg_color_array = np.empty(shape=all_colors_size)
        self.bg_color_array = np.empty(shape=all_colors_size)
    
    def serialize(self):
        "returns our data in a form that can be easily written to json"
        pass


class ArtLayer:
    
    "a single layer from an ArtFrame, containing char + fg/bg color data"
    
    def __init__(self, frame, z, init_random=False):
        self.frame = frame
        self.art = self.frame.art
        self.z = z
        self.build_lists()
        # TODO: if data loaded from disk is passed from frame, do that instead
    
    def build_lists(self):
        # TODO: ensure assumption that len(frames) = this frame is sound for init
        frame_index = len(self.art.frames)
        layer_index = len(frame.layers)
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
                # add this tile to char, fg and bg color update lists
                tu = TileUpdate(frame_index, layer_index, x, y, new_char_index)
                self.tile_char_updates.append(tu)
                tu.value = new_fg_color
                self.tile_fg_updates.append(tu)
                tu.value = new_bg_color
                self.tile_bg_updates.append(tu)
            self.chars.append(char_line)
            self.fg_colors.append(fg_line)
            self.bg_colors.append(bg_line)


class TileUpdate():
    def __init__(self, frame_index, layer_index, x, y, value):
        # TODO: some cool way to unpack and store these args in one line?
        self.frame_index = frame_index
        self.layer_index = layer_index
        self.x, self.y = x, y
        self.value = value


class Art:
    
    """
    Art asset:
    Contains the data that is modified by user edits, gets saved and loaded
    from disk. Also contains the arrays that Renderables use to populate
    their buffers.
    
    assumptions:
    - an Art contains 1 or more ArtFrames
    - each ArtFrame contains 1 or more ArtLayers
    - each ArtLayer contains WxH tiles
    - each tile has a character, foreground color, and background color
    - all ArtLayers in an Art are the same dimensions
    """
    
    quad_width,quad_height = 1, 1
    vert_length = 3 # X, Y, Z
    
    # TODO: argument that provides data loaded from disk? better as a subclass?
    def __init__(self, charset, palette, width, height):
        self.charset, self.palette = charset, palette
        self.width, self.height = width, height
        # track # of layers here so new frames know how many layers to create
        self.layers = 1
        # initialize char/fg/bg data for 1 frame containing 1 layer
        self.tile_char_updates, self.tile_fg_updates, self.tile_bg_updates = [],[],[]
        # TODO: read frames from disk data if it's given
        self.frames = [ArtFrame(self)]
        # list of Renderables using us - each new Renderable adds itself
        self.renderables = []
        # build vert and element arrays
        self.build_geo()
        # creating new layer will mark all tiles as needing uv/color array updates
        self.update_char_array()
        self.update_color_array(True)
        self.update_color_array(False)
    
    def build_geo(self, z):
        "builds the vertex and element arrays used by all layers"
        tiles = self.layers * self.width * self.height
        all_verts_size = tiles * VERT_STRIDE
        self.vert_array = np.empty(shape=all_verts_size)
        all_elems_size = tiles * ELEM_STRIDE
        self.elem_array = np.empty(shape=all_elems_size)
        # generate geo according to art size
        vert_index = 0
        elem_index = 0
        for layer in range(self.layers):
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
                    verts = [x0, y0, z]
                    verts += [x1, y1, z]
                    verts += [x2, y2, z]
                    verts += [x3, y3, z]
                    self.vert_array[vert_index:vert_index+VERT_STRIDE] = verts
                    vert_index += VERT_STRIDE
                    # vertex elements
                    elements = [elem_index, elem_index+1, elem_index+2]
                    elements += [elem_index+1, elem_index+2, elem_index+3]
                    self.elem_array[elem_index:elem_index+ELEM_STRIDE] = elements
                    elem_index += ELEM_STRIDE
    
    def generate_arraysX(self):
        for tile_y in range(self.height):
            for tile_x in range(self.width):
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
            # TODO: {'dynamic': GL.GL_ARRAY_BUFFER, 'array': GL.GL_ARRAY_BUFFER} etc
            # to remove GL import in Art
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
        return self.fg_colors[y][x]
    
    def get_bg_color_at(self, x, y):
        return self.bg_colors[y][x]
    
    def save_to_file(self):
        savefile = open('dump.json', 'w')
        json.dump(self, savefile)
        # TODO: save char/fg/bg lists (frames w/ layers), charset/palette, size,
        # camera loc/zoom
    
    def update(self):
        # TODO: update everything from lists
        """
        self.tile_char_updates, self.tile_fg_updates, self.tile_bg_updates
        self.update_char_array()
        self.update_color_array(True)
        self.update_color_array(False)
        """
    
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
