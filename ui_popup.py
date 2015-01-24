
from ui_element import UIElement, UIArt, UIRenderable

class ToolPopup(UIElement):
    
    visible = False
    width, height = 20, 15
    # scale the character set will be drawn at
    char_scale = 2
    char_margin = 0.05
    
    def __init__(self, ui):
        art = ui.active_art
        # create charset and palette art and renderables
        # width and height set here, everything else happens in reset_art
        w, h = art.charset.map_width, art.charset.map_height
        self.charset_art = UIArt(None, ui.app, art.charset, art.palette, w, h)
        self.charset_renderable = UIRenderable(ui.app, self.charset_art)
        w, h = len(art.palette.colors), 1
        self.palette_art = UIArt(None, ui.app, art.charset, art.palette, w, h)
        self.palette_renderable = UIRenderable(ui.app, self.palette_art)
        for r in [self.charset_renderable, self.palette_renderable]:
            r.ui = ui
            r.grain_strength = 0
        UIElement.__init__(self, ui)
    
    def reset_art(self):
        aspect = self.ui.app.window_width / self.ui.app.window_height
        charset = self.ui.active_art.charset
        palette = self.ui.active_art.palette
        # TODO: using screen resolution, try to set quad size to an even
        # multiple of screen so the sampling doesn't get chunky
        cqw = UIArt.quad_width * self.char_scale
        cqh = UIArt.quad_width * (charset.char_height / charset.char_width) * self.char_scale * aspect
        self.charset_art.quad_width, self.charset_art.quad_height = cqw, cqh
        self.palette_art.quad_width, self.palette_art.quad_height = cqw, cqh
        # set panel size based on charset size
        fg = self.ui.palette.darkest_index
        bg = self.ui.palette.lightest_index
        margin = self.char_margin * 2
        self.width = (cqw * charset.map_width + margin) / UIArt.quad_width
        self.height = (cqh * charset.map_height + margin) / UIArt.quad_height + 6
        self.art.resize(int(self.width), int(self.height), bg)
        # panel text
        self.art.clear_frame_layer(0, 0, bg)
        # tab captions
        self.art.write_string(0, 0, 3, 0, 'Tools', fg)
        self.art.write_string(0, 0, self.width - 3, 0, 'Char/Colors', fg, None, True)
        # charset renderable location will be set in update()
        # charset label
        self.art.write_string(0, 0, 2, 2, 'Character Set: %s' % charset.name, fg)
        # palette label
        pal_caption_y = (cqh * charset.map_height) / self.art.quad_height
        pal_caption_y += 4
        self.art.write_string(0, 0, 2, int(pal_caption_y), 'Color Palette: %s' % palette.name, fg)
        # populate charset and palette Arts
        # populate charset
        # only need to populate characters on reset_art, but update
        # colors every update()
        self.charset_art.clear_frame_layer(0, 0, 0)
        i = 0
        for y in range(charset.map_height):
            for x in range(charset.map_width):
                self.charset_art.set_char_index_at(0, 0, x, y, i)
                i += 1
        # populate palette
        self.palette_art.clear_frame_layer(0, 0, 0)
        palette = self.ui.active_art.palette
        for x in range(len(palette.colors)):
            self.palette_art.set_color_at(0, 0, x, 0, x, False)
        self.art.geo_changed = True
        self.charset_art.geo_changed = True
        self.palette_art.geo_changed = True
    
    def show(self):
        # if already visible, bail - key repeat probably triggered this
        if self.visible:
            return
        self.visible = True
        x = (2 * self.ui.app.mouse_x) / self.ui.app.window_width - 1
        y = (-2 * self.ui.app.mouse_y) / self.ui.app.window_height + 1
        
        charset = self.ui.active_art.charset
        # TODO: try to position popup center near mouse
        w = self.charset_art.quad_width * charset.map_width + self.char_margin * 2
        x -= w / 2
        # TODO: store charset and palette dimensions in reset_art so we don't
        # have to recalc them here!
        h = self.charset_art.quad_height * charset.map_height
        y += h / 2
        # clamp to edges of screen
        x = max(-1, min(1 - w, x))
        y = min(1, max(-1 + h, y))
        # set location for main renderable and sub elements
        self.x, self.y = x, y
        self.renderable.x, self.renderable.y = x, y
        # position charset and palette
        self.charset_renderable.x = x + self.char_margin
        self.charset_renderable.y = y
        self.charset_renderable.y -= self.art.quad_height * 3
        self.palette_renderable.x = x + self.char_margin
        self.palette_renderable.y = self.charset_renderable.y
        self.palette_renderable.y -= self.charset_art.quad_height * charset.map_height
        self.palette_renderable.y -= self.art.quad_height * 2
    
    def hide(self):
        self.visible = False
    
    def update(self):
        charset = self.ui.active_art.charset
        fg, bg = self.ui.selected_fg_color, self.ui.selected_bg_color
        # repopulate colors every update
        for y in range(charset.map_height):
            for x in range(charset.map_width):
                self.charset_art.set_tile_at(0, 0, x, y, None, fg, bg)
        self.charset_art.update()
        self.palette_art.update()
    
    def render(self, elapsed_time):
        UIElement.render(self, elapsed_time)
        self.charset_renderable.render(elapsed_time)
        self.palette_renderable.render(elapsed_time)
