import numpy as np
from PIL import Image
from OpenGL import GL

from texture import Texture
from ui_element import UIArt, FPSCounterUI
from ui_console import ConsoleUI
from ui_status_bar import StatusBarUI
from ui_popup import ToolPopup

UI_ASSET_DIR = 'ui/'
SCALE_INCREMENT = 0.25

class UI:
    
    # user-configured UI scale factor
    scale = 1.0
    charset_name = 'ui'
    palette_name = 'c64'
    # low-contrast background texture that distinguishes UI from flat color
    grain_texture = 'bgnoise_alpha.png'
    visible = True
    
    def __init__(self, app, active_art):
        self.app = app
        # the current art being edited
        self.active_art = active_art
        self.active_frame = 0
        self.active_layer = 0
        # for UI, view /and/ projection matrix are identity
        # (aspect correction is done in set_scale)
        self.view_matrix = np.eye(4, 4, dtype=np.float32)
        self.charset = self.app.load_charset(self.charset_name, False)
        self.palette = self.app.load_palette(self.palette_name, False)
        # currently selected char, fg color, bg color
        art_char = self.active_art.charset
        art_pal = self.active_art.palette
        self.selected_char = art_char.get_char_index('A') or 2
        self.selected_fg_color = art_pal.lightest_index
        self.selected_bg_color = art_pal.darkest_index
        # create elements
        self.elements = []
        # set geo sizes, force scale update
        self.set_scale(self.scale)
        fps_counter = FPSCounterUI(self)
        self.console = ConsoleUI(self)
        self.status_bar = StatusBarUI(self)
        self.popup = ToolPopup(self)
        self.elements.append(fps_counter)
        self.elements.append(self.status_bar)
        self.elements.append(self.console)
        self.elements.append(self.popup)
        # grain texture
        img = Image.open(UI_ASSET_DIR + self.grain_texture)
        img = img.convert('RGBA')
        width, height = img.size
        self.grain_texture = Texture(img.tostring(), width, height)
        self.grain_texture.set_wrap(GL.GL_REPEAT)
        self.grain_texture.set_filter(GL.GL_LINEAR, GL.GL_LINEAR_MIPMAP_LINEAR)
        # update elements that weren't created when UI scale was determined
        self.set_elements_scale()
    
    def set_scale(self, new_scale):
        old_scale = self.scale
        self.scale = new_scale
        # update UI renderable geo sizes for new scale
        # determine width and height of current window in chars
        # use floats, window might be a fractional # of chars wide/tall
        aspect = self.app.window_width / self.app.window_height
        inv_aspect = self.app.window_height / self.app.window_width
        # TODO: this math is correct but hard to follow, rewrite for clarity
        width = self.app.window_width / (self.charset.char_width * self.scale * inv_aspect)
        height = self.app.window_height / (self.charset.char_height * self.scale * inv_aspect)
        # any new UI elements created should use new scale
        UIArt.quad_width = 2 / width * aspect
        UIArt.quad_height = 2 / height * aspect
        self.width_tiles = width * inv_aspect / self.scale
        self.height_tiles = height / self.scale
        # tell elements to refresh
        self.set_elements_scale()
        if self.scale != old_scale:
            self.app.log('UI scale is now %s (%.3f x %.3f)' % (self.scale, self.width_tiles, self.height_tiles))
    
    def set_elements_scale(self):
        for e in self.elements:
            e.art.quad_width, e.art.quad_height = UIArt.quad_width, UIArt.quad_height
            # Art dimensions may well need to change
            e.reset_art()
            e.reset_loc()
            e.art.geo_changed = True
    
    def window_resized(self):
        # recalc renderables' quad size (same scale, different aspect)
        self.set_scale(self.scale)
    
    def set_active_frame(self, new_frame):
        new_frame %= self.active_art.frames
        # bail if frame is still the same, eg we only have 1 frame
        if new_frame == self.active_frame:
            return
        self.active_frame = new_frame
        # update active art's renderables
        for r in self.active_art.renderables:
            r.set_frame(self.active_frame)
    
    def set_active_layer(self, new_layer):
        self.active_layer = min(max(0, new_layer), self.active_art.layers-1)
        self.app.grid.z = self.active_art.layers_z[self.active_layer]
        self.app.cursor.z = self.active_art.layers_z[self.active_layer]
        self.app.update_window_title()
    
    def select_char(self, new_char_index):
        # wrap at last valid index
        self.selected_char = new_char_index % self.active_art.charset.last_index
    
    def select_color(self, new_color_index, fg):
        "common code for select_fg/bg"
        new_color_index %= len(self.active_art.palette.colors)
        if fg:
            self.selected_fg_color = new_color_index
        else:
            self.selected_bg_color = new_color_index
    
    def select_fg(self, new_fg_index):
        self.select_color(new_fg_index, True)
    
    def select_bg(self, new_bg_index):
        self.select_color(new_bg_index, False)
    
    def update(self):
        for e in self.elements:
            e.update()
            # art update: tell renderables to refresh buffers
            e.art.update()
    
    def clicked(self, button):
        pass
    
    def unclicked(self, button):
        pass
    
    def DBG_paint(self):
        "simple quick function to test painting"
        x, y = self.app.cursor.get_tile()
        # don't allow painting out of bounds
        if not self.active_art.is_tile_inside(x, y):
            return
        self.active_art.set_tile_at(0, self.active_layer, x, y, self.selected_char, self.selected_fg_color, self.selected_bg_color)
    
    def DBG_grab(self):
        x, y = self.app.cursor.get_tile()
        if not self.active_art.is_tile_inside(x, y):
            return
        self.selected_char = self.active_art.get_char_index_at(0, self.active_layer, x, y)
        self.selected_fg_color = self.active_art.get_fg_color_index_at(0, self.active_layer, x, y)
        self.selected_bg_color = self.active_art.get_bg_color_index_at(0, self.active_layer, x, y)
    
    def destroy(self):
        for e in self.elements:
            e.renderable.destroy()
        self.grain_texture.destroy()
    
    def render(self, elapsed_time):
        for e in self.elements:
            if e.visible:
                e.render(elapsed_time)