import json
import numpy as np

from random import randint
from random import choice

# X, Y, Z
VERT_LENGTH = 3
# 4 verts in a quad
VERT_STRIDE = 4 * VERT_LENGTH
# elements: 3 verts per tri * 2 tris in a quad
ELEM_STRIDE = 6
# uvs: 2 coordinates per vert * 4 verts in a quad
UV_STRIDE = 2 * 4
# colors: 4 channels (RGBA) per vert
COLOR_STRIDE = 4 * 4


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
    
    # TODO: argument that provides data loaded from disk? better as a subclass?
    def __init__(self, charset, palette, width, height):
        self.charset, self.palette = charset, palette
        self.width, self.height = width, height
        # track # of layers here so new frames know how many layers to create
        self.layers = 1
        # initialize char/fg/bg data for 1 frame containing 1 layer
        self.tile_char_updates, self.tile_fg_updates, self.tile_bg_updates = [],[],[]
        # TODO: read frames from disk data if it's given
        self.frames = []
        self.add_frame()
        # list of Renderables using us - each new Renderable adds itself
        self.renderables = []
        # build vert and element arrays
        self.build_geo()
        # creating new layer will mark all tiles as needing uv/color array updates
        #self.update()
    
    def add_frame(self):
        new_frame = ArtFrame(self)
        self.frames.append(new_frame)
        new_frame.index = len(self.frames) - 1
    
    def build_geo(self):
        "builds the vertex and element arrays used by all layers"
        tiles = self.layers * self.width * self.height
        all_verts_size = tiles * VERT_STRIDE
        self.vert_array = np.empty(shape=all_verts_size)
        all_elems_size = tiles * ELEM_STRIDE
        self.elem_array = np.empty(shape=all_elems_size)
        # generate geo according to art size
        vert_index = 0
        elem_index = 0
        for layer in self.frames[0].layers:
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
                    verts = [x0, y0, layer.z]
                    verts += [x1, y1, layer.z]
                    verts += [x2, y2, layer.z]
                    verts += [x3, y3, layer.z]
                    self.vert_array[vert_index:vert_index+VERT_STRIDE] = verts
                    vert_index += VERT_STRIDE
                    # vertex elements
                    elements = [elem_index, elem_index+1, elem_index+2]
                    elements += [elem_index+1, elem_index+2, elem_index+3]
                    self.elem_array[elem_index:elem_index+ELEM_STRIDE] = elements
                    elem_index += ELEM_STRIDE
    
    # set methods
    # these set tiles in the internal list format, then mark those tiles
    # for update in the array data used by renderables.
    
    def set_char_index_at(self, frame_index, layer_index, x, y, char_index):
        frame = self.frames[frame_index]
        layer = frame.layers[layer_index]
        layer.chars[y][x] = char_index
        # mark tile for char (UV) array update
        tu = TileUpdate(frame, layer, x, y, char_index)
        self.tile_char_updates.append(tu)
    
    def set_color_at(self, frame_index, layer_index, x, y, color, fg=True):
        frame = self.frames[frame_index]
        layer = frame.layers[layer_index]
        # no functional differences between fg and bg color update,
        # so use the same code path with different parameters
        update_list = layer.fg_colors
        if not fg:
            update_list = layer.bg_colors
        update_list[y][x] = color
        # mark tile for color array update
        tu = TileUpdate(frame, layer, x, y, color)
        if fg:
            self.tile_fg_updates.append(tu)
        else:
            self.tile_bg_updates.append(tu)
    
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
        for char_update in self.tile_char_updates:
            self.update_char_array(char_update)
        # if any char updates, update renderables' uv buffers
        if len(self.tile_char_updates) > 0:
            for r in self.renderables:
                array = self.frames[r.frame].uv_array
                r.update_dynamic_array_buffer(r.uv_buffer, array)
            # clear update list
            self.tile_char_updates = []
        # same with fg/bg color buffers
        for fg_color_update in self.tile_fg_updates:
            self.update_color_array(fg_color_update, True)
        if len(self.tile_fg_updates) > 0:
            for r in self.renderables:
                array = self.frames[r.frame].fg_color_array
                r.update_dynamic_array_buffer(r.fg_color_buffer, array)
            self.tile_fg_updates = []
        for bg_color_update in self.tile_bg_updates:
            self.update_color_array(bg_color_update, False)
        if len(self.tile_bg_updates) > 0:
            for r in self.renderables:
                array = self.frames[r.frame].bg_color_array
                r.update_dynamic_array_buffer(r.bg_color_buffer, array)
            self.tile_bg_updates = []
    
    def update_char_array(self, update):
        #print('processing char %s' % update)
        # get tile value's UVs from sprite data
        u0,v0 = self.charset.get_uvs(update.value)
        u1,v1 = u0 + self.charset.u_width, v0
        u2,v2 = u0, v0 - self.charset.v_height
        u3,v3 = u1, v2
        # XY -> index into 1D list of uvs
        uv_index = (update.y * self.width) + update.x
        # account for layer #
        uv_index += update.layer.index * (self.width * self.height)
        uv_index *= UV_STRIDE
        uvs = [u0, v0, u1, v1, u2, v2, u3, v3]
        #print(update.frame.uv_array)
        update.frame.uv_array[uv_index:uv_index+UV_STRIDE] = uvs
        for renderable in self.renderables:
            renderable.update_buffer(renderable.uv_buffer, update.frame.uv_array, 'array', 'dynamic', None, None)
    
    def update_color_array(self, update, fg):
        #print('processing %s %s' % (['bg','fg'][fg], update))
        array = update.frame.fg_color_array
        if not fg:
            array = update.frame.bg_color_array
        r,g,b,a = update.value[0], update.value[1], update.value[2], update.value[3]
        index = (update.y * self.width) + update.x
        # account for layer #
        index += update.layer.index * (self.width * self.height)
        index *= COLOR_STRIDE
        array[index:index+COLOR_STRIDE] = [r,g,b,a, r,g,b,a, r,g,b,a, r,g,b,a]
    
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
        #self.print_test()
    
    def print_test(self):
        self.set_char_index_at(0, 0, 1, 1, self.charset.get_char_index('H'))
        self.set_char_index_at(0, 0, 2, 1, self.charset.get_char_index('e'))
        self.set_char_index_at(0, 0, 3, 1, self.charset.get_char_index('l'))
        self.set_char_index_at(0, 0, 4, 1, self.charset.get_char_index('l'))
        self.set_char_index_at(0, 0, 5, 1, self.charset.get_char_index('o'))
        self.set_char_index_at(0, 0, 6, 1, self.charset.get_char_index('!'))


class ArtFrame:
    
    "a single animation frame from an Art, containing multiple ArtLayers"
    layer_offset = 0.1
    
    def __init__(self, art, delay=0.1):
        self.art = art
        # index: position in our art's list of frames, important for arrays
        self.index = None
        # time to wait after this frame starts displaying before displaying next
        self.delay = delay
        self.layers = []
        # initialize with one blank layer
        # TODO: if data supplied from ArtFromDisk, pass into layer constructor
        self.add_layer(0)
        self.build_arrays()
    
    def add_layer(self, z):
        new_layer = ArtLayer(self, z)
        self.layers.append(new_layer)
        new_layer.index = len(self.layers) - 1
    
    def build_arrays(self):
        "creates (but does not populate) char/color arrays for this frame"
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
        self.build_lists(init_random)
        # index: position in our frame's list of layers, important for arrays
        self.index = None
        # TODO: if data loaded from disk is passed from frame, do that instead
    
    def build_lists(self, init_random):
        # TODO: ensure assumption that len(frames) = this frame is sound
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
                tu = TileUpdate(self.frame, self, x, y, new_char_index)
                self.art.tile_char_updates.append(tu)
                tu = tu.copy()
                tu.value = new_fg_color
                self.art.tile_fg_updates.append(tu)
                tu = tu.copy()
                tu.value = new_bg_color
                self.art.tile_bg_updates.append(tu)
            self.chars.append(char_line)
            self.fg_colors.append(fg_line)
            self.bg_colors.append(bg_line)


class TileUpdate():
    
    def __init__(self, frame, layer, x, y, value):
        # TODO: some cool way to unpack and store these args in one line?
        self.frame = frame
        self.layer = layer
        self.x, self.y = x, y
        self.value = value
    
    def __str__(self):
        return 'update: frame %s, layer %s, x=%s, y=%s, value=%s' % (self.frame.index, self.layer.index, self.x, self.y, self.value)
    
    def copy(self):
        return TileUpdate(self.frame, self.layer, self.x, self.y, self.value)
