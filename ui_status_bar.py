import os.path
from math import ceil

from ui_element import UIElement, UIArt, UIRenderable

class StatusBarUI(UIElement):
    
    snap_bottom = True
    snap_left = True
    dim_color = 7
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
    tool_label = 'tool:'
    tool_label_x = bg_swatch_x + swatch_width + 2
    tool_selection_x = tool_label_x + len(tool_label)
    tile_label = 'tile:'
    layer_label = 'layer:'
    frame_label = 'frame:'
    
    def __init__(self, ui):
        art = ui.active_art
        # create 3 custom Arts w/ source charset and palette, renderables for each
        self.char_art = UIArt(None, ui.app, art.charset, art.palette, self.swatch_width, 1)
        self.char_renderable = UIRenderable(ui.app, self.char_art)
        self.fg_art = UIArt(None, ui.app, art.charset, art.palette, self.swatch_width, 1)
        self.fg_renderable = UIRenderable(ui.app, self.fg_art)
        self.bg_art = UIArt(None, ui.app, art.charset, art.palette, self.swatch_width, 1)
        self.bg_renderable = UIRenderable(ui.app, self.bg_art)
        # set some properties in bulk
        for r in [self.char_renderable, self.fg_renderable, self.bg_renderable]:
            r.ui = ui
            r.grain_strength = 0
        UIElement.__init__(self, ui)
    
    def reset_art(self):
        self.width = ceil(self.ui.width_tiles)
        # must resize here, as window width will vary
        self.art.resize(self.width, self.height)
        # write chars/colors to the art
        self.rewrite_art()
        self.art.geo_changed = True
        self.char_art.geo_changed = True
        self.fg_art.geo_changed = True
        self.bg_art.geo_changed = True
    
    def rewrite_art(self):
        bg = self.ui.palette.lightest_index
        self.art.clear_frame_layer(0, 0, bg)
        self.write_left_elements()
        self.write_right_elements()
    
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
        self.rewrite_art()
    
    def position_swatch(self, renderable, x_offset):
        renderable.x = (self.char_art.quad_width * x_offset) - 1
        renderable.y = self.char_art.quad_height - 1
    
    def reset_loc(self):
        UIElement.reset_loc(self)
    
    def write_left_elements(self):
        """
        fills in left-justified parts of status bar, eg labels for selected
        character/color/tool sections
        """
        color = self.ui.palette.darkest_index
        self.art.write_string(0, 0, self.char_label_x, 0, self.char_label, color)
        self.art.write_string(0, 0, self.fg_label_x, 0, self.fg_label, color)
        self.art.write_string(0, 0, self.bg_label_x, 0, self.bg_label, color)
        self.art.write_string(0, 0, self.tool_label_x, 0, self.tool_label, color)
        # TODO: get name of tool from UI once they exist
        tool_selection = 'painT'
        color = self.ui.palette.lightest_index
        bg = self.ui.palette.darkest_index
        self.art.write_string(0, 0, self.tool_selection_x, 0, tool_selection, color, bg)
    
    def write_right_elements(self):
        """
        fills in right-justified parts of status bar, eg current
        frame/layer/tile and filename
        """
        dark = self.ui.palette.darkest_index
        light = self.ui.palette.lightest_index
        padding = 2
        x = self.width
        art = self.ui.active_art
        # filename
        filename = ' [nothing]  '
        if art:
            filename = ' %s  ' % os.path.basename(art.filename)
        # use "right justify" final arg of write_string
        self.art.write_string(0, 0, x, 0, filename, light, dark, True)
        x += -padding - len(filename)
        # tile
        tile = 'X/Y'
        color = light
        if self.ui.app.cursor:
            tile_x, tile_y = self.ui.app.cursor.get_tile()
            # user-facing coordinates are always base 1
            tile_x += 1
            tile_y += 1
            if tile_x <= 0 or tile_x > art.width:
                color = self.dim_color
            if tile_y <= 0 or tile_y > art.height:
                color = self.dim_color
            tile_x = str(tile_x).rjust(3)
            tile_y = str(tile_y).rjust(3)
            tile = '%s,%s' % (tile_x, tile_y)
        self.art.write_string(0, 0, x, 0, tile, color, dark, True)
        x -= len(tile)
        self.art.write_string(0, 0, x, 0, self.tile_label, dark, light, True)
        x += -padding - len(self.tile_label)
        # layer
        if art:
            layers = art.layers
        layer = '%s/%s' % (self.ui.active_layer + 1, layers)
        self.art.write_string(0, 0, x, 0, layer, light, dark, True)
        x -= len(layer)
        self.art.write_string(0, 0, x, 0, self.layer_label, dark, light, True)
        x += -padding - len(self.layer_label)
        # frame
        frames = 0
        if art:
            frames = art.frames
        frame = '%s/%s' % (self.ui.active_frame + 1, frames)
        self.art.write_string(0, 0, x, 0, frame, light, dark, True)
        x -= len(frame)
        self.art.write_string(0, 0, x, 0, self.frame_label, dark, light, True)
    
    def render(self, elapsed_time):
        UIElement.render(self, elapsed_time)
        self.char_renderable.render(elapsed_time)
        self.fg_renderable.render(elapsed_time)
        self.bg_renderable.render(elapsed_time)
