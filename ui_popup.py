
from ui_element import UIElement, UIArt, UIRenderable
from ui_swatch import CharacterSetSwatch, PaletteSwatch
from renderable_line import LineRenderable, SelectionBoxRenderable

TAB_TOOLS = 0
TAB_CHAR_COLOR = 1

class ToolPopup(UIElement):
    
    visible = False
    # actual size will be based on character set + palette size and scale
    tile_width, tile_height = 20, 15
    swatch_margin = 0.05
    tool_tab_label = 'Tools'
    char_color_tab_label = 'Chars/Colors'
    unselected_tab_color = 15
    
    def __init__(self, ui):
        self.charset_swatch = CharacterSetSwatch(ui, self)
        self.palette_swatch = PaletteSwatch(ui, self)
        self.cursor_box = SelectionBoxRenderable(ui.app, self.charset_swatch.art)
        # set by swatch.set_cursor_loc based on selection validity
        self.cursor_char = -1
        self.cursor_color = -1
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
        self.tile_width = (cqw * charset.map_width + margin) / UIArt.quad_width
        self.tile_height = (cqh * charset.map_height + margin) / UIArt.quad_height + 6
        self.art.resize(int(self.tile_width), int(self.tile_height), bg)
        # panel text
        self.art.clear_frame_layer(0, 0, bg)
        # tab captions
        tab_width = int(self.tile_width / 2)
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
        x, y = self.ui.get_screen_coords(self.ui.app.mouse_x, self.ui.app.mouse_y)
        # center on mouse
        w, h = self.tile_width * self.art.quad_width, self.tile_height * self.art.quad_height
        x -= w / 2
        y += h / 2
        # clamp to edges of screen
        self.x = max(-1, min(1 - w, x))
        self.y = min(1, max(-1 + h, y))
        # set location for sub elements
        self.renderable.x, self.renderable.y = self.x, self.y
        self.charset_swatch.reset_loc()
        self.palette_swatch.reset_loc()
    
    def hide(self):
        self.visible = False
    
    def hovered(self):
        # TODO: anything needed here? sub-element hovers happen in update
        UIElement.hovered(self)
    
    def update(self):
        if self in self.ui.hovered_elements:
            x, y = self.ui.get_screen_coords(self.ui.app.mouse_x, self.ui.app.mouse_y)
            for e in [self.charset_swatch, self.palette_swatch]:
                if e.is_inside(x, y):
                    e.set_cursor_loc(self.cursor_box, x, y)
                    break
        self.art.update()
        # note: self.cursor_box updates in charset_swatch.update
        self.charset_swatch.update()
        self.palette_swatch.update()
    
    def clicked(self, button):
        UIElement.clicked(self, button)
        # if cursor is over a char or color, make it the ui's selected one
        if self.cursor_char != -1:
            self.ui.selected_char = self.cursor_char
        elif self.cursor_color != -1:
            if button == 1:
                self.ui.selected_fg_color = self.cursor_color
            elif button == 3:
                self.ui.selected_bg_color = self.cursor_color
    
    def render(self, elapsed_time):
        UIElement.render(self, elapsed_time)
        self.charset_swatch.render(elapsed_time)
        self.palette_swatch.render(elapsed_time)
        if self.cursor_char != -1 or self.cursor_color != -1:
            self.cursor_box.render(elapsed_time)
