
from ui_element import UIElement, UIArt, UIRenderable

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
        # create charset and palette art and renderables
        # width and height set here, everything else happens in reset_art
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
        # TODO: draw wireframe selection box


class CharacterSetSwatch(UISwatch):
    
    # scale the character set will be drawn at
    char_scale = 2
    
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
    
    def update(self):
        charset = self.ui.active_art.charset
        fg, bg = self.ui.selected_fg_color, self.ui.selected_bg_color
        # repopulate colors every update
        for y in range(charset.map_height):
            for x in range(charset.map_width):
                self.art.set_tile_at(0, 0, x, y, None, fg, bg)
        self.art.update()


class PaletteSwatch(UISwatch):
    
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
    
    def update(self):
        self.art.update()
