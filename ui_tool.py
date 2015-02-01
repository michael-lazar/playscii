

class UITool:
    
    name = 'DEBUGTESTTOOL'
    # name visible in popup's tool tab
    button_caption = 'Debug Tool'
    # paint continuously, ie every time mouse enters a new tile
    paint_while_dragging = True
    
    def __init__(self, ui):
        self.ui = ui
        self.brush_size = 1
        self.affects_char = True
        self.affects_fg_color = True
        self.affects_bg_color = True
    
    def paint(self):
        pass
    
    def increase_brush_size(self):
        if self.brush_size:
            self.brush_size += 1
    
    def decrease_brush_size(self):
        if self.brush_size and self.brush_size > 1:
            self.brush_size -= 1


class PencilTool(UITool):
    
    name = 'pencil'
    button_caption = 'Pencil'
    
    def paint(self):
        x, y = self.ui.app.cursor.get_tile()
        # don't allow painting out of bounds
        if not self.ui.active_art.is_tile_inside(x, y):
            return
        char = self.ui.selected_char if self.affects_char else None
        fg = self.ui.selected_fg_color if self.affects_fg_color else None
        bg = self.ui.selected_bg_color if self.affects_bg_color else None
        self.ui.active_art.set_tile_at(self.ui.active_frame, self.ui.active_layer, x, y, char, fg, bg)


class EraseTool(UITool):
    
    name = 'erase'
    button_caption = 'Erase'
    
    def paint(self):
        x, y = self.ui.app.cursor.get_tile()
        # don't allow painting out of bounds
        if not self.ui.active_art.is_tile_inside(x, y):
            return
        char = 0 if self.affects_char else None
        fg = 0 if self.affects_fg_color else None
        bg = 0 if self.affects_bg_color else None
        self.ui.active_art.set_tile_at(self.ui.active_frame, self.ui.active_layer, x, y, char, fg, bg)


class GrabTool(UITool):
    
    name = 'grab'
    button_caption = 'Grab'
    brush_size = None
    
    def paint(self):
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
