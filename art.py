import os.path, json
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

ART_DIR = 'art/'
ART_FILE_EXTENSION = 'psci'

SCRIPT_DIR = 'scripts/'
SCRIPT_FILE_EXTENSION = 'arsc'

# flip/rotate UV constants
UV_NORMAL = 0
UV_ROTATE90 = 1
UV_ROTATE180 = 2
UV_ROTATE270 = 3
UV_FLIPX = 4
UV_FLIPY = 5
# flip X & Y is identical to rotate 180

uv_types = {
    UV_NORMAL:    (0, 0, 1, 0, 0, 1, 1, 1),
    UV_ROTATE90:  (0, 1, 0, 0, 1, 1, 1, 0),
    UV_ROTATE180: (1, 1, 0, 1, 1, 0, 0, 0),
    UV_ROTATE270: (1, 0, 1, 1, 0, 0, 0, 1),
    UV_FLIPX:     (1, 0, 0, 0, 1, 1, 0, 1),
    UV_FLIPY:     (0, 1, 1, 1, 0, 0, 1, 0)
}

# reverse dict for easy (+ fast?) lookup in eg get_char_transform_at
uv_types_reverse = {
    uv_types[UV_NORMAL]: UV_NORMAL,
    uv_types[UV_ROTATE90]: UV_ROTATE90,
    uv_types[UV_ROTATE180]: UV_ROTATE180,
    uv_types[UV_ROTATE270]: UV_ROTATE270,
    uv_types[UV_FLIPX]: UV_FLIPX,
    uv_types[UV_FLIPY]: UV_FLIPY
}

class Art:
    """
    Art asset:
    Contains the data that is modified by user edits and gets saved to disk.
    Data stored as arrays that TileRenderables use to populate their buffers.
    
    assumptions:
    - an Art contains 1 or more frames
    - each frame contains 1 or more layers
    - each layer contains WxH tiles
    - each tile has a character, foreground color, and background color
    - all layers in an Art are the same dimensions
    """
    quad_width,quad_height = 1, 1
    log_size_changes = False
    recalc_quad_height = True
    log_creation = True
    # avoid writing to characters out of bounds in write_string -
    # used for debug
    write_string_range_check = False
    
    def __init__(self, filename, app, charset, palette, width, height):
        "creates a new, blank document"
        if filename and not filename.endswith('.%s' % ART_FILE_EXTENSION):
            filename += '.%s' % ART_FILE_EXTENSION
        self.filename = filename
        self.app = app
        self.charset, self.palette = charset, palette
        self.width, self.height = width, height
        self.frames = 0
        # list of frame delays
        self.frame_delays = []
        self.layers = 1
        # list of layer Z values
        self.layers_z = [DEFAULT_LAYER_Z]
        # list of char/fg/bg arrays, one for each frame
        self.chars, self.uv_mods, self.fg_colors, self.bg_colors = [],[],[],[]
        # add one frame to start
        self.add_frame()
        # lists of changed frames, processed each update()
        self.char_changed_frames, self.uv_changed_frames = [], []
        self.fg_changed_frames, self.bg_changed_frames = [], []
        # clear our single layer to a sensible BG color
        self.clear_frame_layer(0, 0, bg_color=self.palette.darkest_index)
        # support non-square characters:
        # derive quad_height from chars aspect; quad_width always 1.0
        if self.recalc_quad_height:
            self.quad_height *= self.charset.char_height / self.charset.char_width
        # list of TileRenderables using us - each new Renderable adds itself
        self.renderables = []
        # running scripts and timing info
        self.scripts = []
        self.script_rates = []
        self.scripts_next_exec_time = []
        # tell renderables to rebind vert and element buffers next update
        self.geo_changed = True
        # run update once before renderables initialize so they have
        # something to bind
        self.update()
        if self.log_creation:
            self.app.log('created new document:')
            self.app.log('  character set: %s' % self.charset.name)
            self.app.log('  palette: %s' % self.palette.name)
            self.app.log('  width/height: %s x %s' % (self.width, self.height))
            self.app.log('  frames: %s' % self.frames)
            self.app.log('  layers: %s' % self.layers)
    
    def add_frame(self, delay=DEFAULT_FRAME_DELAY):
        "adds a blank frame to end of frame sequence"
        self.frames += 1
        self.frame_delays.append(delay)
        tiles = self.layers * self.width * self.height
        shape = (self.layers, self.height, self.width, 4)
        blank_array = np.zeros(shape, dtype=np.float32)
        self.chars.append(blank_array)
        self.fg_colors.append(blank_array.copy())
        self.bg_colors.append(blank_array.copy())
        # UV init is more complex than just all zeroes
        self.uv_mods.append(self.new_uv_layers(self.layers))
        if self.log_size_changes:
            self.app.log('frame %s added with %s layers' % (self.frames-1, self.layers))
    
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
            self.app.log('duplicated frame %s as frame %s' % (frame_index, self.frames-1))
    
    def set_charset(self, new_charset):
        if self.recalc_quad_height:
            self.quad_width = 1
            self.quad_height = 1 * (self.charset.char_height / self.charset.char_width)
        self.charset = new_charset
        self.geo_changed = True
    
    def add_layer(self, z=DEFAULT_LAYER_Z):
        self.layers += 1
        self.layers_z.append(z)
        # simply add another layer to our 3D array
        new_tile_shape = (self.layers, self.height, self.width, 4)
        new_uv_shape = (self.layers, self.height, self.width, UV_STRIDE)
        for frame in range(self.frames):
            self.chars[frame] = np.resize(self.chars[frame], new_tile_shape)
            self.fg_colors[frame] = np.resize(self.fg_colors[frame], new_tile_shape)
            self.bg_colors[frame] = np.resize(self.bg_colors[frame], new_tile_shape)
            self.uv_mods[frame] = np.resize(self.uv_mods[frame], new_uv_shape)
        # adding a layer changes all frames' UV data
        for i in range(self.frames): self.uv_changed_frames.append(i)
        if self.log_size_changes:
            self.app.log('added layer %s' % (self.layers))
        # rebuild geo with added verts for new layer
        self.geo_changed = True
    
    def resize(self, new_width, new_height, new_bg=0):
        "resizes this Art to the given dimensions, cropping or expanding as needed"
        self.width, self.height = new_width, new_height
        new_shape = (self.layers, self.height, self.width, 4)
        new_uv_shape = (self.layers, self.height, self.width, UV_STRIDE)
        for frame in range(self.frames):
            self.chars[frame] = np.resize(self.chars[frame], new_shape)
            self.fg_colors[frame] = np.resize(self.fg_colors[frame], new_shape)
            self.bg_colors[frame] = np.resize(self.bg_colors[frame], new_shape)
            self.uv_mods[frame] = np.resize(self.uv_mods[frame], new_uv_shape)
        # adding a layer changes all frames' UV data
        for i in range(self.frames): self.uv_changed_frames.append(i)
        # TODO: use specified background color for newly created tiles?
        self.geo_changed = True
    
    def clear_frame_layer(self, frame, layer, bg_color=0, fg_color=None):
        "clears given layer of given frame to transparent BG + no characters"
        # "clear" UVs to UV_NORMAL
        for y in range(self.height):
            for x in range(self.width):
                self.uv_mods[frame][layer][y][x] = uv_types[UV_NORMAL]
                self.chars[frame][layer][y][x] = 0
                self.fg_colors[frame][layer][y][x] = fg_color or 0
                self.bg_colors[frame][layer][y][x] = bg_color
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
        shape = (self.layers, self.height, self.width, VERT_STRIDE)
        self.vert_array = np.empty(shape, dtype=np.float32)
        all_elems_size = self.layers * self.width * self.height * ELEM_STRIDE
        self.elem_array = np.empty(shape=all_elems_size, dtype=np.uint32)
        # generate geo according to art size
        # vert_index corresponds to # of verts, loc_index to position in array
        # (given that each vert has 3 components)
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
                    z = self.layers_z[layer]
                    verts = [x0, y0, z]
                    verts += [x1, y1, z]
                    verts += [x2, y2, z]
                    verts += [x3, y3, z]
                    self.vert_array[layer][tile_y][tile_x] = verts
                    # vertex elements
                    elements = [vert_index, vert_index+1, vert_index+2]
                    elements += [vert_index+1, vert_index+2, vert_index+3]
                    self.elem_array[elem_index:elem_index+ELEM_STRIDE] = elements
                    elem_index += ELEM_STRIDE
                    # 4 verts in a quad
                    vert_index += 4
    
    def new_uv_layers(self, layers):
        "returns given # of layer's worth of vanilla UV array data"
        shape = (layers, self.height, self.width, UV_STRIDE)
        array = np.zeros(shape, dtype=np.float32)
        # default new layer of UVs to "normal" transform
        uvs = uv_types[UV_NORMAL]
        for layer in range(layers):
            for y in range(self.height):
                for x in range(self.width):
                    array[layer][y][x] = uvs
        return array
    
    def is_tile_inside(self, x, y):
        "returns True if given X,Y tile coord is within our bounds"
        return 0 <= x < self.width and 0 <= y < self.height
    
    # get methods
    def get_char_index_at(self, frame, layer, x, y):
        return int(self.chars[frame][layer][y][x][0])
    
    def get_fg_color_index_at(self, frame, layer, x, y):
        return int(self.fg_colors[frame][layer][y][x][0])
    
    def get_bg_color_index_at(self, frame, layer, x, y):
        return int(self.bg_colors[frame][layer][y][x][0])
    
    def get_char_transform_at(self, frame, layer, x, y):
        uvs = self.uv_mods[frame][layer][y][x]
        # use reverse dict of tuples b/c they're hashable
        return uv_types_reverse.get(tuple(uvs), UV_NORMAL)
    
    def get_tile_at(self, frame, layer, x, y):
        char = self.get_char_index_at(frame, layer, x, y)
        fg = self.get_fg_color_index_at(frame, layer, x, y)
        bg = self.get_bg_color_index_at(frame, layer, x, y)
        xform = self.get_char_transform_at(frame, layer, x, y)
        return char, fg, bg, xform
    
    # set methods
    def set_char_index_at(self, frame, layer, x, y, char_index):
        self.chars[frame][layer][y][x] = char_index
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
        update_array[layer][y][x] = color_index
        if fg and not frame in self.fg_changed_frames:
            self.fg_changed_frames.append(frame)
        elif not fg and not frame in self.bg_changed_frames:
            self.bg_changed_frames.append(frame)
    
    def set_char_transform_at(self, frame, layer, x, y, transform):
        self.uv_mods[frame][layer][y][x] = uv_types[transform]
        if not frame in self.uv_changed_frames:
            self.uv_changed_frames.append(frame)
    
    def set_tile_at(self, frame, layer, x, y, char_index=None, fg=None, bg=None,
                    transform=None):
        "convenience function for setting (up to) all 3 tile indices at once"
        if char_index is not None:
            self.set_char_index_at(frame, layer, x, y, char_index)
        if fg is not None:
            self.set_color_at(frame, layer, x, y, fg, True)
        if bg is not None:
            self.set_color_at(frame, layer, x, y, bg, False)
        if transform is not None:
            self.set_char_transform_at(frame, layer, x, y, transform)
    
    def update(self):
        self.update_scripts()
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
    
    def save_to_file(self):
        "build a dict representing all this art's data and write it to disk"
        d = {}
        d['width'] = self.width
        d['height'] = self.height
        # preferred character set and palette, default used if not found
        d['charset'] = self.charset.name
        d['palette'] = self.palette.name
        # remember camera location
        d['camera'] = self.app.camera.x, self.app.camera.y, self.app.camera.z
        # frames and layers are dicts w/ lists of their data + a few properties
        frames = []
        for frame_index in range(self.frames):
            frame = { 'delay': self.frame_delays[frame_index] }
            layers = []
            for layer_index in range(self.layers):
                layer = { 'z': self.layers_z[layer_index] }
                tiles = []
                for y in range(self.height):
                    for x in range(self.width):
                        char = int(self.chars[frame_index][layer_index][y][x][0])
                        fg = int(self.fg_colors[frame_index][layer_index][y][x][0])
                        bg = int(self.bg_colors[frame_index][layer_index][y][x][0])
                        # use get method for transform, data's not simply an int
                        xform = self.get_char_transform_at(frame_index, layer_index, x, y)
                        tiles.append({'char': char, 'fg': fg, 'bg': bg, 'xform': xform})
                layer['tiles'] = tiles
                layers.append(layer)
            frame['layers'] = layers
            frames.append(frame)
        d['frames'] = frames
        # MAYBE-TODO: below gives not-so-pretty-printing, find out way to control
        # formatting for better output
        json.dump(d, open(self.filename, 'w'), sort_keys=True, indent=1)
        self.app.log('saved %s to disk.' % self.filename)
    
    def set_filename(self, new_filename):
        # append extension if missing
        if not new_filename.endswith('.%s' % ART_FILE_EXTENSION):
            new_filename += '.%s' % ART_FILE_EXTENSION
        # if no dir given, assume art/ dir
        #if not '/' in new_filename:
        if os.path.basename(new_filename) == new_filename:
            new_filename = '%s%s' % (ART_DIR, new_filename)
        # TODO: check if file already exists?
        self.filename = new_filename
    
    def run_script(self, script_filename):
        """
        Runs a script on this Art. Scripts contain arbitrary python expressions.
        """
        script_filename = self.get_valid_script_filename(script_filename)
        if not script_filename:
            return
        exec(open(script_filename).read())
        self.app.log('Executed %s' % script_filename)
    
    def is_script_running(self, script_filename):
        script_filename = self.get_valid_script_filename(script_filename)
        return script_filename and script_filename in self.scripts
    
    def get_valid_script_filename(self, script_filename):
        if os.path.exists(script_filename): return script_filename
        # try adding scripts/ subdir
        script_filename = '%s%s' % (SCRIPT_DIR, script_filename)
        if os.path.exists(script_filename): return script_filename
        # try adding extension
        script_filename += '.%s' % SCRIPT_FILE_EXTENSION
        if not os.path.exists(script_filename):
            self.app.log("Couldn't find script file %s" % script_filename)
            return
        return script_filename
    
    def run_script_every(self, script_filename, rate=0.1):
        "starts a script running on this Art at a regular rate."
        script_filename = self.get_valid_script_filename(script_filename)
        if not script_filename:
            return
        if script_filename in self.scripts:
            self.app.log('script %s is already running.' % script_filename)
            return
        # add to "scripts currently running" list
        self.scripts.append(script_filename)
        self.script_rates.append(rate)
        # set next time
        next_run = (self.app.elapsed_time / 1000) + rate
        self.scripts_next_exec_time.append(next_run)
    
    def stop_script(self, script_filename):
        # remove from running scripts, rate list, next_exec list
        script_filename = self.get_valid_script_filename(script_filename)
        if not script_filename:
            return
        if not script_filename in self.scripts:
            self.app.log("script %s exists but isn't running." % script_filename)
            return
        script_index = self.scripts.index(script_filename)
        self.scripts.pop(script_index)
        self.script_rates.pop(script_index)
        self.scripts_next_exec_time.pop(script_index)
    
    def update_scripts(self):
        if len(self.scripts) == 0:
            return
        for i,script in enumerate(self.scripts):
            if (self.app.elapsed_time / 1000) > self.scripts_next_exec_time[i]:
                exec(open(script).read())
                self.scripts_next_exec_time[i] += self.script_rates[i]
    
    def write_string(self, frame, layer, x, y, text, fg_color_index=None, bg_color_index=None, right_justify=False):
        "writes out each char of a string to specified tiles"
        if right_justify:
            x_offset = -len(text)
        else:
            x_offset = 0
        for char in text:
            idx = self.charset.get_char_index(char)
            self.set_char_index_at(frame, layer, x+x_offset, y, idx)
            if fg_color_index:
                self.set_color_at(frame, layer, x+x_offset, y, fg_color_index, True)
            if bg_color_index:
                self.set_color_at(frame, layer, x+x_offset, y, bg_color_index, False)
            x_offset += 1
            if self.write_string_range_check and (x+x_offset < 0 or x+x_offset > self.width - 1):
                self.app.log('Warning: %s.write_string went out of bounds at %s,%s' % (self.filename, x+x_offset, y))
                break


class ArtFromDisk(Art):
    
    "subclass of Art that loads from a file"
    
    def __init__(self, filename, app):
        self.valid = False
        try:
            d = json.load(open(filename))
        except:
            return
        self.filename = filename
        self.app = app
        self.width = d['width']
        self.height = d['height']
        self.charset = self.app.load_charset(d['charset'])
        self.palette = self.app.load_palette(d['palette'])
        # use correct character aspect
        self.quad_height = self.charset.char_height / self.charset.char_width
        if not self.app.override_saved_camera:
            cam = d['camera']
            self.app.camera.set_loc(cam[0], cam[1], cam[2])
        frames = d['frames']
        self.frames = len(frames)
        self.frame_delays = []
        # number of layers should be same for all frames
        self.layers = len(frames[0]['layers'])
        # get layer z depths from first frame's data
        self.layers_z = []
        for layer in frames[0]['layers']:
            self.layers_z.append(layer['z'])
        self.chars, self.uv_mods, self.fg_colors, self.bg_colors = [],[],[],[]
        # lists of changed frames
        self.char_changed_frames, self.uv_changed_frames = [], []
        self.fg_changed_frames, self.bg_changed_frames = [], []
        tiles = self.layers * self.width * self.height
        # build tile data arrays from frame+layer lists
        shape = (self.layers, self.height, self.width, 4)
        for frame in frames:
            self.frame_delays.append(frame['delay'])
            chars = np.zeros(shape, dtype=np.float32)
            uvs = self.new_uv_layers(self.layers)
            fg_colors = chars.copy()
            bg_colors = chars.copy()
            for layer_index,layer in enumerate(frame['layers']):
                x, y = 0, 0
                for tile in layer['tiles']:
                    chars[layer_index][y][x] = tile['char']
                    fg_colors[layer_index][y][x] = tile['fg']
                    bg_colors[layer_index][y][x] = tile['bg']
                    uvs[layer_index][y][x] = uv_types[tile.get('xform', UV_NORMAL)]
                    x += 1
                    if x >= self.width:
                        x = 0
                        y += 1
            self.chars.append(chars)
            self.fg_colors.append(fg_colors)
            self.bg_colors.append(bg_colors)
            self.uv_mods.append(uvs)
        # TODO: for hot-reload, app should pass in old renderables list
        self.renderables = []
        # running scripts and timing info
        self.scripts = []
        self.script_rates = []
        self.scripts_next_exec_time = []
        self.geo_changed = True
        self.update()
        if self.log_creation:
            self.app.log('loaded %s from disk:' % filename)
            self.app.log('  character set: %s' % self.charset.name)
            self.app.log('  palette: %s' % self.palette.name)
            self.app.log('  width/height: %s x %s' % (self.width, self.height))
            self.app.log('  frames: %s' % self.frames)
            self.app.log('  layers: %s' % self.layers)
        # signify to app that this file loaded successfully
        self.valid = True


class ArtFromEDSCII(Art):
    """
    file loader for legacy EDSCII format.
    assumes single frames, single layer, default charset and palette.
    """
    def __init__(self, filename, app, width_override=None):
        # once load process is complete set this true to signify valid data
        self.valid = False
        try:
            data = open(filename, 'rb').read()
        except:
            return
        self.filename = '%s.%s' % (os.path.splitext(filename)[0], ART_FILE_EXTENSION)
        self.app = app
        # document width = find longest stretch before a \n
        longest_line = 0
        for line in data.splitlines():
            if len(line) > longest_line:
                longest_line = len(line)
        self.width = width_override or int(longest_line / 3)
        # derive height from width
        # 2-byte line breaks might produce non-int result, cast erases this
        self.height = int(len(data) / self.width / 3)
        # defaults
        self.charset = self.app.load_charset(app.starting_charset)
        self.palette = self.app.load_palette(app.starting_palette)
        # use correct character aspect
        self.quad_height = self.charset.char_height / self.charset.char_width
        self.frames = 1
        self.frame_delays = [DEFAULT_FRAME_DELAY]
        self.layers = 1
        self.layers_z = [DEFAULT_LAYER_Z]
        shape = (self.layers, self.height, self.width, 4)
        chars = np.zeros(shape, dtype=np.float32)
        fg_colors = chars.copy()
        bg_colors = chars.copy()
        # populate char/color arrays by scanning width-long chunks of file
        def chunks(l, n):
            for i in range(0, len(l), n):
                yield l[i:i+n]
        # 3 bytes per tile, +1 for line ending
        # BUT: files saved in windows may have 2 byte line breaks, try to detect
        lb_length = 1
        lines = chunks(data, (self.width * 3) + lb_length)
        for line in lines:
            if line[-2] == ord('\r') and line[-1] == ord('\n'):
                self.app.log('windows-style line breaks detected')
                lb_length = 2
                break
        # recreate generator after first use
        lines = chunks(data, (self.width * 3) + lb_length)
        x, y = 0, 0
        for line in lines:
            index = 0
            while index < len(line) - lb_length:
                chars[0][y][x] = line[index]
                # +1 to color indices: playscii color index 0 = transparent
                fg_colors[0][y][x] = line[index+1] + 1
                bg_colors[0][y][x] = line[index+2] + 1
                index += 3
                x += 1
                if x >= self.width:
                    x = 0
                    y += 1
        self.chars = [chars]
        self.uv_mods = [self.new_uv_layers(self.layers)]
        self.fg_colors, self.bg_colors = [fg_colors], [bg_colors]
        self.char_changed_frames, self.uv_changed_frames = [], []
        self.fg_changed_frames, self.bg_changed_frames = [], []
        self.renderables = []
        # running scripts and timing info
        self.scripts = []
        self.script_rates = []
        self.scripts_next_exec_time = []
        self.geo_changed = True
        self.update()
        if self.log_creation:
            self.app.log('EDSCII file %s loaded from disk:' % filename)
            self.app.log('  width/height: %s x %s' % (self.width, self.height))
        self.valid = True
