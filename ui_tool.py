import math
import sdl2
from PIL import Image

from texture import Texture
from edit_command import EditCommandTile
from art import UV_NORMAL, UV_ROTATE90, UV_ROTATE180, UV_ROTATE270, UV_FLIPX, UV_FLIPY, UV_FLIP90, UV_FLIP270
from key_shifts import SHIFT_MAP
from selection import SelectionRenderable

class UITool:
    
    name = 'DEBUGTESTTOOL'
    # name visible in popup's tool tab
    button_caption = 'Debug Tool'
    # paint continuously, ie every time mouse enters a new tile
    paint_while_dragging = True
    # show preview of paint result under cursor
    show_preview = True
    # if True, refresh paint preview immediately after Cursor.finish_paint
    # set this for anything that produces a different change each paint
    update_preview_after_paint = False
    brush_size = 1
    # affects char/fg/bg/xform masks are relevant to how this tool works
    # (false for eg Selection tool)
    affects_masks = True
    # filename of icon in UI_ASSET_DIR, shown on cursor
    icon_filename = 'icon.png'
    
    def __init__(self, ui):
        self.ui = ui
        self.affects_char = True
        self.affects_fg_color = True
        self.affects_bg_color = True
        self.affects_xform = True
        # load icon, cursor's sprite renderable will reference this texture
        icon_filename = self.ui.asset_dir + self.icon_filename
        self.icon_texture = self.load_icon_texture(icon_filename)
    
    def load_icon_texture(self, img_filename):
        img = Image.open(img_filename)
        img = img.convert('RGBA')
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        return Texture(img.tobytes(), *img.size)
    
    def get_icon_texture(self):
        """
        Returns icon texture that should display for tool's current state.
        (override to eg choose from multiples for mod keys)
        """
        return self.icon_texture
    
    def toggle_affects_char(self):
        if not self.affects_masks or self.ui.app.game_mode:
            return
        self.affects_char = not self.affects_char
        self.ui.tool_settings_changed = True
        line = self.button_caption + ' '
        line = '%s %s' % (self.button_caption, [self.ui.affects_char_off_log, self.ui.affects_char_on_log][self.affects_char])
        self.ui.message_line.post_line(line)
    
    def toggle_affects_fg(self):
        if not self.affects_masks or self.ui.app.game_mode:
            return
        self.affects_fg_color = not self.affects_fg_color
        self.ui.tool_settings_changed = True
        line = '%s %s' % (self.button_caption, [self.ui.affects_fg_off_log, self.ui.affects_fg_on_log][self.affects_fg_color])
        self.ui.message_line.post_line(line)
    
    def toggle_affects_bg(self):
        if not self.affects_masks or self.ui.app.game_mode:
            return
        self.affects_bg_color = not self.affects_bg_color
        self.ui.tool_settings_changed = True
        line = '%s %s' % (self.button_caption, [self.ui.affects_bg_off_log, self.ui.affects_bg_on_log][self.affects_bg_color])
        self.ui.message_line.post_line(line)
    
    def toggle_affects_xform(self):
        if not self.affects_masks or self.ui.app.game_mode:
            return
        self.affects_xform = not self.affects_xform
        self.ui.tool_settings_changed = True
        line = '%s %s' % (self.button_caption, [self.ui.affects_xform_off_log, self.ui.affects_xform_on_log][self.affects_xform])
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
    icon_filename = 'tool_paint.png'
    
    def get_tile_change(self, b_char, b_fg, b_bg, b_xform):
        """
        return the tile value changes this tool would perform on a tile -
        lets Pencil and Erase tools use same paint()
        """
        a_char = self.ui.selected_char if self.affects_char else None
        # don't paint fg color for blank characters
        # (disabled, see BB issue #86)
        #a_fg = self.ui.selected_fg_color if self.affects_fg_color and a_char != 0 else None
        a_fg = self.ui.selected_fg_color if self.affects_fg_color else None
        a_bg = self.ui.selected_bg_color if self.affects_bg_color else None
        a_xform = self.ui.selected_xform if self.affects_xform else None
        return a_char, a_fg, a_bg, a_xform
    
    def get_paint_commands(self):
        commands = []
        art = self.ui.active_art
        frame = art.active_frame
        layer = art.active_layer
        cur = self.ui.app.cursor
        # handle dragging while painting (cursor does the heavy lifting here)
        # !!TODO!! finish this, work in progress
        if cur.moved_this_frame() and cur.current_command and False: #DEBUG
            #print('%s: cursor moved' % self.ui.app.get_elapsed_time()) #DEBUG
            tiles = cur.get_tiles_under_drag()
        else:
            tiles = cur.get_tiles_under_brush()
        for tile in tiles:
            # don't allow painting out of bounds
            if not art.is_tile_inside(*tile):
                continue
            # if a selection is active, only paint inside it
            if len(self.ui.select_tool.selected_tiles) > 0:
                if not self.ui.select_tool.selected_tiles.get(tile, False):
                    continue
            new_tc = EditCommandTile(art)
            new_tc.set_tile(frame, layer, *tile)
            b_char, b_fg, b_bg, b_xform = art.get_tile_at(frame, layer, *tile)
            new_tc.set_before(b_char, b_fg, b_bg, b_xform)
            a_char, a_fg, a_bg, a_xform = self.get_tile_change(b_char, b_fg, b_bg, b_xform)
            new_tc.set_after(a_char, a_fg, a_bg, a_xform)
            # Note: even if command has same result as another in command_tiles,
            # add it anyway as it may be a tool for which subsequent edits to
            # the same tile have different effects, eg rotate
            if not new_tc.is_null():
                commands.append(new_tc)
        return commands


class EraseTool(PencilTool):
    
    name = 'erase'
    button_caption = 'Erase'
    icon_filename = 'tool_erase.png'
    
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
    update_preview_after_paint = True
    rotation_shifts = {
        UV_NORMAL: UV_ROTATE90,
        UV_ROTATE90: UV_ROTATE180,
        UV_ROTATE180: UV_ROTATE270,
        UV_ROTATE270: UV_NORMAL,
        # support flipped characters! counter-intuitive results though?
        UV_FLIPX: UV_FLIP270,
        UV_FLIP270: UV_FLIPY,
        UV_FLIPY: UV_ROTATE270,
        UV_FLIP90: UV_FLIPX
    }
    icon_filename = 'tool_rotate.png'
    
    def get_tile_change(self, b_char, b_fg, b_bg, b_xform):
        return b_char, b_fg, b_bg, self.rotation_shifts[b_xform]


class GrabTool(UITool):
    
    name = 'grab'
    button_caption = 'Grab'
    brush_size = None
    show_preview = False
    icon_filename = 'tool_grab.png'
    
    def grab(self):
        x, y = self.ui.app.cursor.get_tile()
        art = self.ui.active_art
        if not art.is_tile_inside(x, y):
            return
        # in order to get the actual tile under the cursor, we must undo the
        # cursor preview edits, grab, then redo them
        for edit in self.ui.app.cursor.preview_edits:
            edit.undo()
        frame, layer = art.active_frame, art.active_layer
        if self.affects_char:
            self.ui.selected_char = art.get_char_index_at(frame, layer, x, y)
        if self.affects_fg_color:
            self.ui.selected_fg_color = art.get_fg_color_index_at(frame, layer, x, y)
        if self.affects_bg_color:
            self.ui.selected_bg_color = art.get_bg_color_index_at(frame, layer, x, y)
        if self.affects_xform:
            # tells popup etc xform has changed
            self.ui.set_selected_xform(art.get_char_transform_at(frame, layer, x, y))
        for edit in self.ui.app.cursor.preview_edits:
            edit.apply()


class TextTool(UITool):
    
    name = 'text'
    button_caption = 'Text'
    brush_size = None
    show_preview = False
    icon_filename = 'tool_text.png'
    
    def __init__(self, ui):
        UITool.__init__(self, ui)
        self.input_active = False
        self.cursor = None
    
    def start_entry(self):
        self.cursor = self.ui.app.cursor
        # popup gobbles keyboard input, so always dismiss it if it's up
        if self.ui.popup.visible:
            self.ui.popup.hide()
        if self.cursor.x < 0 or self.cursor.x > self.ui.active_art.width or \
           -self.cursor.y < 0 or -self.cursor.y > self.ui.active_art.height:
            return
        self.input_active = True
        self.reset_cursor_start(self.cursor.x, -self.cursor.y)
        self.cursor.start_paint()
        #self.ui.message_line.post_line('Started text entry at %s, %s' % (self.start_x + 1, self.start_y + 1))
        self.ui.message_line.post_line('Started text entry, press Escape to stop entering text.', 5)
    
    def finish_entry(self):
        self.input_active = False
        self.ui.tool_settings_changed = True
        if self.cursor:
            x, y = int(self.cursor.x) + 1, int(-self.cursor.y) + 1
            self.cursor.finish_paint()
        #self.ui.message_line.post_line('Finished text entry at %s, %s' % (x, y))
        self.ui.message_line.post_line('Finished text entry.')
    
    def reset_cursor_start(self, new_x, new_y):
        self.start_x, self.start_y = int(new_x), int(new_y)
    
    def handle_keyboard_input(self, key, shift_pressed, ctrl_pressed, alt_pressed):
        # for now, do nothing on ctrl/alt
        if ctrl_pressed or alt_pressed:
            return
        # popup should get input if it's up
        if self.ui.popup.visible:
            return
        keystr = sdl2.SDL_GetKeyName(key).decode()
        art = self.ui.active_art
        frame, layer = art.active_frame, art.active_layer
        x, y = int(self.cursor.x), int(-self.cursor.y)
        char_w, char_h = art.quad_width, art.quad_height
        # TODO: if cursor isn't inside selection, bail early
        if keystr == 'Return':
            if self.cursor.y < art.width:
                self.cursor.x = self.start_x
                self.cursor.y -= 1
        elif keystr == 'Backspace':
            if self.cursor.x > self.start_x:
                self.cursor.x -= char_w
                # undo command on previous tile
                self.cursor.current_command.undo_commands_for_tile(frame, layer, x-1, y)
        elif keystr == 'Space':
            keystr = ' '
        elif keystr == 'Up':
            if -self.cursor.y > 0:
                self.cursor.y += 1
        elif keystr == 'Down':
            if -self.cursor.y < art.height - 1:
                self.cursor.y -= 1
        elif keystr == 'Left':
            if self.cursor.x > 0:
                self.cursor.x -= char_w
        elif keystr == 'Right':
            if self.cursor.x < art.width - 1:
                self.cursor.x += char_w
        elif keystr == 'Escape':
            self.finish_entry()
            return
        # ignore any other non-character keys
        if len(keystr) > 1:
            return
        if keystr.isalpha() and not shift_pressed:
            keystr = keystr.lower()
        elif not keystr.isalpha() and shift_pressed:
            keystr = SHIFT_MAP.get(keystr, ' ')
        # if cursor got out of bounds, don't input
        if 0 > x or x >= art.width or 0 > y or y >= art.height:
            return
        # create tile command
        new_tc = EditCommandTile(art)
        new_tc.set_tile(frame, layer, x, y)
        b_char, b_fg, b_bg, b_xform = art.get_tile_at(frame, layer, x, y)
        new_tc.set_before(b_char, b_fg, b_bg, b_xform)
        a_char = art.charset.get_char_index(keystr)
        a_fg = self.ui.selected_fg_color if self.affects_fg_color else None
        a_bg = self.ui.selected_bg_color if self.affects_bg_color else None
        a_xform = self.ui.selected_xform if self.affects_xform else None
        new_tc.set_after(a_char, a_fg, a_bg, a_xform)
        # add command, apply immediately, and move cursor
        if self.cursor.current_command:
            self.cursor.current_command.add_command_tiles([new_tc])
        else:
            self.ui.app.log('DEV WARNING: Cursor current command was expected')
        new_tc.apply()
        self.cursor.x += char_w
        if self.cursor.x >= self.ui.active_art.width:
            self.cursor.x = self.start_x
            self.cursor.y -= char_h
        if -self.cursor.y >= self.ui.active_art.height:
            self.finish_entry()


class SelectTool(UITool):
    
    name = 'select'
    button_caption = 'Select'
    brush_size = None
    affects_masks = False
    show_preview = False
    icon_filename_normal = 'tool_select.png'
    icon_filename_add = 'tool_select_add.png'
    icon_filename_sub = 'tool_select_sub.png'
    
    def __init__(self, ui):
        UITool.__init__(self, ui)
        self.selection_in_progress = False
        # dict of all tiles (x, y) that have been selected
        # (dict for fast random access in SelectionRenderable.get_adjacet_tile)
        self.selected_tiles, self.last_selection = {}, {}
        # dict of tiles being selected in a drag that's active right now
        self.current_drag, self.last_drag = {}, {}
        self.drag_start_x, self.drag_start_y = -1, -1
        # create selected tiles and current drag LineRenderables
        self.select_renderable = SelectionRenderable(self.ui.app, self.ui.active_art)
        self.drag_renderable = SelectionRenderable(self.ui.app, self.ui.active_art)
        icon = self.ui.asset_dir + self.icon_filename_normal
        self.icon_texture = self.load_icon_texture(icon)
        icon = self.ui.asset_dir + self.icon_filename_add
        self.icon_texture_add = self.load_icon_texture(icon)
        icon = self.ui.asset_dir + self.icon_filename_sub
        self.icon_texture_sub = self.load_icon_texture(icon)
    
    def get_icon_texture(self):
        # show different icons based on mod key status
        if self.ui.app.il.shift_pressed:
            return self.icon_texture_add
        elif self.ui.app.il.ctrl_pressed:
            return self.icon_texture_sub
        else:
            return self.icon_texture
    
    def start_select(self):
        self.selection_in_progress = True
        self.current_drag = {}
        x, y = self.ui.app.cursor.x, int(-self.ui.app.cursor.y)
        self.drag_start_x, self.drag_start_y = x, y
        #print('started select drag at %s,%s' % (x, y))
    
    def finish_select(self, add_to_selection, subtract_from_selection):
        self.selection_in_progress = False
        # selection boolean operations:
        # shift = add, ctrl = subtract, neither = replace
        if not add_to_selection and not subtract_from_selection:
            self.selected_tiles = self.current_drag.copy()
        elif add_to_selection:
            for tile in self.current_drag:
                self.selected_tiles[tile] = True
        elif subtract_from_selection:
            for tile in self.current_drag:
                self.selected_tiles.pop(tile, None)
        self.current_drag = {}
        #x, y = self.ui.app.cursor.x, int(-self.ui.app.cursor.y)
        #print('finished select drag at %s,%s' % (x, y))
    
    def update(self):
        if not self.ui.active_art:
            return
        # update drag based on cursor
        # context: cursor has already updated, UI.update calls this
        if self.selection_in_progress:
            self.current_drag = {}
            start_x, start_y = int(self.drag_start_x), int(self.drag_start_y)
            end_x, end_y = int(self.ui.app.cursor.x), int(-self.ui.app.cursor.y)
            if start_x > end_x:
                start_x, end_x, = end_x, start_x
            if start_y > end_y:
                start_y, end_y, = end_y, start_y
            # always grow to include cursor's tile
            end_x += 1
            end_y += 1
            w, h = self.ui.active_art.width, self.ui.active_art.height
            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    # never allow out-of-bounds tiles to be selected
                    if 0 <= x < w and 0 <= y < h:
                        self.current_drag[(x, y)] = True
        # if selection or drag tiles have updated since last update,
        # tell our renderables to update
        if self.selected_tiles != self.last_selection:
            self.select_renderable.rebuild_geo(self.selected_tiles)
            self.select_renderable.rebind_buffers()
        if self.current_drag != self.last_drag:
            self.drag_renderable.rebuild_geo(self.current_drag)
            self.drag_renderable.rebind_buffers()
        self.last_selection = self.selected_tiles.copy()
        self.last_drag = self.current_drag.copy()
    
    def render_selections(self):
        if len(self.selected_tiles) > 0:
            self.select_renderable.render()
        if len(self.current_drag) > 0:
            self.drag_renderable.render()


class PasteTool(UITool):
    
    name = 'paste'
    button_caption = 'Paste'
    brush_size = None
    icon_filename = 'tool_paste.png'
    
    # TODO!: dragging large pastes around seems heck of slow, investigate
    # why this function might be to blame and see if there's a fix!
    def get_paint_commands(self):
        # for each command in UI.clipboard, update edit command tile with
        # set_before so we can hover/undo/redo properly
        commands = []
        # similar to PencilTool's get_paint_commands, but "tiles under brush"
        # isn't as straightforward here
        art = self.ui.active_art
        for tc in self.ui.clipboard:
            # deep copy of each clipboard command
            new_tc = tc.copy()
            # not much depends on EditCommand.art at the moment, set it just
            # to be safe
            # TODO: determine whether it makes sense to remove it entirely
            new_tc.art = art
            frame, layer, x, y = new_tc.frame, new_tc.layer, new_tc.x, new_tc.y
            frame = art.active_frame
            layer = art.active_layer
            # offset cursor position, center paste on cursor
            x += int(self.ui.app.cursor.x) - int(self.ui.clipboard_width / 2)
            y -= int(self.ui.app.cursor.y) + int(self.ui.clipboard_height / 2)
            if not (0 <= x < art.width and 0 <= y < art.height):
                continue
            # if a selection is active, only paint inside it
            if len(self.ui.select_tool.selected_tiles) > 0:
                if not self.ui.select_tool.selected_tiles.get((x, y), False):
                    continue
            b_char, b_fg, b_bg, b_xform = self.ui.active_art.get_tile_at(frame, layer, x, y)
            new_tc.set_before(b_char, b_fg, b_bg, b_xform)
            new_tc.set_tile(frame, layer, x, y)
            # respect affects masks like other tools
            a_char = new_tc.a_char if self.affects_char else b_char
            a_fg = new_tc.a_fg if self.affects_fg_color else b_fg
            a_bg = new_tc.a_bg if self.affects_bg_color else b_bg
            a_xform = new_tc.a_xform if self.affects_xform else b_xform
            new_tc.set_after(a_char, a_fg, a_bg, a_xform)
            # see comment at end of PencilTool.get_paint_commands
            if not new_tc.is_null():
                commands.append(new_tc)
        return commands
