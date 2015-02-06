
from edit_command import EditCommandTile
from art import UV_NORMAL, UV_ROTATE90, UV_ROTATE180, UV_ROTATE270

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
    
    def toggle_affects_char(self):
        self.affects_char = not self.affects_char
        self.ui.tool_settings_changed = True
        line = self.button_caption + ' '
        if self.affects_char:
            line += self.ui.affects_char_on_log
        else:
            line += self.ui.affects_char_off_log
        self.ui.message_line.post_line(line)
    
    def toggle_affects_fg(self):
        self.affects_fg_color = not self.affects_fg_color
        self.ui.tool_settings_changed = True
        line = self.button_caption + ' '
        if self.affects_fg_color:
            line += self.ui.affects_fg_on_log
        else:
            line += self.ui.affects_fg_off_log
        self.ui.message_line.post_line(line)
    
    def toggle_affects_bg(self):
        self.affects_bg_color = not self.affects_bg_color
        self.ui.tool_settings_changed = True
        line = self.button_caption + ' '
        if self.affects_bg_color:
            line += self.ui.affects_bg_on_log
        else:
            line += self.ui.affects_bg_off_log
        self.ui.message_line.post_line(line)
    
    def get_paint_commands(self):
        "returns a list of EditCommandTiles for a given paint operation"
        return []
    
    def increase_brush_size(self):
        if not self.brush_size:
            return
        self.brush_size += 1
        self.ui.app.cursor.set_scale(self.brush_size)
        self.ui.tool_settings_changed = True
    
    def decrease_brush_size(self):
        if not self.brush_size:
            return
        if self.brush_size > 1:
            self.brush_size -= 1
            self.ui.app.cursor.set_scale(self.brush_size)
            self.ui.tool_settings_changed = True


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
        # TODO: proper char xform handling for pencil and eraser
        xform = 0
        return char, fg, bg, xform
    
    def get_paint_commands(self):
        commands = []
        art = self.ui.active_art
        frame = self.ui.active_frame
        layer = self.ui.active_layer
        tiles = self.ui.app.cursor.get_tiles_under_brush()
        a_char, a_fg, a_bg, a_xform = self.get_tile_change()
        for tile in tiles:
            # don't allow painting out of bounds
            if not art.is_tile_inside(*tile):
                continue
            new_tile_command = EditCommandTile(art)
            new_tile_command.set_tile(frame, layer, *tile)
            b_char, b_fg, b_bg, b_xform = art.get_tile_at(frame, layer, *tile)
            new_tile_command.set_before(b_char, b_fg, b_bg, b_xform)
            new_tile_command.set_after(a_char, a_fg, a_bg, a_xform)
            # Note: even if command has same result as another in command_tiles,
            # add it anyway as it may be a tool for which subsequent edits to
            # the same tile have different effects, eg rotate
            if not new_tile_command.is_null():
                commands.append(new_tile_command)
        return commands


class EraseTool(PencilTool):
    
    name = 'erase'
    button_caption = 'Erase'
    
    def get_tile_change(self):
        char = 0 if self.affects_char else None
        fg = 0 if self.affects_fg_color else None
        # erase to BG color, not transparent
        bg = self.ui.selected_bg_color if self.affects_bg_color else None
        xform = 0
        return char, fg, bg, xform


class RotateTool(UITool):
    
    name = 'rotate'
    button_caption = 'Rotate'
    
    def get_paint_commands(self):
        commands = []
        art = self.ui.active_art
        frame = self.ui.active_frame
        layer = self.ui.active_layer
        tiles = self.ui.app.cursor.get_tiles_under_brush()
        for tile in tiles:
            # don't allow painting out of bounds
            if not art.is_tile_inside(*tile):
                continue
            new_tile_command = EditCommandTile(art)
            new_tile_command.set_tile(frame, layer, *tile)
            b_char, b_fg, b_bg, b_xform = art.get_tile_at(frame, layer, *tile)
            new_tile_command.set_before(b_char, b_fg, b_bg, b_xform)
            # rotate 90 degrees
            if b_xform == UV_NORMAL:
                a_xform = UV_ROTATE90
            elif b_xform == UV_ROTATE90:
                a_xform = UV_ROTATE180
            elif b_xform == UV_ROTATE180:
                a_xform = UV_ROTATE270
            else:
                a_xform = UV_NORMAL
            new_tile_command.set_after(b_char, b_fg, b_bg, a_xform)
            if not new_tile_command.is_null():
                commands.append(new_tile_command)
        return commands


class GrabTool(UITool):
    
    name = 'grab'
    button_caption = 'Grab'
    brush_size = None
    show_preview = False
    
    def grab(self):
        x, y = self.ui.app.cursor.get_tile()
        art = self.ui.active_art
        if not art.is_tile_inside(x, y):
            return
        # in order to get the actual tile under the cursor, we must undo the
        # cursor preview edits, grab, then redo them
        for edit in self.ui.app.cursor.preview_edits:
            edit.undo()
        frame, layer = self.ui.active_frame, self.ui.active_layer
        if self.affects_char:
            self.ui.selected_char = art.get_char_index_at(frame, layer, x, y)
        if self.affects_fg_color:
            self.ui.selected_fg_color = art.get_fg_color_index_at(frame, layer, x, y)
        if self.affects_bg_color:
            self.ui.selected_bg_color = art.get_bg_color_index_at(frame, layer, x, y)
        for edit in self.ui.app.cursor.preview_edits:
            edit.apply()