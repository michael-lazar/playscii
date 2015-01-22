from math import ceil

from ui_element import UIElement, UIArt, UIRenderable

class StatusBarUI(UIElement):
    
    snap_bottom = True
    snap_left = True
    char_label = 'ch:'
    fg_label = 'fg:'
    bg_label = 'bg:'
    swatch_width = 3
    char_label_x = 2
    char_swatch_x = char_label_x + len(char_label)
    fg_label_x = char_swatch_x + swatch_width + 2
    fg_swatch_x = fg_label_x + len(fg_label)
    bg_label_x = fg_swatch_x + swatch_width + 2
    bg_swatch_x = bg_label_x + len(bg_label)
    
    def __init__(self, ui):
        UIElement.__init__(self, ui)
        art = self.ui.active_art
        # create 3 custom Arts w/ source charset and palette, renderables for each
        self.char_art = UIArt(None, ui.app, art.charset, art.palette, self.swatch_width, 1)
        self.char_renderable = UIRenderable(ui.app, self.char_art)
        self.fg_art = UIArt(None, ui.app, art.charset, art.palette, self.swatch_width, 1)
        self.fg_renderable = UIRenderable(ui.app, self.fg_art)
        self.bg_art = UIArt(None, ui.app, art.charset, art.palette, self.swatch_width, 1)
        self.bg_renderable = UIRenderable(ui.app, self.bg_art)
        # set some properties in bulk
        for r in [self.char_renderable, self.fg_renderable, self.bg_renderable]:
            r.ui = self.ui
            r.grain_strength = 0
    
    def reset_art(self):
        self.width = ceil(self.ui.width_tiles)
        # must resize here, as window width will vary
        self.art.resize(self.width, self.height)
        bg = self.ui.palette.lightest_index
        self.art.clear_frame_layer(0, 0, bg)
        color = self.ui.palette.darkest_index
        
        self.art.write_string(0, 0, self.char_label_x, 0, self.char_label, color)
        self.art.write_string(0, 0, self.fg_label_x, 0, self.fg_label, color)
        self.art.write_string(0, 0, self.bg_label_x, 0, self.bg_label, color)
        self.art.geo_changed = True
    
    def update(self):
        # set color swatches
        for i in range(self.swatch_width):
            self.char_art.set_color_at(0, 0, i, 0, self.ui.selected_bg_color, False)
            self.fg_art.set_color_at(0, 0, i, 0, self.ui.selected_fg_color, False)
            self.bg_art.set_color_at(0, 0, i, 0, self.ui.selected_bg_color, False)
        # set char w/ correct FG color
        self.char_art.set_char_index_at(0, 0, 1, 0, self.ui.selected_char)
        self.char_art.set_color_at(0, 0, 1, 0, self.ui.selected_fg_color, True)
        # position elements
        self.position_swatch(self.char_renderable, self.char_swatch_x)
        self.position_swatch(self.fg_renderable, self.fg_swatch_x)
        self.position_swatch(self.bg_renderable, self.bg_swatch_x)
        for art in [self.char_art, self.fg_art, self.bg_art]:
            art.update()
    
    def position_swatch(self, renderable, x_offset):
        # TODO: this is bugged, swatches get too big as window gets wider
        aspect = self.ui.app.window_width / self.ui.app.window_height
        inv_aspect = 1 / aspect
        renderable.x = (self.char_art.quad_width * x_offset) - 1
        renderable.y = self.char_art.quad_height - 1
    
    def reset_loc(self):
        UIElement.reset_loc(self)
    
    def render(self, elapsed_time):
        UIElement.render(self, elapsed_time)
        self.char_renderable.render(elapsed_time)
        self.fg_renderable.render(elapsed_time)
        self.bg_renderable.render(elapsed_time)
