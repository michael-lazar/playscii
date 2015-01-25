import math
import numpy as np

from ui_element import UIElement, UIArt, UIRenderable, UIRenderableX
from renderable_line import LineRenderable

TAB_TOOLS = 0
TAB_CHAR_COLOR = 1

class ToolPopup(UIElement):
    
    visible = False
    width, height = 20, 15
    swatch_margin = 0.05
    tool_tab_label = 'Tools'
    char_color_tab_label = 'Chars/Colors'
    unselected_tab_color = 15
    
    def __init__(self, ui):
        self.charset_swatch = CharacterSetSwatch(ui, self)
        self.palette_swatch = PaletteSwatch(ui, self)
        # set which tab is "active"
        self.active_tab = TAB_CHAR_COLOR
        UIElement.__init__(self, ui)
    
    def reset_art(self):
        self.charset_swatch.reset_art()
        self.palette_swatch.reset_art()
        # set panel size based on charset size
        fg = self.ui.palette.darkest_index
        bg = self.ui.palette.lightest_index
        margin = self.swatch_margin * 2
        charset = self.ui.active_art.charset
        palette = self.ui.active_art.palette
        cqw, cqh = self.charset_swatch.art.quad_width, self.charset_swatch.art.quad_height
        self.width = (cqw * charset.map_width + margin) / UIArt.quad_width
        self.height = (cqh * charset.map_height + margin) / UIArt.quad_height + 6
        self.art.resize(int(self.width), int(self.height), bg)
        # panel text
        self.art.clear_frame_layer(0, 0, bg)
        # tab captions
        tab_width = int(self.width / 2)
        # tools
        if self.active_tab == TAB_CHAR_COLOR:
            bg = self.unselected_tab_color
        label = ('   %s' % self.tool_tab_label).ljust(tab_width)
        self.art.write_string(0, 0, 0, 0, label, fg, bg)
        # char/color picker
        bg = self.ui.palette.lightest_index
        if self.active_tab == TAB_TOOLS:
            bg = self.unselected_tab_color
        label = ('%s   ' % self.char_color_tab_label).rjust(tab_width)
        self.art.write_string(0, 0, tab_width + 1, 0, label, fg, bg)
        # charset renderable location will be set in update()
        # charset label
        self.art.write_string(0, 0, 2, 2, 'Character Set: %s' % charset.name, fg)
        # palette label
        pal_caption_y = (cqh * charset.map_height) / self.art.quad_height
        pal_caption_y += 4
        self.art.write_string(0, 0, 2, int(pal_caption_y), 'Color Palette: %s' % palette.name, fg)
        self.art.geo_changed = True
    
    def show(self):
        # if already visible, bail - key repeat probably triggered this
        if self.visible:
            return
        self.visible = True
        self.reset_loc()
    
    def reset_loc(self):
        x = (2 * self.ui.app.mouse_x) / self.ui.app.window_width - 1
        y = (-2 * self.ui.app.mouse_y) / self.ui.app.window_height + 1
        charset = self.ui.active_art.charset
        # TODO: try to position popup center near mouse
        cqw, cqh = self.charset_swatch.art.quad_width, self.charset_swatch.art.quad_height
        w = cqw * charset.map_width + self.swatch_margin * 2
        x -= w / 2
        # TODO: store charset and palette dimensions in reset_art so we don't
        # have to recalc them here!
        h = cqh * charset.map_height
        y += h / 2
        # clamp to edges of screen
        x = max(-1, min(1 - w, x))
        y = min(1, max(-1 + h, y))
        # set location for main renderable and sub elements
        self.x, self.y = x, y
        self.renderable.x, self.renderable.y = x, y
        self.charset_swatch.reset_loc()
        self.palette_swatch.reset_loc()
    
    def hide(self):
        self.visible = False
    
    def update(self):
        self.art.update()
        self.charset_swatch.update()
        self.palette_swatch.update()
    
    def render(self, elapsed_time):
        UIElement.render(self, elapsed_time)
        self.charset_swatch.render(elapsed_time)
        self.palette_swatch.render(elapsed_time)


class UISwatch():
    
    def __init__(self, ui, popup):
        self.ui = ui
        self.popup = popup
        self.width, self.height = self.get_size()
        art = self.ui.active_art
        self.art = UIArt(None, self.ui.app, art.charset, art.palette, self.width, self.height)
        self.renderable = UIRenderable(self.ui.app, self.art)
        self.renderable.ui = self.ui
        self.renderable.grain_strength = 0
        self.reset_art()
    
    def reset_art(self):
        pass
    
    def get_size(self):
        return 1, 1
    
    def render(self, elapsed_time):
        self.renderable.render(elapsed_time)


class CharacterSetSwatch(UISwatch):
    
    # scale the character set will be drawn at
    char_scale = 2
    
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
        self.renderable.x = self.popup.x + self.popup.swatch_margin
        self.renderable.y = self.popup.y
        self.renderable.y -= self.popup.art.quad_height * 3
        self.grid.x, self.grid.y = self.renderable.x, self.renderable.y
        self.grid.y -= self.art.quad_height
    
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
        self.renderable.x = self.popup.x + self.popup.swatch_margin
        self.renderable.y = self.popup.charset_swatch.renderable.y
        self.renderable.y -= self.art.quad_height * self.ui.active_art.charset.map_height
        self.renderable.y -= self.popup.art.quad_height * 2
        # first color in palette (top left) always transparent
        self.transparent_x.x = self.renderable.x
        self.transparent_x.y = self.renderable.y - self.art.quad_height
    
    def update(self):
        self.art.update()
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
        center_offset = (self.art.quad_width - self.popup.art.quad_width) / 2
        self.f_renderable.x += center_offset
        # BG label position
        self.b_renderable.alpha = 1 - color
        self.b_renderable.x = self.bg_selection_box.x
        self.b_renderable.y = self.renderable.y
        self.b_renderable.x += center_offset
    
    def render(self, elapsed_time):
        UISwatch.render(self, elapsed_time)
        self.transparent_x.render(elapsed_time)
        self.fg_selection_box.render(elapsed_time)
        self.bg_selection_box.render(elapsed_time)
        self.f_renderable.render(elapsed_time)
        self.b_renderable.render(elapsed_time)


class SelectionBoxRenderable(LineRenderable):
    
    color = (0.5, 0.5, 0.5, 1)
    
    def get_color(self, elapsed_time):
        return self.color
    
    def build_geo(self):
        self.vert_array = np.array([(0, 0), (1, 0), (1, 1), (0, 1)], dtype=np.float32)
        self.elem_array = np.array([0, 1, 1, 2, 2, 3, 3, 0], dtype=np.uint32)
        self.color_array = np.array([self.color * 4], dtype=np.float32)


class ColorSelectionLabelArt(UIArt):
    def __init__(self, ui, letter):
        letter_index = ui.charset.get_char_index(letter)
        UIArt.__init__(self, None, ui.app, ui.charset, ui.palette, 1, 1)
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
