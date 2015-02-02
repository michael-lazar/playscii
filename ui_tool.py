

class UITool:
    
    name = 'DEBUGTESTTOOL'
    # name visible in popup's tool tab
    button_caption = 'Debug Tool'
    # paint continuously, ie every time mouse enters a new tile
    paint_while_dragging = True
    # show preview of paint result under cursor
    show_preview = True
    
    def __init__(self, ui):
        self.ui = ui
        self.brush_size = 1
        self.affects_char = True
        self.affects_fg_color = True
        self.affects_bg_color = True
    
    def paint(self, art=None, base_zero=False):
        pass
    
    def increase_brush_size(self):
        if self.brush_size:
            self.brush_size += 1
        self.ui.app.cursor.set_scale(self.brush_size)
    
    def decrease_brush_size(self):
        if self.brush_size and self.brush_size > 1:
            self.brush_size -= 1
        self.ui.app.cursor.set_scale(self.brush_size)


class PencilTool(UITool):
    
    name = 'pencil'
    button_caption = 'Pencil'
    
    def get_tile_change(self):
        """
        return the tile value changes this tool would perform on a tile -
        lets Pencil and Erase tools use same paint()
        """
        char = self.ui.selected_char if self.affects_char else None
        fg = self.ui.selected_fg_color if self.affects_fg_color else None
        bg = self.ui.selected_bg_color if self.affects_bg_color else None
        return char, fg, bg
    
    def paint(self, art=None, base_zero=False):
        # by default paint to active art, but allow pass-in eg cursor preview
        art = art or self.ui.active_art
        # "base zero" = cursor preview, mapping art-space to cursor-art-space
        tiles = self.ui.app.cursor.get_tiles_under_brush(base_zero)
        frame = self.ui.active_frame if art == self.ui.active_art else 0
        layer = self.ui.active_layer if art == self.ui.active_art else 0
        char, fg, bg = self.get_tile_change()
        for tile in tiles:
            x, y = tile[0], tile[1]
            # don't allow painting out of bounds
            if not art.is_tile_inside(x, y):
                continue
            art.set_tile_at(frame, layer, x, y, char, fg, bg)


class EraseTool(PencilTool):
    
    name = 'erase'
    button_caption = 'Erase'
    
    def get_tile_change(self):
        char = 0 if self.affects_char else None
        fg = 0 if self.affects_fg_color else None
        bg = 0 if self.affects_bg_color else None
        return char, fg, bg


class GrabTool(UITool):
    
    name = 'grab'
    button_caption = 'Grab'
    brush_size = None
    show_preview = False
    
    def paint(self, art=None, base_zero=False):
        x, y = self.ui.app.cursor.get_tile()
        art = self.ui.active_art
        if not art.is_tile_inside(x, y):
            return
        frame, layer = self.ui.active_frame, self.ui.active_layer
        if self.affects_char:
            self.ui.selected_char = art.get_char_index_at(frame, layer, x, y)
        if self.affects_fg_color:
            self.ui.selected_fg_color = art.get_fg_color_index_at(frame, layer, x, y)
        if self.affects_bg_color:
            self.ui.selected_bg_color = art.get_bg_color_index_at(frame, layer, x, y)
