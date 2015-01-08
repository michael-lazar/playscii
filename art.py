import json
import numpy as np

from random import randint

# X, Y, Z
VERT_LENGTH = 3
# 4 verts in a quad
VERT_STRIDE = 4 * VERT_LENGTH
# elements: 3 verts per tri * 2 tris in a quad
ELEM_STRIDE = 6
# UVs: 2 floats per vert * 4 verts in a quad
UV_STRIDE = 2 * 4

DEFAULT_FRAME_DELAY = 0.1
DEFAULT_LAYER_Z = 0

class Art:
    
    """
    Art asset:
    Contains the data that is modified by user edits, gets saved and loaded
    from disk. Also contains the arrays that Renderables use to populate
    their buffers.
    
    assumptions:
    - an Art contains 1 or more frames
    - each ArtFrame contains 1 or more layers
    - each ArtLayer contains WxH tiles
    - each tile has a character, foreground color, and background color
    - all layers in an Art are the same dimensions
    """
    
    quad_width,quad_height = 1, 1
    log_size_changes = False
    
    # TODO: argument that provides data loaded from disk? better as a subclass?
    def __init__(self, charset, palette, width, height):
        self.charset, self.palette = charset, palette
        self.width, self.height = width, height
        # TODO: read frame from disk data if it's given
        self.frames = 0
        # list of frame delays
        self.frame_delays = []
        self.layers = 1
        # list of layer Z values
        self.layers_z = [DEFAULT_LAYER_Z]
        # list of char/fg/bg arrays, one for each frame
        self.chars = []
        self.uv_mods = []
        self.fg_colors = []
        self.bg_colors = []
        # add one frame to start (if we're not loading from disk)
        self.add_frame()
        # lists of changed frames, processed each update()
        self.char_changed_frames, self.uv_changed_frames = [], []
        self.fg_changed_frames, self.bg_changed_frames = [], []
        # list of Renderables using us - each new Renderable adds itself
        self.renderables = []
        # tell renderables to rebind vert and element buffers next update
        self.geo_changed = True
        # run update once before renderables initialize so they have
        # something to bind
        self.update()
    
    def add_frame(self, delay=DEFAULT_FRAME_DELAY):
        "adds a blank frame to end of frame sequence"
        self.frames += 1
        self.frame_delays.append(delay)
        tiles = self.layers * self.width * self.height
        blank_array = np.zeros(shape=tiles * 4, dtype=np.float32)
        self.chars.append(blank_array)
        self.fg_colors.append(blank_array.copy())
        self.bg_colors.append(blank_array.copy())
        # UV init is more complex than just all zeroes
        self.uv_mods.append(self.new_uv_layers(self.layers))
        if self.log_size_changes:
            print('frame %s added with %s layers' % (self.frames-1, self.layers))
    
    def duplicate_frame(self, frame_index):
        "adds a duplicate of specified frame to end of frame sequence"
        self.frames += 1
        # copy source frame's delay
        self.frame_delays.append(self.frame_delays[frame_index])
        # copy frame's char/color arrays
        self.chars.append(self.chars[frame_index].copy())
        self.uv_mods.append(self.uv_mods[frame_index].copy())
        self.fg_colors.append(self.fg_colors[frame_index].copy())
        self.bg_colors.append(self.bg_colors[frame_index].copy())
        if self.log_size_changes:
            print('duplicated frame %s as frame %s' % (frame_index, self.frames-1))
    
    def add_layer(self, z=DEFAULT_LAYER_Z):
        "adds a blank layer"
        layer_size = self.width * self.height * 4
        index = self.layers * layer_size
        self.layers += 1
        self.layers_z.append(z)
        # char/color data for all layers in one array, so resize instead
        # of reinitializing
        new_size = index + layer_size
        def expand_array(array, new_size, layer_size, index):
            array.resize(new_size, refcheck=False)
            # populate with "blank" values at appropriate (end) spot
            new_layer_array = np.zeros(shape=layer_size, dtype=np.float32)
            array[index:new_size] = new_layer_array
        for component_list in [self.chars, self.fg_colors, self.bg_colors]:
            for array in component_list:
                expand_array(array, new_size, layer_size, index)
        # UV data: different size, special initialization (2 floats per vert)
        index *= 2
        new_size *= 2
        for array in self.uv_mods:
            array.resize(new_size, refcheck=False)
            new_array = self.new_uv_layers(1)
            array[index:new_size] = new_array
        # adding a layer changes all frames' UV data
        self.uv_changed_frames = range(self.frames)
        if self.log_size_changes:
            print('added layer %s' % (self.layers))
        # rebuild geo with added verts for new layer
        self.geo_changed = True
    
    def clear_frame_layer(self, frame, layer, bg_color=0):
        "clears given layer of given frame to transparent BG + no characters"
        layer_size = self.width * self.height * 4
        index = layer * layer_size
        self.chars[frame][index:index+layer_size] = 0
        # TODO: clear UVs as well once something can modify them, eg rotate/flip
        self.fg_colors[frame][index:index+layer_size] = 0
        self.bg_colors[frame][index:index+layer_size] = bg_color
        # tell this frame to update
        if frame not in self.char_changed_frames:
            self.char_changed_frames.append(frame)
        if frame not in self.fg_changed_frames:
            self.fg_changed_frames.append(frame)
        if frame not in self.bg_changed_frames:
            self.bg_changed_frames.append(frame)
    
    def duplicate_layer(self, layer_index):
        # TODO: duplicate by copying data from specified layer
        pass
    
    def build_geo(self):
        "builds the vertex and element arrays used by all layers"
        tiles = self.layers * self.width * self.height
        all_verts_size = tiles * VERT_STRIDE
        self.vert_array = np.empty(shape=all_verts_size, dtype=np.float32)
        all_elems_size = tiles * ELEM_STRIDE
        self.elem_array = np.empty(shape=all_elems_size, dtype=np.uint32)
        # generate geo according to art size
        # vert_index corresponds to # of verts, loc_index to position in array
        # (given that each vert has 3 components)
        vert_index = 0
        loc_index = 0
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
                    z = self.layers_z[layer]
                    verts = [x0, y0, z]
                    verts += [x1, y1, z]
                    verts += [x2, y2, z]
                    verts += [x3, y3, z]
                    self.vert_array[loc_index:loc_index+VERT_STRIDE] = verts
                    loc_index += VERT_STRIDE
                    # vertex elements
                    elements = [vert_index, vert_index+1, vert_index+2]
                    elements += [vert_index+1, vert_index+2, vert_index+3]
                    self.elem_array[elem_index:elem_index+ELEM_STRIDE] = elements
                    elem_index += ELEM_STRIDE
                    # 4 verts in a quad
                    vert_index += 4
    
    def new_uv_layers(self, layers):
        "returns given # of layer's worth of vanilla UV array data"
        # TODO: support for char rotation/flipping will alter these!
        size = layers * self.width * self.height * UV_STRIDE
        array = np.zeros(shape=size, dtype=np.float32)
        uvs = [0, 0, 1, 0, 0, 1, 1, 1]
        # UV offsets
        index = 0
        while index < size:
            array[index:index+UV_STRIDE] = uvs
            index += UV_STRIDE
        return array
    
    def get_array_index(self, layer, x, y):
        "returns the index into tile array data for a given layer + x + y"
        # multiply by 4 because we store each value for each vert in quad
        return ((layer * self.width * self.height) + (y * self.width) + x) * 4
    
    # get methods
    def get_char_index_at(self, frame, layer, x, y):
        index = self.get_array_index(layer, x, y)
        return self.chars[frame][index]
    
    def get_fg_color_index_at(self, frame, layer, x, y):
        index = self.get_array_index(layer, x, y)
        return self.fg_colors[frame][index]
    
    def get_bg_color_index_at(self, x, y):
        index = self.get_array_index(layer, x, y)
        return self.bg_colors[frame][index]
    
    # set methods
    def set_char_index_at(self, frame, layer, x, y, char_index):
        index = self.get_array_index(layer, x, y)
        self.chars[frame][index:index+4] = char_index
        # next update, tell renderables on the changed frame to update buffers
        if not frame in self.char_changed_frames:
            self.char_changed_frames.append(frame)
    
    def set_color_at(self, frame, layer, x, y, color_index, fg=True):
        # modulo to resolve any negative indices
        color_index %= len(self.palette.colors)
        # no functional differences between fg and bg color update,
        # so use the same code path with different parameters
        update_array = self.fg_colors[frame]
        if not fg:
            update_array = self.bg_colors[frame]
        index = self.get_array_index(layer, x, y)
        update_array[index:index+4] = color_index
        if fg and not frame in self.fg_changed_frames:
            self.fg_changed_frames.append(frame)
        elif not fg and not frame in self.bg_changed_frames:
            self.bg_changed_frames.append(frame)
    
    def set_tile_at(self, frame, layer, x, y, char_index=None, fg=None, bg=None):
        "convenience function for setting (up to) all 3 tile indices at once"
        if char_index:
            self.set_char_index_at(frame, layer, x, y, char_index)
        if fg:
            self.set_color_at(frame, layer, x, y, fg, True)
        if bg:
            self.set_color_at(frame, layer, x, y, bg, False)
    
    def update(self):
        # update our renderables if they're on a frame whose char/colors changed
        if self.geo_changed:
            self.build_geo()
        for r in self.renderables:
            if self.geo_changed:
                r.update_geo_buffers()
                self.geo_changed = False
            do_char = r.frame in self.char_changed_frames
            do_uvs = r.frame in self.uv_changed_frames
            do_fg = r.frame in self.fg_changed_frames
            do_bg = r.frame in self.bg_changed_frames
            r.update_tile_buffers(do_char, do_uvs, do_fg, do_bg)
        # empty lists of changed frames
        self.char_changed_frames, self.uv_changed_frames = [], []
        self.fg_changed_frames, self.bg_changed_frames = [], []
    
    def load_from_file(self, filename):
        data = json.load(open(filename))
        # TODO: turn data into object
    
    def save_to_file(self):
        # TODO: save camera loc/zoom
        # TODO: redo this since overhaul
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
        # clear 1st layer to black, 2nd and 3rd to transparent
        self.clear_frame_layer(0, 0, self.palette.darkest_index)
        self.clear_frame_layer(0, 1)
        self.clear_frame_layer(0, 2)
        # write white text onto 3 layers
        color = self.palette.lightest_index
        self.write_string(0, 0, 1, 1, 'Hello.', color)
        # draw snaky ring thingy
        # color ramp: 4, 10, 9, 15, 5, 16, 6, back to 4
        # top
        self.set_tile_at(0, 1, 1, 3, 119, 4)
        self.set_tile_at(0, 1, 2, 3, 102, 10)
        self.set_tile_at(0, 1, 3, 3, 102, 9)
        self.set_tile_at(0, 1, 4, 3, 102, 15)
        self.set_tile_at(0, 1, 5, 3, 120, 5)
        # sides
        self.set_tile_at(0, 1, 1, 4, 145, 6)
        self.set_tile_at(0, 1, 5, 4, 145, 16)
        self.set_tile_at(0, 1, 1, 5, 145, 16)
        self.set_tile_at(0, 1, 5, 5, 145, 6)
        # bottom
        self.set_tile_at(0, 1, 1, 6, 121, 5)
        self.set_tile_at(0, 1, 2, 6, 102, 15)
        self.set_tile_at(0, 1, 3, 6, 102, 9)
        self.set_tile_at(0, 1, 4, 6, 102, 10)
        self.set_tile_at(0, 1, 5, 6, 122, 4)
        # :]
        char = self.charset.get_char_index(':')
        self.set_tile_at(0, 2, 3, 4, char, color)
        char = self.charset.get_char_index(']')
        self.set_tile_at(0, 2, 4, 4, char, color)
    
    def do_test_animation(self):
        "sets more test data. assumes: 8x8, 3 layers, 6 frames"
        # cycle capitals through "hello" text
        h = self.charset.get_char_index('h')
        char = self.charset.get_char_index('E')
        self.set_char_index_at(1, 0, 2, 1, char)
        self.set_char_index_at(1, 0, 1, 1, h)
        char = self.charset.get_char_index('L')
        self.set_char_index_at(2, 0, 3, 1, char)
        self.set_char_index_at(2, 0, 1, 1, h)
        self.set_char_index_at(3, 0, 4, 1, char)
        self.set_char_index_at(3, 0, 1, 1, h)
        char = self.charset.get_char_index('O')
        self.set_char_index_at(4, 0, 5, 1, char)
        self.set_char_index_at(4, 0, 1, 1, h)
        char = self.charset.get_char_index('!')
        self.set_char_index_at(5, 0, 6, 1, char)
        self.set_char_index_at(5, 0, 1, 1, h)
        self.set_char_index_at(6, 0, 1, 1, h)
        # make smiley go from ;] to :D
        char = self.charset.get_char_index(';')
        self.set_char_index_at(3, 2, 3, 4, char)
        self.set_char_index_at(4, 2, 3, 4, char)
        self.set_char_index_at(5, 2, 3, 4, char)
        char = self.charset.get_char_index('D')
        self.set_char_index_at(3, 2, 4, 4, char)
        self.set_char_index_at(4, 2, 4, 4, char)
        self.set_char_index_at(5, 2, 4, 4, char)
        # cycle colors for snaky thing
        #
        # frame 1 top
        #
        self.set_color_at(1, 1, 1, 3, 10)
        self.set_color_at(1, 1, 2, 3, 9)
        self.set_color_at(1, 1, 3, 3, 15)
        self.set_color_at(1, 1, 4, 3, 5)
        self.set_color_at(1, 1, 5, 3, 16)
        # frame 1 sides
        self.set_color_at(1, 1, 1, 4, 4)
        self.set_color_at(1, 1, 5, 4, 6)
        self.set_color_at(1, 1, 1, 5, 6)
        self.set_color_at(1, 1, 5, 5, 4)
        # frame 1 bottom
        self.set_color_at(1, 1, 1, 6, 16)
        self.set_color_at(1, 1, 2, 6, 5)
        self.set_color_at(1, 1, 3, 6, 15)
        self.set_color_at(1, 1, 4, 6, 9)
        self.set_color_at(1, 1, 5, 6, 10)
        #
        # frame 2 top
        #
        self.set_color_at(2, 1, 1, 3, 9)
        self.set_color_at(2, 1, 2, 3, 15)
        self.set_color_at(2, 1, 3, 3, 5)
        self.set_color_at(2, 1, 4, 3, 16)
        self.set_color_at(2, 1, 5, 3, 6)
        # frame 2 sides
        self.set_color_at(2, 1, 1, 4, 10)
        self.set_color_at(2, 1, 5, 4, 4)
        self.set_color_at(2, 1, 1, 5, 4)
        self.set_color_at(2, 1, 5, 5, 10)
        # frame 2 bottom
        self.set_color_at(2, 1, 1, 6, 6)
        self.set_color_at(2, 1, 2, 6, 16)
        self.set_color_at(2, 1, 3, 6, 5)
        self.set_color_at(2, 1, 4, 6, 15)
        self.set_color_at(2, 1, 5, 6, 9)
        #
        # frame 3 top
        #
        self.set_color_at(3, 1, 1, 3, 15)
        self.set_color_at(3, 1, 2, 3, 5)
        self.set_color_at(3, 1, 3, 3, 16)
        self.set_color_at(3, 1, 4, 3, 6)
        self.set_color_at(3, 1, 5, 3, 4)
        # frame 3 sides
        self.set_color_at(3, 1, 1, 4, 9)
        self.set_color_at(3, 1, 5, 4, 10)
        self.set_color_at(3, 1, 1, 5, 10)
        self.set_color_at(3, 1, 5, 5, 9)
        # frame 3 bottom
        self.set_color_at(3, 1, 1, 6, 4)
        self.set_color_at(3, 1, 2, 6, 6)
        self.set_color_at(3, 1, 3, 6, 16)
        self.set_color_at(3, 1, 4, 6, 5)
        self.set_color_at(3, 1, 5, 6, 15)
        #
        # frame 4 top
        #
        self.set_color_at(4, 1, 1, 3, 5)
        self.set_color_at(4, 1, 2, 3, 16)
        self.set_color_at(4, 1, 3, 3, 6)
        self.set_color_at(4, 1, 4, 3, 4)
        self.set_color_at(4, 1, 5, 3, 10)
        # frame 4 sides
        self.set_color_at(4, 1, 1, 4, 15)
        self.set_color_at(4, 1, 5, 4, 9)
        self.set_color_at(4, 1, 1, 5, 9)
        self.set_color_at(4, 1, 5, 5, 15)
        # frame 4 bottom
        self.set_color_at(4, 1, 1, 6, 10)
        self.set_color_at(4, 1, 2, 6, 4)
        self.set_color_at(4, 1, 3, 6, 6)
        self.set_color_at(4, 1, 4, 6, 16)
        self.set_color_at(4, 1, 5, 6, 5)
        #
        # frame 5 top
        #
        self.set_color_at(5, 1, 1, 3, 16)
        self.set_color_at(5, 1, 2, 3, 6)
        self.set_color_at(5, 1, 3, 3, 4)
        self.set_color_at(5, 1, 4, 3, 10)
        self.set_color_at(5, 1, 5, 3, 9)
        # frame 5 sides
        self.set_color_at(5, 1, 1, 4, 5)
        self.set_color_at(5, 1, 5, 4, 15)
        self.set_color_at(5, 1, 1, 5, 15)
        self.set_color_at(5, 1, 5, 5, 5)
        # frame 5 bottom
        self.set_color_at(5, 1, 1, 6, 9)
        self.set_color_at(5, 1, 2, 6, 10)
        self.set_color_at(5, 1, 3, 6, 4)
        self.set_color_at(5, 1, 4, 6, 6)
        self.set_color_at(5, 1, 5, 6, 16)
        #
        # frame 6 top
        #
        self.set_color_at(6, 1, 1, 3, 6)
        self.set_color_at(6, 1, 2, 3, 4)
        self.set_color_at(6, 1, 3, 3, 10)
        self.set_color_at(6, 1, 4, 3, 9)
        self.set_color_at(6, 1, 5, 3, 15)
        # frame 6 sides
        self.set_color_at(6, 1, 1, 4, 16)
        self.set_color_at(6, 1, 5, 4, 5)
        self.set_color_at(6, 1, 1, 5, 5)
        self.set_color_at(6, 1, 5, 5, 16)
        # frame 6 bottom
        self.set_color_at(6, 1, 1, 6, 15)
        self.set_color_at(6, 1, 2, 6, 9)
        self.set_color_at(6, 1, 3, 6, 10)
        self.set_color_at(6, 1, 4, 6, 4)
        self.set_color_at(6, 1, 5, 6, 6)
    
    def write_string(self, frame, layer, x, y, text, color_index=None):
        "writes out each char of a string to specified tiles"
        x_offset = 0
        for char in text:
            idx = self.charset.get_char_index(char)
            self.set_char_index_at(frame, layer, x+x_offset, y, idx)
            if color_index:
                self.set_color_at(frame, layer, x+x_offset, y, color_index, True)
            x_offset += 1
