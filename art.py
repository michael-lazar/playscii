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
    log_array_builds = False
    log_tile_updates = False
    
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
    
    def add_layer(self, z):
        self.layers += 1
        for frame in self.frames:
            frame.add_layer(z)
        self.build_geo()
        print('%s now has %s frames %s layers' % (self, len(self.frames), self.layers))
    
    def add_frame(self):
        new_frame = ArtFrame(self)
        self.frames.append(new_frame)
        new_frame.index = len(self.frames) - 1
        print('%s now has %s frames %s layers' % (self, len(self.frames), self.layers))
    
    def duplicate_frame(self, frame_index):
        src = self.frames[frame_index]
        dest = src.copy()
        self.frames.append(dest)
        dest.index = len(self.frames) - 1
    
    def build_geo(self):
        "builds the vertex and element arrays used by all layers"
        tiles = self.layers * self.width * self.height
        all_verts_size = tiles * VERT_STRIDE
        self.vert_array = np.empty(shape=all_verts_size, dtype=np.float32)
        all_elems_size = tiles * ELEM_STRIDE
        self.elem_array = np.empty(shape=all_elems_size, dtype=np.uint32)
        # generate geo according to art size
        loc_index = 0
        # vert index corresponds to # of verts, loc_index to position in
        # array given that each vert has 3 components
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
                    self.vert_array[loc_index:loc_index+VERT_STRIDE] = verts
                    loc_index += VERT_STRIDE
                    # vertex elements
                    elements = [vert_index, vert_index+1, vert_index+2]
                    elements += [vert_index+1, vert_index+2, vert_index+3]
                    self.elem_array[elem_index:elem_index+ELEM_STRIDE] = elements
                    elem_index += ELEM_STRIDE
                    # 4 verts in a quad
                    vert_index += 4
        if self.log_array_builds:
            print('built geo: %s verts, %s elements' % (len(self.vert_array), len(self.elem_array)))
    
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
        if self.log_tile_updates:
            print('setting tile %s:%s:%s,%s to %s' % (frame_index, layer_index, x, y, char_index))
    
    def set_color_at(self, frame_index, layer_index, x, y, color_index, fg=True):
        frame = self.frames[frame_index]
        layer = frame.layers[layer_index]
        # no functional differences between fg and bg color update,
        # so use the same code path with different parameters
        update_list = layer.fg_colors
        if not fg:
            update_list = layer.bg_colors
        # % to resolve any negative indices
        update_list[y][x] = color_index % len(self.palette.colors)
        # mark tile for color array update
        tu = TileUpdate(frame, layer, x, y, color_index)
        if fg:
            self.tile_fg_updates.append(tu)
        else:
            self.tile_bg_updates.append(tu)
        if self.log_tile_updates:
            print('setting tile %s:%s:%s,%s to %s' % (frame_index, layer_index, x, y, color_index))
    
    # get methods
    def get_char_index_at(self, x, y):
        return self.chars[y][x]
    
    def get_fg_color_index_at(self, x, y):
        return self.fg_colors[y][x]
    
    def get_bg_color_index_at(self, x, y):
        return self.bg_colors[y][x]
    
    def load_from_file(self, filename):
        data = json.load(open(filename))
        # TODO: turn data into object
    
    def save_to_file(self):
        # TODO: save camera loc/zoom
        frame_list = []
        for frame in self.frames:
            frame_list.append(frame.get_save_dict())
        d = { 'charset': self.charset.name,
              'palette': self.palette.name,
              'width': self.width,
              'height': self.height,
              'frames': frame_list
        }
        json.dump(d, open('dump.json', 'w'), sort_keys=False, indent=1)
    
    def update(self):
        """
        commit updates from char/color data lists into their respective arrays
        and update renderable buffers accordingly
        """
        for char_update in self.tile_char_updates:
            self.update_char_array(char_update)
        # if any char updates, update renderables' uv buffers
        if len(self.tile_char_updates) > 0:
            if self.log_tile_updates:
                print('%s char updates processed' % len(self.tile_char_updates))
            for r in self.renderables:
                array = self.frames[r.frame].uv_array
                r.quick_update_dynamic_buffer(r.uv_buffer, array)
            # clear update list
            self.tile_char_updates = []
        # same with fg/bg color buffers
        for fg_color_update in self.tile_fg_updates:
            self.update_color_array(fg_color_update, True)
        if len(self.tile_fg_updates) > 0:
            if self.log_tile_updates:
                print('%s fg color updates processed' % len(self.tile_fg_updates))
            for r in self.renderables:
                array = self.frames[r.frame].fg_color_array
                r.quick_update_dynamic_buffer(r.fg_color_buffer, array)
            self.tile_fg_updates = []
        for bg_color_update in self.tile_bg_updates:
            self.update_color_array(bg_color_update, False)
        if len(self.tile_bg_updates) > 0:
            if self.log_tile_updates:
                print('%s bg color updates processed' % len(self.tile_bg_updates))
            for r in self.renderables:
                array = self.frames[r.frame].bg_color_array
                r.quick_update_dynamic_buffer(r.bg_color_buffer, array)
            self.tile_bg_updates = []
    
    def update_char_array(self, update):
        if self.log_tile_updates:
            print('processing char %s' % update)
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
        update.frame.uv_array[uv_index:uv_index+UV_STRIDE] = uvs
    
    def update_color_array(self, update, fg):
        if self.log_tile_updates:
            print('processing %s %s' % (['bg','fg'][fg], update))
        array = update.frame.fg_color_array
        if not fg:
            array = update.frame.bg_color_array
        color = self.palette.colors[update.value]
        r,g,b,a = color[0], color[1], color[2], color[3]
        # index: account for tile position, layer #, and stride
        index = (update.y * self.width) + update.x
        index += update.layer.index * (self.width * self.height)
        index *= COLOR_STRIDE
        array[index:index+COLOR_STRIDE] = [r,g,b,a, r,g,b,a, r,g,b,a, r,g,b,a]
    
    def mutate(self):
        "change a random tile"
        x = randint(0, self.width-1)
        y = randint(0, self.height-1)
        layer = randint(0, self.layers-1)
        char = randint(0, 128)
        color_index = self.palette.get_random_color_index()
        self.set_char_index_at(0, layer, x, y, char)
        self.set_color_at(0, layer, x, y, color_index)
        color_index = self.palette.get_random_color_index()
        self.set_color_at(0, layer, x, y, color_index, False)
    
    def do_test_text(self):
        "sets some test data. assumes: 8x8, 3 layers"
        self.write_string(0, 0, 1, 1, 'hello.')
        self.write_string(0, 1, 1, 3, 'Hello?')
        self.write_string(0, 2, 1, 5, 'HELLO!')
    
    def do_test_animation(self):
        "sets more test data. assumes: 8x8, 3 layers, 4 frames"
        self.set_color_at(0, 0, 1, 1, 3, True)
        self.set_color_at(1, 0, 1, 1, 4, True)
        self.set_color_at(2, 0, 1, 1, 5, True)
        self.set_color_at(3, 0, 1, 1, 6, True)
    
    def write_string(self, frame, layer, x, y, text):
        "writes out each char of a string to specified tiles"
        x_offset = 0
        for char in text:
            idx = self.charset.get_char_index(char)
            self.set_char_index_at(frame, layer, x+x_offset, y, idx)
            x_offset += 1


class ArtFrame:
    
    "a single animation frame from an Art, containing multiple ArtLayers"
    
    def __init__(self, art, delay=0.1, create_layers=True):
        self.art = art
        # index: position in our art's list of frames, important for arrays
        self.index = None
        # time to wait after this frame starts displaying before displaying next
        self.delay = delay
        self.layers = []
        # initialize with one blank layer
        if create_layers:
            if len(self.art.frames) == 0:
                self.add_layer(0)
            else:
                # if we're not the first frame add # of layers other frames have
                for layer in self.art.frames[0].layers:
                    self.add_layer(layer.z)
        self.build_arrays()
        # TODO: if data supplied from ArtFromDisk, pass into layer constructor
        print('%s created with %s layers' % (self, len(self.layers)))
    
    def get_save_dict(self):
        layer_list = []
        for layer in self.layers:
            layer_list.append(layer.get_save_dict())
        d = { 'delay': self.delay,
              'layers': layer_list
        }
        return d
    
    def copy(self):
        # don't create layers for the new frame, we're about to copy em
        new_frame = ArtFrame(self.art, self.delay, False)
        # for deep copy of layers, copy each layer
        for i,layer in enumerate(self.layers):
            new_layer = layer.copy()
            new_layer.index = layer.index
            new_frame.layers.append(new_layer)
        new_frame.build_arrays()
        return new_frame
    
    def add_layer(self, z):
        new_layer = ArtLayer(self, z)
        self.layers.append(new_layer)
        new_layer.index = len(self.layers) - 1
        self.build_arrays()
    
    def build_arrays(self):
        "creates (but does not populate) char/color arrays for this frame"
        tiles = len(self.layers) * self.art.width * self.art.height
        all_uvs_size = tiles * UV_STRIDE
        self.uv_array = np.empty(shape=all_uvs_size, dtype=np.float32)
        all_colors_size = tiles * COLOR_STRIDE
        self.fg_color_array = np.empty(shape=all_colors_size, dtype=np.float32)
        self.bg_color_array = np.empty(shape=all_colors_size, dtype=np.float32)
        if self.art.log_array_builds:
            print('built arrays: %s uvs, %s fg/bg colors' % (len(self.uv_array), len(self.fg_color_array)))
    
    def serialize(self):
        "returns our data in a form that can be easily written to json"
        pass


class ArtLayer:
    
    "a single layer from an ArtFrame, containing char + fg/bg color data"
    
    init_random = False
    
    def __init__(self, frame, z, build_lists=True):
        self.frame = frame
        self.art = self.frame.art
        self.z = z
        if build_lists:
            self.build_lists()
        # index: position in our frame's list of layers, important for arrays
        self.index = None
        # TODO: if data loaded from disk is passed from frame, do that instead
        print('%s created at z %s' % (self, self.z))
    
    def copy(self):
        new_layer = ArtLayer(self.frame, self.z, False) # skip building lists
        new_layer.chars = self.chars[:]
        new_layer.fg_colors = self.fg_colors[:]
        new_layer.bg_colors = self.bg_colors[:]
        new_layer.mark_all_tiles_for_update()
        return new_layer
    
    def mark_all_tiles_for_update(self):
        for y in range(self.art.height):
            for x in range(self.art.width):
                # add this new tile to char, fg and bg color update lists
                tu = TileUpdate(self.frame, self, x, y, self.chars[y][x])
                self.art.tile_char_updates.append(tu)
                tu = TileUpdate(self.frame, self, x, y, self.fg_colors[y][x])
                self.art.tile_fg_updates.append(tu)
                tu = TileUpdate(self.frame, self, x, y, self.bg_colors[y][x])
                self.art.tile_bg_updates.append(tu)
    
    def get_save_dict(self):
        d = { 'z': self.z }
        tiles_list = []
        for y in range(self.art.height):
            new_line = []
            for x in range(self.art.width):
                char = self.chars[y][x]
                fg_color = self.fg_colors[y][x]
                bg_color = self.bg_colors[y][x]
                tile = {'ch': char, 'fg': fg_color, 'bg': bg_color}
                new_line.append(tile)
            tiles_list.append(new_line)
        d['tiles'] = tiles_list
        return d
    
    def build_lists(self):
        "creates and populates lists-of-rows for layer's char and color data"
        self.chars, self.fg_colors, self.bg_colors = [], [], []
        for y in range(self.art.height):
            char_line, fg_line, bg_line = [], [], []
            for x in range(self.art.width):
                new_char_index = 0
                new_fg_color = -1 % len(self.art.palette.colors)
                new_bg_color = 1
                # transparent layer if not the first
                if len(self.frame.layers) > 0:
                    new_bg_color = 0
                # for test purposes, option to randomize everything
                if self.init_random:
                    new_char_index = randint(0, 255)
                    new_fg_color = self.art.palette.get_random_color_index()
                    new_bg_color = self.art.palette.get_random_color_index()
                char_line.append(new_char_index)
                fg_line.append(new_fg_color)
                bg_line.append(new_bg_color)
                # add this new tile to char, fg and bg color update lists
                tu = TileUpdate(self.frame, self, x, y, new_char_index)
                self.art.tile_char_updates.append(tu)
                tu = TileUpdate(self.frame, self, x, y, new_fg_color)
                self.art.tile_fg_updates.append(tu)
                tu = TileUpdate(self.frame, self, x, y, new_bg_color)
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
