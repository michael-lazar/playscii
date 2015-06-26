import os.path, json
import numpy as np

from random import randint

from edit_command import CommandStack

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
DEFAULT_LAYER_Z_OFFSET = 0.5

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

uv_names = {
    UV_NORMAL: 'Normal',
    UV_ROTATE90: 'Rotate 90',
    UV_ROTATE180: 'Rotate 180',
    UV_ROTATE270: 'Rotate 270',
    UV_FLIPX: 'Flip X',
    UV_FLIPY: 'Flip Y',
}

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
    
    def __init__(self, filename, app, charset, palette, width, height):
        "creates a new, blank document"
        if filename and not filename.endswith('.%s' % ART_FILE_EXTENSION):
            filename += '.%s' % ART_FILE_EXTENSION
        self.filename = filename
        self.app = app
        # save "time loaded" for menu sorting
        self.time_loaded = 0
        self.charset, self.palette = charset, palette
        self.command_stack = CommandStack(self)
        self.unsaved_changes = False
        self.width, self.height = width, height
        self.frames = 0
        # current frame being edited
        self.active_frame = 0
        # list of frame delays
        self.frame_delays = []
        self.layers = 1
        # current layer being edited
        self.active_layer = 0
        # lists of layer Z values and names
        self.layers_z = [DEFAULT_LAYER_Z]
        self.layer_names = ['Layer 1']
        # list of char/fg/bg arrays, one for each frame
        self.chars, self.uv_mods, self.fg_colors, self.bg_colors = [],[],[],[]
        # lists of changed frames, processed each update()
        self.char_changed_frames, self.uv_changed_frames = [], []
        self.fg_changed_frames, self.bg_changed_frames = [], []
        # add one frame to start
        self.add_frame_to_end(DEFAULT_FRAME_DELAY, False)
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
        if self.log_creation and not self.app.game_mode:
            self.app.log('created new document:')
            self.app.log('  character set: %s' % self.charset.name)
            self.app.log('  palette: %s' % self.palette.name)
            self.app.log('  width/height: %s x %s' % (self.width, self.height))
            self.app.log('  frames: %s' % self.frames)
            self.app.log('  layers: %s' % self.layers)
    
    def insert_frame_before_index(self, index, delay=DEFAULT_FRAME_DELAY, log=True):
        "adds a blank frame at the specified index (len+1 to add to end)"
        self.frames += 1
        self.frame_delays.insert(index, delay)
        tiles = self.layers * self.width * self.height
        shape = (self.layers, self.height, self.width, 4)
        fg, bg = 0, 0
        if self.app.ui:
            fg = self.app.ui.selected_fg_color
            bg = self.app.ui.selected_bg_color
        new_char = np.zeros(shape, dtype=np.float32)
        new_fg = np.full(shape, fg, dtype=np.float32)
        new_bg = np.full(shape, bg, dtype=np.float32)
        self.chars.insert(index, new_char)
        self.fg_colors.insert(index, new_fg)
        self.bg_colors.insert(index, new_bg)
        # UV init is more complex than just all zeroes
        self.uv_mods.insert(index, self.new_uv_layers(self.layers))
        # all but lowest layer = transparent
        for l in range(1, self.layers):
            self.clear_frame_layer(index, l, 0, fg)
        self.mark_all_frames_changed()
        # set new frame as active
        if self.app.ui and self is self.app.ui.active_art:
            self.app.ui.set_active_frame(index)
        if log:
            self.app.log('Created new frame at index %s' % str(index))
    
    def add_frame_to_end(self, delay=DEFAULT_FRAME_DELAY, log=True):
        self.insert_frame_before_index(self.frames, delay, log)
    
    def duplicate_frame(self, src_frame_index, dest_frame_index=None, delay=None):
        "creates a duplicate of given frame at given index"
        # stick new frame at end if no destination index given
        dest_frame_index = dest_frame_index or self.frames
        # copy source frame's delay if none given
        delay = delay or self.frame_delays[src_frame_index]
        self.frames += 1
        self.frame_delays.insert(dest_frame_index, delay)
        # copy source frame's char/color arrays
        self.chars.insert(dest_frame_index, self.chars[src_frame_index].copy())
        self.uv_mods.insert(dest_frame_index, self.uv_mods[src_frame_index].copy())
        self.fg_colors.insert(dest_frame_index, self.fg_colors[src_frame_index].copy())
        self.bg_colors.insert(dest_frame_index, self.bg_colors[src_frame_index].copy())
        self.mark_all_frames_changed()
        # set new frame as active
        if self is self.app.ui.active_art:
            self.app.ui.set_active_frame(dest_frame_index-1)
        self.app.log('Duplicated frame %s at frame %s' % (src_frame_index+1, dest_frame_index))
    
    def delete_frame_at(self, index):
        self.chars.pop(index)
        self.fg_colors.pop(index)
        self.bg_colors.pop(index)
        self.uv_mods.pop(index)
        self.frames -= 1
        self.mark_all_frames_changed()
        if self is self.app.ui.active_art:
            self.app.ui.set_active_frame(index)
    
    def move_frame_to_index(self, src_index, dest_index):
        char_data = self.chars.pop(src_index)
        fg_data = self.fg_colors.pop(src_index)
        bg_data = self.bg_colors.pop(src_index)
        uv_data = self.uv_mods.pop(src_index)
        self.chars.insert(dest_index, char_data)
        self.fg_colors.insert(dest_index, fg_data)
        self.bg_colors.insert(dest_index, bg_data)
        self.uv_mods.insert(dest_index, uv_data)
        self.mark_all_frames_changed()
    
    def add_layer(self, z=None, name=None):
        # offset Z from last layer's Z if none given
        z = z or self.layers_z[-1] + DEFAULT_LAYER_Z_OFFSET
        # index isn't user-facing, z is what matters
        index = self.layers - 1
        # duplicate_layer increases self.layers by 1
        self.duplicate_layer(index, z, name)
        for frame in range(self.frames):
            self.clear_frame_layer(frame, self.layers-1, 0)
        # set new layer as active
        if self is self.app.ui.active_art:
            self.app.ui.set_active_layer(index+1)
    
    def duplicate_layer(self, src_index, z=None, new_name=None):
        def duplicate_layer_array(array):
            src_data = np.array([array[src_index]])
            return np.append(array, src_data, 0)
        for frame in range(self.frames):
            self.chars[frame] = duplicate_layer_array(self.chars[frame])
            self.fg_colors[frame] = duplicate_layer_array(self.fg_colors[frame])
            self.bg_colors[frame] = duplicate_layer_array(self.bg_colors[frame])
            self.uv_mods[frame] = duplicate_layer_array(self.uv_mods[frame])
        self.layers += 1
        z = z or self.layers_z[-1] + DEFAULT_LAYER_Z_OFFSET
        self.layers_z.append(z)
        new_name = new_name or 'Copy of %s' % self.layer_names[src_index]
        self.layer_names.append(new_name)
        # rebuild geo with added verts for new layer
        self.geo_changed = True
        # set new layer as active
        if self is self.app.ui.active_art:
            self.app.ui.set_active_layer(self.layers - 1)
        self.app.log('Added new layer %s' % new_name)
    
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
    
    def delete_layer(self, index):
        "deletes layer at given index"
        for frame in range(self.frames):
            self.chars[frame] = np.delete(self.chars[frame], index, 0)
            self.fg_colors[frame] = np.delete(self.fg_colors[frame], index, 0)
            self.bg_colors[frame] = np.delete(self.bg_colors[frame], index, 0)
            self.uv_mods[frame] = np.delete(self.uv_mods[frame], index, 0)
        self.layers_z.pop(index)
        self.layer_names.pop(index)
        self.layers -= 1
        self.geo_changed = True
        self.mark_all_frames_changed()
        if self.active_layer > self.layers - 1:
            self.app.ui.set_active_layer(self.layers - 1)
    
    def set_charset(self, new_charset):
        if new_charset is self.charset:
            return
        if self.recalc_quad_height:
            self.quad_width = 1
            self.quad_height = 1 * (self.charset.char_height / self.charset.char_width)
        self.charset = new_charset
        self.set_unsaved_changes(True)
        self.geo_changed = True
    
    def set_palette(self, new_palette):
        if new_palette is self.palette:
            return
        self.palette = new_palette
        self.set_unsaved_changes(True)
    
    def set_active_frame(self, new_frame):
        new_frame %= self.frames
        # bail if frame is still the same, eg we only have 1 frame
        if new_frame == self.active_frame:
            # return whether or not we actually changed frames
            return False
        self.active_frame = new_frame
        # update our renderables
        for r in self.renderables:
            r.set_frame(self.active_frame)
        return True
    
    def set_active_layer(self, new_layer):
        self.active_layer = min(max(0, new_layer), self.layers-1)
    
    def crop(self, new_width, new_height, origin_x=0, origin_y=0):
        x0, y0 = origin_x, origin_y
        x1, y1 = x0 + new_width, y0 + new_height
        crop_x = new_width < self.width
        crop_y = new_height < self.height
        for frame in range(self.frames):
            for array in [self.chars, self.fg_colors,
                          self.bg_colors, self.uv_mods]:
                if crop_x:
                    array[frame] = array[frame].take(range(x0, x1), axis=2)
                if crop_y:
                    array[frame] = array[frame].take(range(y0, y1), axis=1)
    
    def expand(self, new_width, new_height):
        x_add = new_width - self.width
        y_add = new_height - self.height
        #print('%s expand: %sw + %s = %s, %sh + %s = %s' % (self.filename,
        #    self.width, x_add, new_width, self.height, y_add, new_height))
        def expand_array(array, fill_value, stride):
            # add columns (increasing width)
            if x_add > 0:
                # before height has changed, take care not to append
                # incorrectly sized columns
                h = new_height if new_height < self.height else self.height
                add_shape = (self.layers, h, x_add, stride)
                add = np.full(add_shape, fill_value, dtype=np.float32)
                array = np.append(array, add, 2)
            # add rows (increasing height)
            if y_add > 0:
                add_shape = (self.layers, y_add, new_width, stride)
                add = np.full(add_shape, fill_value, dtype=np.float32)
                array = np.append(array, add, 1)
            # can't modify passed array in-place
            return array
        for frame in range(self.frames):
            self.chars[frame] = expand_array(self.chars[frame], 0, 4)
            fg, bg = 0, 0
            if self.app.ui:
                fg = self.app.ui.selected_fg_color
                # blank background for all new tiles
                # (this might be annoying, just trying it out for a while)
                #bg = self.app.ui.selected_bg_color
            self.fg_colors[frame] = expand_array(self.fg_colors[frame], fg, 4)
            self.bg_colors[frame] = expand_array(self.bg_colors[frame], bg, 4)
            self.uv_mods[frame] = expand_array(self.uv_mods[frame], UV_NORMAL, UV_STRIDE)
    
    def mark_all_frames_changed(self):
        for frame in range(self.frames):
            for l in [self.char_changed_frames, self.fg_changed_frames,
                      self.bg_changed_frames, self.uv_changed_frames]:
                l.append(frame)
    
    def resize(self, new_width, new_height, origin_x=0, origin_y=0):
        if new_width < self.width or new_height < self.height:
            self.crop(new_width, new_height, origin_x, origin_y)
        if new_width > self.width or new_height > self.height:
            self.expand(new_width, new_height)
        self.width, self.height = new_width, new_height
        # tell all frames they've changed, rebind buffers
        self.geo_changed = True
        self.mark_all_frames_changed()
    
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
                    # Z of all layers is 0, layer Z set in shader
                    verts = [x0, y0, 0]
                    verts += [x1, y1, 0]
                    verts += [x2, y2, 0]
                    verts += [x3, y3, 0]
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
        self.updated_this_tick = True
    
    def save_to_file(self):
        "build a dict representing all this art's data and write it to disk"
        # cursor might be hovering, undo any preview changes
        for edit in self.app.cursor.preview_edits:
            edit.undo()
        d = {}
        d['width'] = self.width
        d['height'] = self.height
        # preferred character set and palette, default used if not found
        d['charset'] = self.charset.name
        d['palette'] = self.palette.name
        d['active_frame'] = self.active_frame
        d['active_layer'] = self.active_layer
        # remember camera location
        d['camera'] = self.app.camera.x, self.app.camera.y, self.app.camera.z
        # frames and layers are dicts w/ lists of their data + a few properties
        frames = []
        for frame_index in range(self.frames):
            frame = { 'delay': self.frame_delays[frame_index] }
            layers = []
            for layer_index in range(self.layers):
                layer = { 'z': self.layers_z[layer_index] }
                layer['name'] = self.layer_names[layer_index]
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
        self.set_unsaved_changes(False)
        self.app.log('saved %s to disk.' % self.filename)
    
    def set_unsaved_changes(self, new_status):
        if new_status == self.unsaved_changes:
            return
        self.unsaved_changes = new_status
        self.app.update_window_title()
    
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
    
    def clear_line(self, frame, layer, line_y, fg_color_index=None,
                   bg_color_index=None):
        # TODO: use numpy slicing to do this much more quickly!
        for x in range(self.width):
            self.set_char_index_at(frame, layer, x, line_y, 0)
            if fg_color_index:
                self.set_color_at(frame, layer, x, line_y, fg_color_index)
            if bg_color_index:
                self.set_color_at(frame, layer, x, line_y, bg_color_index, False)
    
    def write_string(self, frame, layer, x, y, text, fg_color_index=None,
                     bg_color_index=None, right_justify=False):
        "writes out each char of a string to specified tiles"
        if y >= self.height:
            return
        x %= self.width
        if right_justify:
            x_offset = -len(text)
        else:
            x_offset = 0
        # never let string drawing go out of bounds
        text = text[:self.width - (x+x_offset)]
        for char in text:
            idx = self.charset.get_char_index(char)
            self.set_char_index_at(frame, layer, x+x_offset, y, idx)
            if fg_color_index:
                self.set_color_at(frame, layer, x+x_offset, y, fg_color_index, True)
            if bg_color_index:
                self.set_color_at(frame, layer, x+x_offset, y, bg_color_index, False)
            x_offset += 1


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
        if not self.charset:
            self.app.log('Character set %s not found!' % d['charset'])
            return
        self.palette = self.app.load_palette(d['palette'])
        if not self.palette:
            self.app.log('Palette %s not found!' % d['palette'])
            return
        # use correct character aspect
        self.quad_height = self.charset.char_height / self.charset.char_width
        if not self.app.override_saved_camera and not self.app.game_mode:
            cam = d['camera']
            self.app.camera.set_loc(cam[0], cam[1], cam[2])
        frames = d['frames']
        self.frames = len(frames)
        self.frame_delays = []
        # active frame will be set properly near end of init
        self.active_frame = 0
        # number of layers should be same for all frames
        self.layers = len(frames[0]['layers'])
        # get layer z depths from first frame's data
        self.layers_z = []
        self.layer_names = []
        # active frame will be set properly near end of init
        self.active_layer = 0
        for i,layer in enumerate(frames[0]['layers']):
            self.layers_z.append(layer['z'])
            layer_num = str(i + 1)
            self.layer_names.append(layer.get('name', 'Layer %s' % layer_num))
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
        self.renderables = []
        self.command_stack = CommandStack(self)
        self.unsaved_changes = False
        # running scripts and timing info
        self.scripts = []
        self.script_rates = []
        self.scripts_next_exec_time = []
        self.geo_changed = True
        # set active frame and layer properly
        active_frame = d.get('active_frame', 0)
        self.set_active_frame(active_frame)
        active_layer = d.get('active_layer', 0)
        self.set_active_layer(active_layer)
        self.update()
        if self.log_creation and not self.app.game_mode:
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
        self.active_frame = 0
        self.layers = 1
        self.layers_z = [DEFAULT_LAYER_Z]
        self.layer_names = ['Layer 1']
        self.active_layer = 0
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
        self.command_stack = CommandStack(self)
        self.unsaved_changes = False
        # running scripts and timing info
        self.scripts = []
        self.script_rates = []
        self.scripts_next_exec_time = []
        self.geo_changed = True
        self.update()
        if self.log_creation and not self.app.game_mode:
            self.app.log('EDSCII file %s loaded from disk:' % filename)
            self.app.log('  width/height: %s x %s' % (self.width, self.height))
        self.valid = True
