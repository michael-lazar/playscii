

class UITool:
    
    name = 'DEBUGTESTTOOL'
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
    
    def paint(self):
        x, y = self.ui.app.cursor.get_tile()
        # don't allow painting out of bounds
        if not self.ui.active_art.is_tile_inside(x, y):
            return
        char = (self.affects_char and self.ui.selected_char) or None
        fg = (self.affects_fg_color and self.ui.selected_fg_color) or None
        bg = (self.affects_bg_color and self.ui.selected_bg_color) or None
        self.ui.active_art.set_tile_at(self.ui.active_frame, self.ui.active_layer, x, y, char, fg, bg)


class EraseTool(UITool):
    
    name = 'erase'
    
    def paint(self):
        x, y = self.ui.app.cursor.get_tile()
        # don't allow painting out of bounds
        if not self.ui.active_art.is_tile_inside(x, y):
            return
        self.ui.active_art.set_tile_at(self.ui.active_frame, self.ui.active_layer, x, y, 0)


class GrabTool(UITool):
    
    name = 'grab'
    brush_size = None
    
    def paint(self):
        x, y = self.ui.app.cursor.get_tile()
        art = self.ui.active_art
        if not art.is_tile_inside(x, y):
            return
        frame, layer = self.ui.active_frame, self.ui.active_layer
        self.ui.selected_char = art.get_char_index_at(frame, layer, x, y)
        self.ui.selected_fg_color = art.get_fg_color_index_at(frame, layer, x, y)
        self.ui.selected_bg_color = art.get_bg_color_index_at(frame, layer, x, y)
