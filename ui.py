import numpy as np
from PIL import Image
from OpenGL import GL

from texture import Texture
from ui_element import UIArt, FPSCounterUI, MessageLineUI, DebugTextUI
from ui_console import ConsoleUI
from ui_status_bar import StatusBarUI
from ui_popup import ToolPopup
from ui_menu_bar import MenuBar
from ui_menu_pulldown import PulldownMenu
from ui_colors import UIColors
from ui_tool import PencilTool, EraseTool, GrabTool, RotateTool, TextTool, SelectTool, PasteTool
from art import UV_NORMAL, UV_ROTATE90, UV_ROTATE180, UV_ROTATE270, UV_FLIPX, UV_FLIPY, uv_names
from edit_command import EditCommand, EditCommandTile

UI_ASSET_DIR = 'ui/'
SCALE_INCREMENT = 0.25


class UI:
    
    # user-configured UI scale factor
    scale = 1.0
    max_onion_alpha = 0.5
    charset_name = 'ui'
    palette_name = 'c64_original'
    # low-contrast background texture that distinguishes UI from flat color
    grain_texture = 'bgnoise_alpha.png'
    visible = True
    logg = False
    popup_hold_to_show = True
    tool_classes = [ PencilTool, EraseTool, GrabTool, RotateTool, TextTool, SelectTool, PasteTool ]
    tool_selected_log = 'tool selected'
    art_selected_log = 'Now editing'
    frame_selected_log = 'Now editing frame'
    layer_selected_log = 'Now editing layer: %s'
    swap_color_log = 'Swapped FG/BG colors'
    affects_char_on_log = 'will affect characters'
    affects_char_off_log = 'will not affect characters'
    affects_fg_on_log = 'will affect foreground colors'
    affects_fg_off_log = 'will not affect foreground colors'
    affects_bg_on_log = 'will affect background colors'
    affects_bg_off_log = 'will not affect background colors'
    affects_xform_on_log = 'will affect character rotation/flip'
    affects_xform_off_log = 'will not affect character rotation/flip'
    xform_selected_log = 'Selected character transform:'
    
    def __init__(self, app, active_art):
        self.app = app
        # the current art being edited
        self.active_art = active_art
        self.active_frame = 0
        self.active_layer = 0
        # dialog box set here
        self.active_dialog = None
        # easy color index lookups
        self.colors = UIColors()
        # for UI, view /and/ projection matrix are identity
        # (aspect correction is done in set_scale)
        self.view_matrix = np.eye(4, 4, dtype=np.float32)
        self.charset = self.app.load_charset(self.charset_name, False)
        self.palette = self.app.load_palette(self.palette_name, False)
        # currently selected char, fg color, bg color
        art_char = self.active_art.charset
        art_pal = self.active_art.palette
        self.selected_char = art_char.get_char_index('A') or 2
        self.selected_fg_color = art_pal.lightest_index
        self.selected_bg_color = art_pal.darkest_index
        self.selected_xform = UV_NORMAL
        self.selected_tool, self.previous_tool = None, None
        # set True when tool settings change, cleared after update, used by
        # cursor to determine if cursor update needed
        self.tool_settings_changed = False
        self.tools = []
        # create tools
        for t in self.tool_classes:
            new_tool = t(self)
            tool_name = '%s_tool' % new_tool.name
            setattr(self, tool_name, new_tool)
            # stick in a list for popup tool tab
            self.tools.append(new_tool)
        self.selected_tool = self.pencil_tool
        # clipboard: list of EditCommandTiles, set by cut/copy, used by paste
        self.clipboard = []
        # track clipboard contents' size so we don't have to recompute it every
        # cursor preview update
        self.clipboard_width = 0
        self.clipboard_height = 0
        # create elements
        self.elements = []
        self.hovered_elements = []
        # set geo sizes, force scale update
        self.set_scale(self.scale)
        fps_counter = FPSCounterUI(self)
        self.console = ConsoleUI(self)
        self.status_bar = StatusBarUI(self)
        self.popup = ToolPopup(self)
        self.message_line = MessageLineUI(self)
        self.debug_text = DebugTextUI(self)
        self.pulldown = PulldownMenu(self)
        self.menu_bar = None
        self.menu_bar = MenuBar(self)
        self.elements.append(fps_counter)
        self.elements.append(self.status_bar)
        self.elements.append(self.popup)
        self.elements.append(self.message_line)
        self.elements.append(self.debug_text)
        self.elements.append(self.pulldown)
        self.elements.append(self.menu_bar)
        # add console last so it draws last
        self.elements.append(self.console)
        # grain texture
        img = Image.open(UI_ASSET_DIR + self.grain_texture)
        img = img.convert('RGBA')
        width, height = img.size
        self.grain_texture = Texture(img.tostring(), width, height)
        self.grain_texture.set_wrap(GL.GL_REPEAT)
        self.grain_texture.set_filter(GL.GL_LINEAR, GL.GL_LINEAR_MIPMAP_LINEAR)
        # update elements that weren't created when UI scale was determined
        self.set_elements_scale()
    
    def set_scale(self, new_scale):
        old_scale = self.scale
        self.scale = new_scale
        # update UI renderable geo sizes for new scale
        # determine width and height of current window in chars
        # use floats, window might be a fractional # of chars wide/tall
        aspect = self.app.window_width / self.app.window_height
        inv_aspect = self.app.window_height / self.app.window_width
        # MAYBE-TODO: this math is correct but hard to follow, rewrite for clarity
        width = self.app.window_width / (self.charset.char_width * self.scale * inv_aspect)
        height = self.app.window_height / (self.charset.char_height * self.scale * inv_aspect)
        # any new UI elements created should use new scale
        UIArt.quad_width = 2 / width * aspect
        UIArt.quad_height = 2 / height * aspect
        self.width_tiles = width * (inv_aspect / self.scale)
        self.height_tiles = height / self.scale
        # tell elements to refresh
        self.set_elements_scale()
        if self.scale != old_scale:
            self.message_line.post_line('UI scale is now %s (%.3f x %.3f)' % (self.scale, self.width_tiles, self.height_tiles))
    
    def set_elements_scale(self):
        for e in self.elements:
            e.art.quad_width, e.art.quad_height = UIArt.quad_width, UIArt.quad_height
            # Art dimensions may well need to change
            e.reset_art()
            e.reset_loc()
            e.art.geo_changed = True
    
    def window_resized(self):
        # recalc renderables' quad size (same scale, different aspect)
        self.set_scale(self.scale)
    
    def set_active_art(self, new_art):
        self.active_art = new_art
        new_charset = self.active_art.charset
        new_palette = self.active_art.palette
        # change active frame and layer if new active art doesn't have that many
        self.active_frame = min(self.active_frame, self.active_art.frames - 1)
        self.active_layer = min(self.active_layer, self.active_art.layers - 1)
        # make sure selection isn't out of bounds in new art
        old_selection = self.select_tool.selected_tiles.copy()
        for tile in old_selection:
            x, y = tile[0], tile[1]
            if x >= new_art.width or y >= new_art.height:
                self.select_tool.selected_tiles.pop(tile, None)
        # set camera bounds based on art size
        self.app.camera.set_limits_for_art(new_art)
        # set for popup
        self.popup.set_active_charset(new_charset)
        self.popup.set_active_palette(new_palette)
        self.reset_onion_frames()
        # reposition all art renderables and change their opacity
        x, y, margin = 0, 0, self.app.grid.art_margin
        for r in self.app.edit_renderables:
            # always put active art at 0,0
            if r in self.active_art.renderables:
                r.alpha = 1
                r.move_to(0, 0, 0, 0.1)
            else:
                r.alpha = 0.5
                r.move_to(x, y, -1, 0.1)
            x += (r.art.width + margin) * r.art.quad_width
            y -= (r.art.height + margin) * r.art.quad_height
        # now that renderables are moved, rescale/reposition grid
        self.app.grid.reset()
        self.app.update_window_title()
        self.message_line.post_line('%s %s' % (self.art_selected_log, self.active_art.filename))
    
    def set_active_art_by_filename(self, art_filename):
        for i,art in enumerate(self.app.art_loaded_for_edit):
            if art_filename == art.filename:
                break
        new_active_art = self.app.art_loaded_for_edit.pop(i)
        self.app.art_loaded_for_edit.insert(0, new_active_art)
        new_active_renderable = self.app.edit_renderables.pop(i)
        self.app.edit_renderables.insert(0, new_active_renderable)
        self.set_active_art(new_active_art)
    
    def previous_active_art(self):
        "cycles to next art in app.art_loaded_for_edit"
        if len(self.app.art_loaded_for_edit) == 1:
            return
        next_active_art = self.app.art_loaded_for_edit.pop(-1)
        self.app.art_loaded_for_edit.insert(0, next_active_art)
        next_active_renderable = self.app.edit_renderables.pop(-1)
        self.app.edit_renderables.insert(0, next_active_renderable)
        self.set_active_art(self.app.art_loaded_for_edit[0])
    
    def next_active_art(self):
        if len(self.app.art_loaded_for_edit) == 1:
            return
        last_active_art = self.app.art_loaded_for_edit.pop(0)
        self.app.art_loaded_for_edit.append(last_active_art)
        last_active_renderable = self.app.edit_renderables.pop(0)
        self.app.edit_renderables.append(last_active_renderable)
        self.set_active_art(self.app.art_loaded_for_edit[0])
    
    def set_selected_tool(self, new_tool):
        if new_tool == self.selected_tool:
            return
        self.previous_tool = self.selected_tool
        self.selected_tool = new_tool
        self.popup.reset_art()
        self.tool_settings_changed = True
        # close menu if we selected tool from it
        if self.menu_bar.active_menu_name:
            self.menu_bar.close_active_menu()
        self.message_line.post_line('%s %s' % (self.selected_tool.button_caption, self.tool_selected_log))
    
    def set_selected_xform(self, new_xform):
        self.selected_xform = new_xform
        self.popup.set_xform(new_xform)
        self.tool_settings_changed = True
        line = '%s %s' % (self.xform_selected_log, uv_names[self.selected_xform])
        self.message_line.post_line(line)
    
    def cycle_selected_xform(self, back=False):
        xform = self.selected_xform
        if back:
            xform -= 1
        else:
            xform += 1
        xform %= UV_FLIPY + 1
        self.set_selected_xform(xform)
    
    def reset_onion_frames(self, new_art=None):
        "set correct visibility, frame, and alpha for all onion renderables"
        new_art = new_art or self.active_art
        alpha = self.max_onion_alpha
        total_onion_frames = 0
        def set_onion(r, new_frame, alpha):
            # scale back if fewer than MAX_ONION_FRAMES in either direction
            if total_onion_frames >= new_art.frames:
                r.visible = False
                return
            r.visible = True
            if not new_art is r.art:
                r.set_art(new_art)
            r.set_frame(new_frame)
            r.alpha = alpha
            # make BG dimmer so it's easier to see
            r.bg_alpha = alpha / 2
        # populate "next" frames first
        for i,r in enumerate(self.app.onion_renderables_next):
            total_onion_frames += 1
            new_frame = self.active_frame + i + 1
            set_onion(r, new_frame, alpha)
            alpha /= 2
            #print('next onion %s set to frame %s alpha %s' % (i, new_frame, alpha))
        alpha = self.max_onion_alpha
        for i,r in enumerate(self.app.onion_renderables_prev):
            total_onion_frames += 1
            new_frame = self.active_frame - (i + 1)
            set_onion(r, new_frame, alpha)
            # each successive onion layer is dimmer
            alpha /= 2
            #print('previous onion %s set to frame %s alpha %s' % (i, new_frame, alpha))
    
    def set_active_frame(self, new_frame):
        new_frame %= self.active_art.frames
        # bail if frame is still the same, eg we only have 1 frame
        if new_frame == self.active_frame:
            return
        self.active_frame = new_frame
        # update active art's renderables
        for r in self.active_art.renderables:
            r.set_frame(self.active_frame)
        self.reset_onion_frames()
        self.tool_settings_changed = True
        self.message_line.post_line('%s %s' % (self.frame_selected_log, self.active_frame + 1))
    
    def set_active_layer(self, new_layer):
        self.active_layer = min(max(0, new_layer), self.active_art.layers-1)
        z = self.active_art.layers_z[self.active_layer]
        self.app.grid.z = z
        self.select_tool.select_renderable.z = z
        self.select_tool.drag_renderable.z = z
        self.app.cursor.z = z
        self.app.update_window_title()
        self.tool_settings_changed = True
        layer_name = self.active_art.layer_names[self.active_layer]
        self.message_line.post_line(self.layer_selected_log % layer_name)
    
    def select_char(self, new_char_index):
        if not self.active_art:
            return
        # wrap at last valid index
        self.selected_char = new_char_index % self.active_art.charset.last_index
        self.tool_settings_changed = True
    
    def select_color(self, new_color_index, fg):
        "common code for select_fg/bg"
        if not self.active_art:
            return
        new_color_index %= len(self.active_art.palette.colors)
        if fg:
            self.selected_fg_color = new_color_index
        else:
            self.selected_bg_color = new_color_index
        self.tool_settings_changed = True
    
    def select_fg(self, new_fg_index):
        self.select_color(new_fg_index, True)
    
    def select_bg(self, new_bg_index):
        self.select_color(new_bg_index, False)
    
    def swap_fg_bg_colors(self):
        fg, bg = self.selected_fg_color, self.selected_bg_color
        self.selected_fg_color, self.selected_bg_color = bg, fg
        self.tool_settings_changed = True
        self.message_line.post_line(self.swap_color_log)
    
    def cut_selection(self):
        self.copy_selection()
        self.erase_tiles_in_selection()
    
    def erase_selection_or_art(self):
        if len(self.select_tool.selected_tiles) > 0:
            self.erase_tiles_in_selection()
        else:
            self.active_art.clear_frame_layer(self.active_frame, self.active_layer,
                                              bg_color=self.selected_bg_color)
    
    def erase_tiles_in_selection(self):
        # create and commit command group to clear all tiles in selection
        frame, layer = self.active_frame, self.active_layer
        new_command = EditCommand(self.active_art)
        for tile in self.select_tool.selected_tiles:
            new_tile_command = EditCommandTile(self.active_art)
            new_tile_command.set_tile(frame, layer, *tile)
            b_char, b_fg, b_bg, b_xform = self.active_art.get_tile_at(frame, layer, *tile)
            new_tile_command.set_before(b_char, b_fg, b_bg, b_xform)
            a_char = a_fg = 0
            a_xform = UV_NORMAL
            # clear to current BG
            a_bg = self.selected_bg_color
            new_tile_command.set_after(a_char, a_fg, a_bg, a_xform)
            new_command.add_command_tiles(new_tile_command)
        new_command.apply()
        self.active_art.command_stack.commit_commands(new_command)
        self.active_art.set_unsaved_changes(True)
    
    def copy_selection(self):
        # convert current selection tiles (active frame+layer) into
        # EditCommandTiles for Cursor.preview_edits
        # (via PasteTool get_paint_commands)
        self.clipboard = []
        frame, layer = self.active_frame, self.active_layer
        min_x, min_y = 9999, 9999
        max_x, max_y = -1, -1
        for tile in self.select_tool.selected_tiles:
            x, y = tile[0], tile[1]
            if x < min_x:
                min_x = x
            elif x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            elif y > max_y:
                max_y = y
            art = self.active_art
            new_tile_command = EditCommandTile(art)
            new_tile_command.set_tile(frame, layer, x, y)
            a_char, a_fg, a_bg, a_xform = art.get_tile_at(frame, layer, x, y)
            # set data as "after" state, before will be set by cursor hover
            new_tile_command.set_after(a_char, a_fg, a_bg, a_xform)
            self.clipboard.append(new_tile_command)
        # rebase tiles at top left corner of clipboard tiles
        for tile_command in self.clipboard:
            x = tile_command.x - min_x
            y = tile_command.y - min_y
            tile_command.set_tile(frame, layer, x, y)
        self.clipboard_width = max_x - min_x
        self.clipboard_height = max_y - min_y
        # switch to PasteTool
        self.set_selected_tool(self.paste_tool)
        self.tool_settings_changed = True
    
    def crop_to_selection(self, art):
        # ignore non-rectangular selection features, use top left and bottom
        # right corners
        if len(self.select_tool.selected_tiles) == 0:
            return
        min_x, max_x = 99999, -1
        min_y, max_y = 99999, -1
        for tile in self.select_tool.selected_tiles:
            x, y = tile[0], tile[1]
            if x < min_x:
                min_x = x
            elif x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            elif y > max_y:
                max_y = y
        w = max_x - min_x + 1
        h = max_y - min_y + 1
        art.resize(w, h, min_x, min_y)
        self.app.log('Resized %s to %s x %s' % (art.filename, w, h))
        art.set_unsaved_changes(True)
        # clear selection to avoid having tiles we know are OoB selected
        self.select_tool.selected_tiles = {}
        self.adjust_for_art_resize(art)
    
    def adjust_for_art_resize(self, art):
        # update grid, camera, cursor
        if art is self.active_art:
            self.app.camera.set_limits_for_art(art)
            self.app.camera.center_camera_for_art(art)
            self.app.grid.reset()
            if self.app.cursor.x > art.width:
               self.app.cursor.x = art.width
            if self.app.cursor.y > art.height:
               self.app.cursor.y = art.height
            self.app.cursor.moved = True
    
    def resize_art(self, art, new_width, new_height, origin_x, origin_y):
        art.resize(new_width, new_height, origin_x, origin_y)
        self.adjust_for_art_resize(art)
    
    def select_none(self):
        self.select_tool.selected_tiles = {}
    
    def select_all(self):
        self.select_tool.selected_tiles = {}
        for y in range(self.active_art.height):
            for x in range(self.active_art.width):
                self.select_tool.selected_tiles[(x, y)] = True
    
    def invert_selection(self):
        old_selection = self.select_tool.selected_tiles.copy()
        self.select_tool.selected_tiles = {}
        for y in range(self.active_art.height):
            for x in range(self.active_art.width):
                if not old_selection.get((x, y), False):
                    self.select_tool.selected_tiles[(x, y)] = True
    
    def get_screen_coords(self, window_x, window_y):
        x = (2 * window_x) / self.app.window_width - 1
        y = (-2 * window_y) / self.app.window_height + 1
        return x, y
    
    def update(self):
        self.select_tool.update()
        # window coordinates -> OpenGL coordinates
        mx, my = self.get_screen_coords(self.app.mouse_x, self.app.mouse_y)
        # test elements for hover
        was_hovering = self.hovered_elements[:]
        self.hovered_elements = []
        for e in self.elements:
            # only check visible elements
            if e.visible and e.can_hover and e.is_inside(mx, my):
                self.hovered_elements.append(e)
                # only hover if we weren't last update
                if not e in was_hovering:
                    e.hovered()
        for e in was_hovering:
            if not e in self.hovered_elements:
                e.unhovered()
        # update all elements, regardless of whether they're being hovered etc
        for e in self.elements:
            e.update()
            # art update: tell renderables to refresh buffers
            e.art.update()
        self.tool_settings_changed = False
    
    def clicked(self, button):
        for e in self.hovered_elements:
            e.clicked(button)
        if self.pulldown.visible and not self.pulldown in self.hovered_elements and not self.menu_bar in self.hovered_elements:
            self.menu_bar.close_active_menu()
    
    def unclicked(self, button):
        for e in self.hovered_elements:
            e.unclicked(button)
    
    def quick_grab(self):
        if self.popup.visible or self.console.visible:
            return
        self.grab_tool.grab()
        self.tool_settings_changed = True
    
    def undo(self):
        # if still painting, finish
        if self.app.cursor.current_command:
            self.app.cursor.finish_paint()
        self.active_art.command_stack.undo()
        self.active_art.set_unsaved_changes(True)
    
    def redo(self):
        self.active_art.command_stack.redo()
    
    def open_dialog(self, box_class):
        dialog = box_class(self)
        self.active_dialog = dialog
        # insert dialog at index 0 so it draws first instead of last
        self.elements.insert(0, dialog)
    
    def destroy(self):
        for e in self.elements:
            e.destroy()
        self.grain_texture.destroy()
    
    def render(self):
        for e in self.elements:
            if e.visible:
                if not self.app.game_mode or (self.app.game_mode and e.game_mode_visible):
                    e.render()
