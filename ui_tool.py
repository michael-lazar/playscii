import sdl2

from edit_command import EditCommandTile
from art import UV_NORMAL, UV_ROTATE90, UV_ROTATE180, UV_ROTATE270, UV_FLIPX, UV_FLIPY
from key_shifts import shift_map

class UITool:
    
    name = 'DEBUGTESTTOOL'
    # name visible in popup's tool tab
    button_caption = 'Debug Tool'
    # paint continuously, ie every time mouse enters a new tile
    paint_while_dragging = True
    # show preview of paint result under cursor
    show_preview = True
    brush_size = 1
    
    def __init__(self, ui):
        self.ui = ui
        self.affects_char = True
        self.affects_fg_color = True
        self.affects_bg_color = True
        self.affects_xform = True
    
    def toggle_affects_char(self):
        self.affects_char = not self.affects_char
        self.ui.tool_settings_changed = True
        line = self.button_caption + ' '
        line = '%s %s' % (self.button_caption, [self.ui.affects_char_on_log, self.ui.affects_char_off_log][self.affects_char])
        self.ui.message_line.post_line(line)
    
    def toggle_affects_fg(self):
        self.affects_fg_color = not self.affects_fg_color
        self.ui.tool_settings_changed = True
        line = '%s %s' % (self.button_caption, [self.ui.affects_fg_on_log, self.ui.affects_fg_off_log][self.affects_fg_color])
        self.ui.message_line.post_line(line)
    
    def toggle_affects_bg(self):
        self.affects_bg_color = not self.affects_bg_color
        self.ui.tool_settings_changed = True
        line = '%s %s' % (self.button_caption, [self.ui.affects_bg_on_log, self.ui.affects_bg_off_log][self.affects_bg_color])
        self.ui.message_line.post_line(line)
    
    def toggle_affects_xform(self):
        self.affects_xform = not self.affects_xform
        self.ui.tool_settings_changed = True
        line = '%s %s' % (self.button_caption, [self.ui.affects_xform_on_log, self.ui.affects_xform_off_log][self.affects_xform])
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
    # "Paint" not Pencil so the A mnemonic works :/
    button_caption = 'Paint'
    
    def get_tile_change(self, b_char, b_fg, b_bg, b_xform):
        """
        return the tile value changes this tool would perform on a tile -
        lets Pencil and Erase tools use same paint()
        """
        a_char = self.ui.selected_char if self.affects_char else None
        # don't paint fg color for blank characters
        a_fg = self.ui.selected_fg_color if self.affects_fg_color and a_char != 0 else None
        a_bg = self.ui.selected_bg_color if self.affects_bg_color else None
        a_xform = self.ui.selected_xform if self.affects_xform else None
        return a_char, a_fg, a_bg, a_xform
    
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
            a_char, a_fg, a_bg, a_xform = self.get_tile_change(b_char, b_fg, b_bg, b_xform)
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
    
    def get_tile_change(self, b_char, b_fg, b_bg, b_xform):
        char = 0 if self.affects_char else None
        fg = 0 if self.affects_fg_color else None
        # erase to BG color, not transparent
        bg = self.ui.selected_bg_color if self.affects_bg_color else None
        xform = UV_NORMAL if self.affects_xform else None
        return char, fg, bg, xform


class RotateTool(PencilTool):
    
    name = 'rotate'
    button_caption = 'Rotate'
    
    def get_tile_change(self, b_char, b_fg, b_bg, b_xform):
        if b_xform == UV_NORMAL:
            a_xform = UV_ROTATE90
        elif b_xform == UV_ROTATE90:
            a_xform = UV_ROTATE180
        elif b_xform == UV_ROTATE180:
            a_xform = UV_ROTATE270
        else:
            a_xform = UV_NORMAL
        return b_char, b_fg, b_bg, a_xform


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


class TextTool(UITool):
    
    name = 'text'
    button_caption = 'Text'
    brush_size = None
    show_preview = False
    
    def __init__(self, ui):
        UITool.__init__(self, ui)
        self.input_active = False
        self.cursor = None
    
    def start_entry(self):
        # TODO: call this instead of setting input_active directly
        self.cursor = self.ui.app.cursor
        self.input_active = True
        self.reset_cursor_start(self.cursor.x, -self.cursor.y)
        self.cursor.start_paint()
        self.ui.message_line.post_line('Started text entry at %s, %s' % (self.start_x + 1, self.start_y + 1))
    
    def finish_entry(self):
        self.input_active = False
        self.ui.tool_settings_changed = True
        x, y = int(self.cursor.x) + 1, int(-self.cursor.y) + 1
        self.ui.message_line.post_line('Finished text entry at %s, %s' % (x, y))
        self.cursor.finish_paint()
    
    def reset_cursor_start(self, new_x, new_y):
        self.start_x, self.start_y = int(new_x), int(new_y)
    
    def handle_keyboard_input(self, key, shift_pressed, ctrl_pressed, alt_pressed):
        keystr = sdl2.SDL_GetKeyName(key).decode()
        art = self.ui.active_art
        frame, layer = self.ui.active_frame, self.ui.active_layer
        x, y = self.cursor.x, -self.cursor.y
        if keystr == 'Return':
            if self.cursor.y < art.width:
                self.cursor.x = self.start_x
                self.cursor.y -= 1
        elif keystr == 'Backspace':
            if self.cursor.x > self.start_x:
                self.cursor.x -= 1
            # undo command on previous tile
            self.cursor.current_command.undo_commands_for_tile(frame, layer, x-1, y)
        elif keystr == 'Space':
            keystr = ' '
        elif keystr == 'Up':
            self.cursor.y += 1
        elif keystr == 'Down':
            self.cursor.y -= 1
        elif keystr == 'Left':
            self.cursor.x -= 1
        elif keystr == 'Right':
            self.cursor.x += 1
        elif keystr == 'Escape':
            self.finish_entry()
            return
        # ignore any other non-character keys
        if len(keystr) > 1:
            return
        if keystr.isalpha() and not shift_pressed:
            keystr = keystr.lower()
        elif not keystr.isalpha() and shift_pressed:
            keystr = shift_map.get(keystr, ' ')
        # create tile command
        new_tile_command = EditCommandTile(art)
        new_tile_command.set_tile(frame, layer, x, y)
        b_char, b_fg, b_bg, b_xform = art.get_tile_at(frame, layer, x, y)
        new_tile_command.set_before(b_char, b_fg, b_bg, b_xform)
        a_char = art.charset.get_char_index(keystr)
        a_fg = self.ui.selected_fg_color if self.affects_fg_color else None
        a_bg = self.ui.selected_bg_color if self.affects_bg_color else None
        a_xform = self.ui.selected_xform if self.affects_xform else None
        new_tile_command.set_after(a_char, a_fg, a_bg, a_xform)
        # add command, apply immediately, and move cursor
        self.cursor.current_command.add_command_tiles(new_tile_command)
        new_tile_command.apply()
        self.cursor.x += 1
        if self.cursor.x >= self.ui.active_art.width:
            self.cursor.x = self.start_x
            self.cursor.y -= 1
        if -self.cursor.y >= self.ui.active_art.height:
            self.finish_entry()
