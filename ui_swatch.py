import math, time
import numpy as np

from ui_element import UIElement, UIArt, UIRenderable
from renderable_line import LineRenderable, SelectionBoxRenderable, UIRenderableX

class UISwatch(UIElement):
    
    def __init__(self, ui, popup):
        self.ui = ui
        self.popup = popup
        self.renderable = None
        self.reset()
    
    def reset(self):
        self.tile_width, self.tile_height = self.get_size()
        art = self.ui.active_art
        # generate a unique name for debug purposes
        art_name = '%s_%s' % (int(time.time()), self.__class__.__name__)
        self.art = UIArt(art_name, self.ui.app, art.charset, art.palette, self.tile_width, self.tile_height)
        if self.renderable:
            self.renderable.destroy()
        self.renderable = UIRenderable(self.ui.app, self.art)
        self.renderable.ui = self.ui
        self.renderable.grain_strength = 0
        self.reset_art()
    
    def reset_art(self):
        pass
    
    def get_size(self):
        return 1, 1
    
    def set_cursor_loc(self, cursor, mouse_x, mouse_y):
        """
        common, generalized code for both character and palette swatches:
        set cursor's screen location, tile location, and quad size.
        """
        # get location within char map
        w, h = self.art.quad_width, self.art.quad_height
        tile_x = (mouse_x - self.x) / w
        tile_y = (mouse_y - self.y) / h
        # snap to tile
        tile_x = int(math.floor(tile_x / w) * w)
        tile_y = int(math.ceil(tile_y / h) * h)
        # back to screen coords
        x = tile_x * w + self.x
        y = (tile_y - 1) * h + self.y
        tile_index = (abs(tile_y) * self.art.width) + tile_x
        # if a valid character isn't hovered, bail
        if not self.is_selection_index_valid(tile_index):
            self.set_cursor_selection_index(-1)
            return
        # cool, set cursor location & size
        self.set_cursor_selection_index(tile_index)
        cursor.quad_size_ref = self.art
        cursor.tile_x = cursor.tile_y = tile_x, tile_y
        cursor.x, cursor.y = x, y
    
    def is_selection_index_valid(self, index):
        "returns True if given index is valid for choices this swatch offers"
        return False
    
    def set_cursor_selection_index(self, index):
        "another set_cursor_loc support method, overriden by subclasses"
        self.popup.blah = index
    
    def render(self, elapsed_time):
        self.renderable.render(elapsed_time)


class CharacterSetSwatch(UISwatch):
    
    # scale the character set will be drawn at
    char_scale = 3
    
    def __init__(self, ui, popup):
        UISwatch.__init__(self, ui, popup)
        self.selection_box = SelectionBoxRenderable(ui.app, self.art)
        self.grid = CharacterGridRenderable(ui.app, self.art)
    
    def get_size(self):
        art = self.ui.active_art
        return art.charset.map_width, art.charset.map_height
    
    def reset_art(self):
        # TODO: using screen resolution, try to set quad size to an even
        # multiple of screen so the sampling doesn't get chunky
        aspect = self.ui.app.window_width / self.ui.app.window_height
        charset = self.art.charset
        self.art.quad_width = UIArt.quad_width * self.char_scale
        self.art.quad_height = self.art.quad_width * (charset.char_height / charset.char_width) * aspect
        # only need to populate characters on reset_art, but update
        # colors every update()
        self.art.clear_frame_layer(0, 0, 0)
        i = 0
        for y in range(charset.map_height):
            for x in range(charset.map_width):
                self.art.set_char_index_at(0, 0, x, y, i)
                i += 1
        self.art.geo_changed = True
    
    def reset_loc(self):
        self.x = self.popup.x + self.popup.swatch_margin
        self.y = self.popup.y
        self.y -= self.popup.art.quad_height * 3
        self.renderable.x, self.renderable.y = self.x, self.y
        self.grid.x, self.grid.y = self.x, self.y
        self.grid.y -= self.art.quad_height
    
    def is_selection_index_valid(self, index):
        return index < self.art.charset.last_index
    
    def set_cursor_selection_index(self, index):
        self.popup.cursor_char = index
        self.popup.cursor_color = -1
    
    def update(self):
        charset = self.ui.active_art.charset
        fg, bg = self.ui.selected_fg_color, self.ui.selected_bg_color
        # repopulate colors every update
        for y in range(charset.map_height):
            for x in range(charset.map_width):
                self.art.set_tile_at(0, 0, x, y, None, fg, bg)
        self.art.update()
        # selection box color
        elapsed_time = self.ui.app.elapsed_time
        color = 0.75 + (math.sin(elapsed_time / 100) / 2)
        self.selection_box.color = (color, color) * 2
        # set cursor color here rather than doin sin(time) again in popup update
        self.popup.cursor_box.color = (color, color) * 2
        # position
        self.selection_box.x = self.renderable.x
        selection_x = self.ui.selected_char % charset.map_width
        self.selection_box.x += selection_x * self.art.quad_width
        self.selection_box.y = self.renderable.y
        selection_y = (self.ui.selected_char - selection_x) / charset.map_width
        self.selection_box.y -= (selection_y + 1) * self.art.quad_height
    
    def render(self, elapsed_time):
        UISwatch.render(self, elapsed_time)
        self.grid.render(elapsed_time)
        self.selection_box.render(elapsed_time)


class PaletteSwatch(UISwatch):
    
    def __init__(self, ui, popup):
        UISwatch.__init__(self, ui, popup)
        self.transparent_x = UIRenderableX(ui.app, self.art)
        self.fg_selection_box = SelectionBoxRenderable(ui.app, self.art)
        self.bg_selection_box = SelectionBoxRenderable(ui.app, self.art)
        # F label for FG color selection
        self.f_art = ColorSelectionLabelArt(ui, 'F')
        self.f_renderable = ColorSelectionLabelRenderable(ui.app, self.f_art)
        self.f_renderable.ui = ui
        # B label for BG color seletion
        self.b_art = ColorSelectionLabelArt(ui, 'B')
        self.b_renderable = ColorSelectionLabelRenderable(ui.app, self.b_art)
        self.b_renderable.ui = ui
    
    def get_size(self):
        # TODO: make colors bigger if palette is small enough
        return len(self.ui.active_art.palette.colors), 1
    
    def reset_art(self):
        # TODO: if # of colors in palette is reasonable, make palette quads
        # double sized, taking up more lines as needed
        cqw, cqh = self.popup.charset_swatch.art.quad_width, self.popup.charset_swatch.art.quad_height
        self.art.quad_width = cqw
        self.art.quad_height = cqh
        self.art.clear_frame_layer(0, 0, 0)
        palette = self.ui.active_art.palette
        for x in range(len(palette.colors)):
            self.art.set_color_at(0, 0, x, 0, x, False)
        self.art.geo_changed = True
    
    def reset_loc(self):
        self.x = self.popup.x + self.popup.swatch_margin
        self.y = self.popup.charset_swatch.renderable.y
        self.y -= self.art.quad_height * self.ui.active_art.charset.map_height
        self.y -= self.popup.art.quad_height * 2
        self.renderable.x, self.renderable.y = self.x, self.y
        # first color in palette (top left) always transparent
        self.transparent_x.x = self.renderable.x
        self.transparent_x.y = self.renderable.y - self.art.quad_height
        # set f/b_art's quad size
        self.f_art.quad_width, self.f_art.quad_height = self.b_art.quad_width, self.b_art.quad_height = self.popup.art.quad_width, self.popup.art.quad_height
        self.f_art.geo_changed = True
        self.b_art.geo_changed = True
    
    def is_selection_index_valid(self, index):
        return index < len(self.art.palette.colors)
    
    def set_cursor_selection_index(self, index):
        self.popup.cursor_color = index
        self.popup.cursor_char = -1
    
    def update(self):
        self.art.update()
        self.f_art.update()
        self.b_art.update()
        # color selection boxes
        elapsed_time = self.ui.app.elapsed_time
        color = 0.75 + (math.sin(elapsed_time / 100) / 2)
        self.fg_selection_box.color = (color, color) * 2
        self.bg_selection_box.color = (color, color) * 2
        # fg selection box position
        # TODO: redo when palette takes multiple rows
        self.fg_selection_box.x = self.renderable.x
        self.fg_selection_box.x += self.art.quad_width * self.ui.selected_fg_color
        self.fg_selection_box.y = self.renderable.y - self.art.quad_height
        # bg box position
        self.bg_selection_box.x = self.renderable.x
        self.bg_selection_box.x += self.art.quad_width * self.ui.selected_bg_color
        self.bg_selection_box.y = self.renderable.y - self.art.quad_height
        # FG label position
        self.f_renderable.alpha = 1 - color
        self.f_renderable.x = self.fg_selection_box.x
        self.f_renderable.y = self.renderable.y
        # center
        x_offset = (self.art.quad_width - self.popup.art.quad_width) / 2
        y_offset = (self.art.quad_height - self.popup.art.quad_height) / 2
        self.f_renderable.x += x_offset
        self.f_renderable.y -= y_offset
        # BG label position
        self.b_renderable.alpha = 1 - color
        self.b_renderable.x = self.bg_selection_box.x
        self.b_renderable.y = self.renderable.y
        self.b_renderable.x += x_offset
        self.b_renderable.y -= y_offset
    
    def render(self, elapsed_time):
        UISwatch.render(self, elapsed_time)
        self.transparent_x.render(elapsed_time)
        self.fg_selection_box.render(elapsed_time)
        self.bg_selection_box.render(elapsed_time)
        self.f_renderable.render(elapsed_time)
        self.b_renderable.render(elapsed_time)


class ColorSelectionLabelArt(UIArt):
    def __init__(self, ui, letter):
        letter_index = ui.charset.get_char_index(letter)
        art_name = '%s_%s' % (int(time.time()), self.__class__.__name__)
        UIArt.__init__(self, art_name, ui.app, ui.charset, ui.palette, 1, 1)
        label_color = ui.palette.lightest_index
        label_bg_color = 0
        self.set_tile_at(0, 0, 0, 0, letter_index, label_color, label_bg_color)


class ColorSelectionLabelRenderable(UIRenderable):
    # transparent background so we can see the swatch color behind it
    bg_alpha = 0


class CharacterGridRenderable(LineRenderable):
    color = (0.5, 0.5, 0.5, 0.25)
    def build_geo(self):
        w, h = self.quad_size_ref.width, self.quad_size_ref.height
        v = []
        e = []
        c = self.color * 4 * w * h
        index = 0
        for x in range(1, w):
            v += [(x, -h+1), (x, 1)]
            e += [index, index+1]
            index += 2
        for y in range(h-1):
            v += [(w, -y), (0, -y)]
            e += [index, index+1]
            index += 2
        self.vert_array = np.array(v, dtype=np.float32)
        self.elem_array = np.array(e, dtype=np.uint32)
        self.color_array = np.array(c, dtype=np.float32)
