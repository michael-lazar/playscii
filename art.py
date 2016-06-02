import os.path, json, time
import numpy as np

from edit_command import CommandStack
from image_export import write_thumbnail

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
EDSCII_FILE_EXTENSION = 'ed'

THUMBNAIL_CACHE_DIR = 'thumbnails/'

ART_SCRIPT_DIR = 'artscripts/'
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
    - each layer is a rectangular grid of Width * Height tiles
    - each tile has: character, foreground color, background color, & transform
    - char/color tile values are expressed as indices into charset / palette
    - all layers in an Art are the same dimensions
    """
    quad_width,quad_height = 1, 1
    "size of each tile in world space"
    log_size_changes = False
    recalc_quad_height = True
    log_creation = False
    
    def __init__(self, filename, app, charset, palette, width, height):
        "Creates a new, blank document with given parameters."
        self.valid = False
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
        # camera position - updated in Art.update, saved in .psci
        self.update_saved_camera(self.app.camera)
        # list of char/fg/bg arrays, one for each frame
        self.chars, self.uv_mods, self.fg_colors, self.bg_colors = [],[],[],[]
        # lists of changed frames, processed each update()
        self.char_changed_frames, self.uv_changed_frames = [], []
        self.fg_changed_frames, self.bg_changed_frames = [], []
        self.renderables = []
        "List of TileRenderables using us - each new Renderable adds itself"
        self.instances = []
        "List of ArtInstances using us as their source"
        # init frames and layers - ArtFromDisk has its own logic for this
        self.init_layers()
        self.init_frames()
        # support non-square characters:
        # derive quad_height from chars aspect; quad_width always 1.0
        if self.recalc_quad_height:
            self.quad_height *= self.charset.char_height / self.charset.char_width
        # running scripts and timing info
        self.scripts = []
        self.script_rates = []
        self.scripts_next_exec_time = []
        # tell renderables to rebind vert and element buffers next update
        self.geo_changed = True
        # run update once before renderables initialize so they have
        # something to bind
        self.first_update()
        if self.log_creation and not self.app.game_mode:
            self.log_init()
        self.valid = True
    
    def log_init(self):
        self.app.log('created new document:')
        self.app.log('  character set: %s' % self.charset.name)
        self.app.log('  palette: %s' % self.palette.name)
        self.app.log('  width/height: %s x %s' % (self.width, self.height))
        self.app.log('  frames: %s' % self.frames)
        self.app.log('  layers: %s' % self.layers)
    
    def init_layers(self):
        self.layers = 1
        # current layer being edited
        self.active_layer = 0
        # lists of layer Z values and names
        self.layers_z = [DEFAULT_LAYER_Z]
        self.layers_visibility = [True]
        self.layer_names = ['Layer 1']
    
    def init_frames(self):
        self.frames = 0
        # current frame being edited
        self.active_frame = 0
        # list of frame delays
        self.frame_delays = []
        # add one frame to start
        self.add_frame_to_end(DEFAULT_FRAME_DELAY, False)
        # clear our single layer to a sensible BG color
        self.clear_frame_layer(0, 0, bg_color=self.palette.darkest_index)
    
    def first_update(self):
        self.update()
    
    def insert_frame_before_index(self, index, delay=DEFAULT_FRAME_DELAY, log=True):
        "Add a blank frame at the specified index (len+1 to add to end)."
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
        "Add a blank frame at the end of the current animation."
        self.insert_frame_before_index(self.frames, delay, log)
    
    def duplicate_frame(self, src_frame_index, dest_frame_index=None, delay=None):
        "Create a duplicate of given frame at given index."
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
        "Delete frame at given index."
        self.chars.pop(index)
        self.fg_colors.pop(index)
        self.bg_colors.pop(index)
        self.uv_mods.pop(index)
        self.frames -= 1
        self.mark_all_frames_changed()
        if self is self.app.ui.active_art:
            self.app.ui.set_active_frame(index)
    
    def move_frame_to_index(self, src_index, dest_index):
        "Move frame at given index to new given index."
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
        "Add a new layer with given Z with given name."
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
        "Duplicate layer with given index. Duplicate uses given Z and name."
        def duplicate_layer_array(array):
            src_data = np.array([array[src_index]])
            return np.append(array, src_data, 0)
        for frame in range(self.frames):
            self.chars[frame] = duplicate_layer_array(self.chars[frame])
            self.fg_colors[frame] = duplicate_layer_array(self.fg_colors[frame])
            self.bg_colors[frame] = duplicate_layer_array(self.bg_colors[frame])
            self.uv_mods[frame] = duplicate_layer_array(self.uv_mods[frame])
        self.layers += 1
        z = z or self.layers_z
        self.layers_z.append(z)
        self.layers_visibility.append(True)
        new_name = new_name or 'Copy of %s' % self.layer_names[src_index]
        self.layer_names.append(new_name)
        # rebuild geo with added verts for new layer
        self.geo_changed = True
        # set new layer as active
        if self is self.app.ui.active_art:
            self.app.ui.set_active_layer(self.layers - 1)
        self.app.log('Added new layer %s' % new_name)
        self.set_unsaved_changes(True)
    
    def clear_frame_layer(self, frame, layer, bg_color=0, fg_color=None):
        "Clear given layer of given frame to transparent BG + no characters."
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
        "Delete layer at given index."
        for frame in range(self.frames):
            self.chars[frame] = np.delete(self.chars[frame], index, 0)
            self.fg_colors[frame] = np.delete(self.fg_colors[frame], index, 0)
            self.bg_colors[frame] = np.delete(self.bg_colors[frame], index, 0)
            self.uv_mods[frame] = np.delete(self.uv_mods[frame], index, 0)
        self.layers_z.pop(index)
        self.layers_visibility.pop(index)
        self.layer_names.pop(index)
        self.layers -= 1
        self.geo_changed = True
        self.mark_all_frames_changed()
        if self.active_layer > self.layers - 1:
            self.app.ui.set_active_layer(self.layers - 1)
        self.set_unsaved_changes(True)
    
    def set_charset(self, new_charset):
        "Set Art to use given character set (referenced by object, not name)."
        if new_charset is self.charset:
            return
        self.charset = new_charset
        if self.recalc_quad_height:
            self.quad_width = 1
            self.quad_height = 1 * (self.charset.char_height / self.charset.char_width)
        self.set_unsaved_changes(True)
        self.geo_changed = True
    
    def set_palette(self, new_palette):
        "Set Art to use given color palette (referenced by object, not name)."
        if new_palette is self.palette:
            return
        self.palette = new_palette
        self.set_unsaved_changes(True)
    
    def set_active_frame(self, new_frame):
        "Set frame at given index for active editing in Art Mode."
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
        "Set layer at given index for active editing in Art Mode."
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
    
    def mark_frame_changed(self, frame):
        "Given frame at given index as changed for next render."
        for l in [self.char_changed_frames, self.fg_changed_frames,
                  self.bg_changed_frames, self.uv_changed_frames]:
            l.append(frame)
    
    def mark_all_frames_changed(self):
        "Mark all frames as changed for next render."
        for frame in range(self.frames):
            self.mark_frame_changed(frame)
    
    def resize(self, new_width, new_height, origin_x=0, origin_y=0):
        """
        Crop and/or expand Art to new given dimensions, with optional new
        top left tile if cropping. Calls crop() and expand(), so no need to
        call those directly.
        """
        if new_width < self.width or new_height < self.height:
            self.crop(new_width, new_height, origin_x, origin_y)
        if new_width > self.width or new_height > self.height:
            self.expand(new_width, new_height)
        self.width, self.height = new_width, new_height
        # tell all frames they've changed, rebind buffers
        self.geo_changed = True
        self.mark_all_frames_changed()
    
    def build_geo(self):
        """
        (Re)build the vertex and element arrays used by all layers.
        Run if the Art has untracked changes to size or layer count.
        """
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
        "Return given # of layer's worth of vanilla UV array data."
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
        "Return True if given x,y tile coord is within our bounds."
        return 0 <= x < self.width and 0 <= y < self.height
    
    # get methods
    def get_char_index_at(self, frame, layer, x, y):
        "Return character index for given frame/layer/x,y tile."
        return int(self.chars[frame][layer][y][x][0])
    
    def get_fg_color_index_at(self, frame, layer, x, y):
        "Return foreground color index for given frame/layer/x,y tile."
        return int(self.fg_colors[frame][layer][y][x][0])
    
    def get_bg_color_index_at(self, frame, layer, x, y):
        "Return background color index for given frame/layer/x,y tile."
        return int(self.bg_colors[frame][layer][y][x][0])
    
    def get_char_transform_at(self, frame, layer, x, y):
        "Return character transform enum for given frame/layer/x,y tile."
        uvs = self.uv_mods[frame][layer][y][x]
        # use reverse dict of tuples b/c they're hashable
        return uv_types_reverse.get(tuple(uvs), UV_NORMAL)
    
    def get_tile_at(self, frame, layer, x, y):
        """
        Return (char index, fg color index, bg color index, transform) tuple
        for given frame/layer/x,y tile.
        """
        char = self.get_char_index_at(frame, layer, x, y)
        fg = self.get_fg_color_index_at(frame, layer, x, y)
        bg = self.get_bg_color_index_at(frame, layer, x, y)
        xform = self.get_char_transform_at(frame, layer, x, y)
        return char, fg, bg, xform
    
    # set methods
    def set_char_index_at(self, frame, layer, x, y, char_index):
        "Set character index for given frame/layer/x,y tile."
        self.chars[frame][layer][y][x] = char_index
        # next update, tell renderables on the changed frame to update buffers
        if not frame in self.char_changed_frames:
            self.char_changed_frames.append(frame)
    
    def set_color_at(self, frame, layer, x, y, color_index, fg=True):
        """
        Set (fg or bg) color index for given frame/layer/x,y tile.
        Foreground or background specified with "fg" boolean.
        """
        # modulo to resolve any negative indices
        color_index %= len(self.palette.colors)
        # no functional differences between fg and bg color update,
        # so use the same code path with different parameters
        update_array = self.fg_colors[frame] if fg else self.bg_colors[frame]
        update_array[layer][y][x] = color_index
        if fg and not frame in self.fg_changed_frames:
            self.fg_changed_frames.append(frame)
        elif not fg and not frame in self.bg_changed_frames:
            self.bg_changed_frames.append(frame)
    
    def set_all_non_transparent_colors(self, new_color_index):
        """
        Set color index for all non-transparent (index 0) colors on all tiles
        on all frames and layers.
        """
        for frame, layer, x, y in TileIter(self):
            # non-transparent color could be FG or BG
            char, fg, bg, xform = self.get_tile_at(frame, layer, x, y)
            change_fg = bg == 0
            self.set_color_at(frame, layer, x, y, new_color_index, change_fg)
    
    def set_all_bg_colors(self, new_color_index, exclude_layers=[]):
        "Set background color index for all tiles on all frames and layers."
        for frame, layer, x, y in TileIter(self):
            # exclude all layers named in list
            if self.layer_names[layer] in exclude_layers:
                continue
            self.set_color_at(frame, layer, x, y, new_color_index, fg=False)
    
    def set_char_transform_at(self, frame, layer, x, y, transform):
        """
        Set character transform (X/Y flip, 0/90/180/270 rotate) for given
        frame/layer/x,y tile.
        """
        self.uv_mods[frame][layer][y][x] = uv_types[transform]
        if not frame in self.uv_changed_frames:
            self.uv_changed_frames.append(frame)
    
    def set_tile_at(self, frame, layer, x, y, char_index=None, fg=None, bg=None,
                    transform=None):
        """
        Convenience function for setting all tile attributes (character index,
        foreground and background color, and transofmr) at once.
        """
        if char_index is not None:
            self.set_char_index_at(frame, layer, x, y, char_index)
        if fg is not None:
            self.set_color_at(frame, layer, x, y, fg, True)
        if bg is not None:
            self.set_color_at(frame, layer, x, y, bg, False)
        if transform is not None:
            self.set_char_transform_at(frame, layer, x, y, transform)
    
    def shift(self, frame, layer, amount_x, amount_y):
        "Shift + wrap art on given frame and layer by given amount in X and Y."
        for a in [self.chars, self.fg_colors, self.bg_colors, self.uv_mods]:
            a[frame][layer] = np.roll(a[frame][layer], amount_x, 1)
            a[frame][layer] = np.roll(a[frame][layer], amount_y, 0)
        self.mark_frame_changed(frame)
    
    def shift_all_frames(self, amount_x, amount_y):
        "Shift + wrap art in X and Y on all frames and layers."
        for frame in range(self.frames):
            for layer in range(self.layers):
                self.shift(frame, layer, amount_x, amount_y)
    
    def update_saved_camera(self, camera):
        self.camera_x, self.camera_y, self.camera_z = camera.x, camera.y, camera.z
    
    def changed_this_frame(self):
        return self.geo_changed or len(self.char_changed_frames) > 0 or \
            len(self.uv_changed_frames) > 0 or \
            len(self.fg_changed_frames) > 0 or \
            len(self.bg_changed_frames) > 0
    
    def update(self):
        self.update_scripts()
        # update our camera if we're active
        if not self.app.game_mode and self.app.ui and self.app.ui.active_art is self:
            self.update_saved_camera(self.app.camera)
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
            if do_char or do_fg or do_bg or do_uvs:
                r.update_tile_buffers(do_char, do_uvs, do_fg, do_bg)
        # update instances if we chaned
        if self.changed_this_frame() and self.instances:
            for instance in self.instances:
                if instance.update_when_source_changes:
                    instance.restore_from_source()
        # empty lists of changed frames
        self.char_changed_frames, self.uv_changed_frames = [], []
        self.fg_changed_frames, self.bg_changed_frames = [], []
        self.updated_this_tick = True
    
    def save_to_file(self):
        """
        Write this Art to disk.
        Build a dict serializing all this art's data and write it to a file.
        """
        start_time = time.time()
        # cursor might be hovering, undo any preview changes
        for edit in self.app.cursor.preview_edits:
            edit.undo()
        d = {'width': self.width, 'height': self.height,
             'charset': self.charset.name, 'palette': self.palette.name,
             'active_frame': self.active_frame,
             'active_layer': self.active_layer,
             'camera': (self.camera_x, self.camera_y, self.camera_z)
        }
        # preferred character set and palette, default used if not found
        # remember camera location
        # frames and layers are dicts w/ lists of their data + a few properties
        frames = []
        for frame_index in range(self.frames):
            frame = { 'delay': self.frame_delays[frame_index] }
            layers = []
            for layer_index in range(self.layers):
                layer = {'z': self.layers_z[layer_index],
                         'visible': int(self.layers_visibility[layer_index]),
                         'name': self.layer_names[layer_index]
                }
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
        # remove old thumbnail
        thumb_dir = self.app.cache_dir + THUMBNAIL_CACHE_DIR
        if os.path.exists(self.filename):
            old_thumb_filename = thumb_dir + self.app.get_file_hash(self.filename) + '.png'
            if os.path.exists(old_thumb_filename):
                os.remove(old_thumb_filename)
        # MAYBE-TODO: below gives not-so-pretty-printing, find out way to control
        # formatting for better output
        json.dump(d, open(self.filename, 'w'), sort_keys=True, indent=1)
        end_time = time.time()
        self.set_unsaved_changes(False)
        self.app.log('saved %s to disk in %.5f seconds' % (self.filename, end_time - start_time))
        # write thumbnail
        new_thumb_filename = thumb_dir + self.app.get_file_hash(self.filename) + '.png'
        write_thumbnail(self.app, self.filename, new_thumb_filename)
    
    def set_unsaved_changes(self, new_status):
        "Mark this Art as having unsaved changes in Art Mode."
        if new_status == self.unsaved_changes:
            return
        self.unsaved_changes = new_status
        self.app.update_window_title()
    
    def set_filename(self, new_filename):
        "Change Art's filename to new given string."
        # append extension if missing
        if not new_filename.endswith('.' + ART_FILE_EXTENSION):
            new_filename += '.' + ART_FILE_EXTENSION
        # if no dir given, assume documents/art/ dir
        if os.path.basename(new_filename) == new_filename:
            new_dir = self.app.documents_dir
            # documents/game/art if game loaded
            if self.app.gw.game_dir is not None:
                new_dir = self.app.gw.game_dir
            new_dir += ART_DIR
            new_filename = new_dir + new_filename
        # TODO: check if file already exists? warn user?
        # (probably better to do this in new art / save as
        self.filename = new_filename
    
    def run_script(self, script_filename):
        """
        Run a script on this Art. Scripts contain arbitrary python expressions,
        executed within Art's scope. Don't run art scripts you don't trust!
        """
        script_filename = self.get_valid_script_filename(script_filename)
        if not script_filename:
            return
        exec(open(script_filename).read())
        # assume script will change art
        self.unsaved_changes = True
        self.app.log('Executed %s' % script_filename)
    
    def is_script_running(self, script_filename):
        "Return True if script with given filename is currently running."
        script_filename = self.get_valid_script_filename(script_filename)
        return script_filename and script_filename in self.scripts
    
    def get_valid_script_filename(self, script_filename):
        if not type(script_filename) is str: return None
        return self.app.find_filename_path(script_filename, ART_SCRIPT_DIR,
                                           SCRIPT_FILE_EXTENSION)
    
    def run_script_every(self, script_filename, rate=0.1):
        "Start a script running on this Art at a regular rate."
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
        next_run = (self.app.get_elapsed_time() / 1000) + rate
        self.scripts_next_exec_time.append(next_run)
    
    def stop_script(self, script_filename):
        "Halt this Art's execution of script with given filename."
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
    
    def stop_all_scripts(self):
        "Halt all art scripts executing on this Art."
        for script_filename in self.scripts:
            self.stop_script(script_filename)
    
    def update_scripts(self):
        if len(self.scripts) == 0:
            return
        # don't run on game art while paused
        if self.app.game_mode and self.app.gw.paused:
            return
        for i,script in enumerate(self.scripts):
            if (self.app.get_elapsed_time() / 1000) > self.scripts_next_exec_time[i]:
                exec(open(script).read())
                self.unsaved_changes = True
                self.scripts_next_exec_time[i] += self.script_rates[i]
    
    def clear_line(self, frame, layer, line_y, fg_color_index=None,
                   bg_color_index=None):
        "Clear characters on given horizontal line, to optional given colors."
        # TODO: use numpy slicing to do this much more quickly!
        for x in range(self.width):
            self.set_char_index_at(frame, layer, x, line_y, 0)
            if fg_color_index:
                self.set_color_at(frame, layer, x, line_y, fg_color_index)
            if bg_color_index:
                self.set_color_at(frame, layer, x, line_y, bg_color_index, False)
    
    def write_string(self, frame, layer, x, y, text, fg_color_index=None,
                     bg_color_index=None, right_justify=False):
        """
        Write given string starting at given frame/layer/x,y tile, with
        optional given colors, left-justified by default.
        Any characters not in character set's mapping data are ignored.
        """
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
    
    def get_filtered_tiles(self, frame, layer, char_value, invert_filter=False):
        "Return list of (x,y) tile coords that match (or don't) a char value."
        tiles = []
        for y in range(self.height):
            for x in range(self.width):
                char = self.get_char_index_at(frame, layer, x, y)
                if (not invert_filter and char == char_value) or \
                   (invert_filter and char != char_value):
                    tiles.append((x, y))
        return tiles
    
    def get_blank_tiles(self, frame, layer):
        "Return a list of (x,y) tile coords whose character is blank (0)."
        return self.get_filtered_tiles(frame, layer, 0)
    
    def get_nonblank_tiles(self, frame, layer):
        "Return a list of (x,y) tile coords whose character is NOT blank (0)."
        return self.get_filtered_tiles(frame, layer, 0, invert_filter=True)


class ArtFromDisk(Art):
    "Subclass of Art that loads from a file. Main difference is initialization."
    def __init__(self, filename, app):
        self.valid = False
        try:
            d = json.load(open(filename))
        except:
            return
        width = d['width']
        height = d['height']
        charset = app.load_charset(d['charset'])
        if not charset:
            app.log('Character set %s not found!' % d['charset'])
            return
        palette = app.load_palette(d['palette'])
        if not palette:
            app.log('Palette %s not found!' % d['palette'])
            return
        # store loaded data for init_layers/frames
        self.loaded_data = d
        # base Art class initializes all vars, thereafter we just populate
        Art.__init__(self, filename, app, charset, palette,
                     width, height)
        # still loading...
        self.valid = False
        if not self.app.override_saved_camera:
            cam = d['camera']
            self.camera_x, self.camera_y, self.camera_z = cam[0], cam[1], cam[2]
        else:
            self.update_saved_camera(self.app.camera)
        # update renderables with new data
        self.update()
        # signify to app that this file loaded successfully
        self.valid = True
    
    def log_init(self):
        self.app.log('Loaded %s from disk:' % filename)
        self.app.log('  character set: %s' % self.charset.name)
        self.app.log('  palette: %s' % self.palette.name)
        self.app.log('  width/height: %s x %s' % (self.width, self.height))
        self.app.log('  frames: %s' % self.frames)
        self.app.log('  layers: %s' % self.layers)
    
    def init_layers(self):
        frames = self.loaded_data['frames']
        # number of layers should be same for all frames
        self.layers = len(frames[0]['layers'])
        self.layers_z, self.layers_visibility, self.layer_names = [], [], []
        for i,layer in enumerate(frames[0]['layers']):
            self.layers_z.append(layer['z'])
            self.layers_visibility.append(bool(layer.get('visible', 1)))
            layer_num = str(i + 1)
            self.layer_names.append(layer.get('name', 'Layer %s' % layer_num))
        active_layer = self.loaded_data.get('active_layer', 0)
        self.set_active_layer(active_layer)
    
    def init_frames(self):
        frames = self.loaded_data['frames']
        self.frames = len(frames)
        self.active_frame = 0
        self.frame_delays = []
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
        # set active frame properly
        active_frame = self.loaded_data.get('active_frame', 0)
        self.set_active_frame(active_frame)
    
    def first_update(self):
        # do nothing on first update during Art.init; we update after loading
        pass


class ArtInstance(Art):
    """
    Deep copy / clone of a source Art that can hold unique changes and be
    restored to its source.
    """
    update_when_source_changes = True
    "Set False if you want to manually update this Art."
    def __init__(self, source):
        self.source = source
        # unique(?) filename
        self.filename = '%s_Instance%i' % (source.filename, time.time())
        self.app = source.app
        self.instances = None
        self.char_changed_frames, self.uv_changed_frames = [], []
        self.fg_changed_frames, self.bg_changed_frames = [], []
        # init lists that should be retained across refreshes
        self.scripts = []
        self.script_rates = []
        self.scripts_next_exec_time = []
        self.renderables = []
        self.restore_from_source()
        self.source.instances.append(self)
    
    def set_unsaved_changes(self, new_status):
        pass
    
    def restore_from_source(self):
        "Restore ArtInstance to its source Art's new values."
        # copy common references/values
        for prop in ['app', 'width', 'height', 'charset', 'palette',
                     'quad_width', 'quad_height', 'layers', 'frames']:
            setattr(self, prop, getattr(self.source, prop))
        # copy lists
        self.layers_z = self.source.layers_z[:]
        self.layers_visibility = self.source.layers_visibility[:]
        self.layer_names = self.source.layer_names[:]
        self.frame_delays = self.source.frame_delays[:]
        # deep copy tile data lists
        self.chars, self.uv_mods, self.fg_colors, self.bg_colors = [],[],[],[]
        for frame_chars in self.source.chars:
            self.chars.append(frame_chars.copy())
        for frame_uvs in self.source.uv_mods:
            self.uv_mods.append(frame_uvs.copy())
        for frame_fg_colors in self.source.fg_colors:
            self.fg_colors.append(frame_fg_colors.copy())
        for frame_bg_colors in self.source.bg_colors:
            self.bg_colors.append(frame_bg_colors.copy())
        self.geo_changed = True
        self.mark_all_frames_changed()
        self.update()


class ArtFromEDSCII(Art):
    """
    File loader for legacy EDSCII format.
    Assumes single frames, single layer, default charset and palette.
    """
    # TODO: make this init more like ArtFromDisk, ie use mostly Art.init
    def __init__(self, filename, app, width_override=None):
        # once load process is complete set this true to signify valid data
        self.valid = False
        try:
            data = open(filename, 'rb').read()
        except:
            return
        self.filename = '%s.%s' % (os.path.splitext(filename)[0], ART_FILE_EXTENSION)
        self.app = app
        self.time_loaded = 0
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
        self.layers_visibility = [True]
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


class TileIter:
    "Iterator for iterating over all tiles in all layers and frames in an Art."
    def __init__(self, art):
        self.width, self.height = art.width, art.height
        self.frames, self.layers = art.frames, art.layers
    
    def __iter__(self):
        self.frame, self.layer = 0, 0
        self.x, self.y = -1, 0
        return self
    
    def __next__(self):
        self.x += 1
        if self.x >= self.width:
            self.x = 0
            self.y += 1
        if self.y >= self.height:
            self.y = 0
            self.layer += 1
        if self.layer >= self.layers:
            self.layer = 0
            self.frame += 1
        if self.frame >= self.frames:
            raise StopIteration
        return self.frame, self.layer, self.x, self.y
