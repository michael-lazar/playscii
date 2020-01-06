import ctypes, os, platform
import sdl2

from sys import exit

from ui import SCALE_INCREMENT
from renderable import LAYER_VIS_FULL, LAYER_VIS_DIM, LAYER_VIS_NONE
from ui_art_dialog import NewArtDialog, SaveAsDialog, QuitUnsavedChangesDialog, CloseUnsavedChangesDialog, RevertChangesDialog, ResizeArtDialog, AddFrameDialog, DuplicateFrameDialog, FrameDelayDialog, FrameDelayAllDialog, FrameIndexDialog, AddLayerDialog, DuplicateLayerDialog, SetLayerNameDialog, SetLayerZDialog, PaletteFromFileDialog, ImportFileDialog, ExportFileDialog, SetCameraZoomDialog, ExportOptionsDialog
from ui_game_dialog import NewGameDirDialog, LoadGameStateDialog, SaveGameStateDialog, AddRoomDialog, SetRoomCamDialog, SetRoomEdgeWarpsDialog, SetRoomBoundsObjDialog, RenameRoomDialog
from ui_info_dialog import PagedInfoDialog
from ui_file_chooser_dialog import ArtChooserDialog, CharSetChooserDialog, PaletteChooserDialog, PaletteFromImageChooserDialog, RunArtScriptDialog
from ui_list_operations import LO_NONE, LO_SELECT_OBJECTS, LO_SET_SPAWN_CLASS, LO_LOAD_STATE, LO_SET_ROOM, LO_SET_ROOM_OBJECTS, LO_SET_OBJECT_ROOMS, LO_OPEN_GAME_DIR, LO_SET_ROOM_EDGE_WARP, LO_SET_ROOM_EDGE_WARP, LO_SET_ROOM_EDGE_OBJ, LO_SET_ROOM_CAMERA
from collision import CT_NONE
from art import ART_DIR, ART_FILE_EXTENSION
from key_shifts import NUMLOCK_ON_MAP, NUMLOCK_OFF_MAP

BINDS_FILENAME = 'binds.cfg'
BINDS_TEMPLATE_FILENAME = 'binds.cfg.default'


class InputLord:
    
    "sets up key binds and handles input"
    wheel_zoom_amount = 3.0
    keyboard_zoom_amount = 1.0
    
    def __init__(self, app):
        self.app = app
        self.ui = self.app.ui
        # read from binds.cfg file or create it from template
        # exec results in edit_binds, a dict whose keys are keys+mods
        # and whose values are bound functions
        self.edit_bind_src = None
        # bad probs if a command isn't in binds.cfg, so just blow it away
        # if the template is newer than it
        # TODO: better solution is find any binds in template but not binds.cfg
        # and add em
        binds_filename = self.app.config_dir + BINDS_FILENAME
        binds_outdated = not os.path.exists(binds_filename) or os.path.getmtime(binds_filename) < os.path.getmtime(BINDS_TEMPLATE_FILENAME)
        if not binds_outdated and os.path.exists(binds_filename):
            exec(open(binds_filename).read())
            self.app.log('Loaded key binds from %s' % binds_filename)
        else:
            default_data = open(BINDS_TEMPLATE_FILENAME).readlines()[1:]
            new_binds = open(binds_filename, 'w')
            new_binds.writelines(default_data)
            new_binds.close()
            self.app.log('Created new key binds file %s' % binds_filename)
            exec(''.join(default_data))
        if not self.edit_bind_src:
            self.app.log('No bind data found, Is binds.cfg.default present?')
            exit()
        # associate key + mod combos with methods
        self.edit_binds = {}
        for bind_string in self.edit_bind_src:
            bind = self.parse_key_bind(bind_string)
            if not bind:
                continue
            # bind data could be a single item (string) or a list/tuple
            bind_data = self.edit_bind_src[bind_string]
            if type(bind_data) is str:
                bind_fnames = ['BIND_%s' % bind_data]
            else:
                bind_fnames = ['BIND_%s' % s for s in bind_data]
            bind_functions = []
            for bind_fname in bind_fnames:
                if not hasattr(self, bind_fname):
                    continue
                bind_functions.append(getattr(self, bind_fname))
            self.edit_binds[bind] = bind_functions
        # get controller(s)
        # TODO: use kewl SDL2 gamepad system
        js_init = sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_JOYSTICK)
        if js_init != 0:
            self.app.log("SDL2: Couldn't initialize joystick subsystem, code %s" % js_init)
            return
        sticks = sdl2.SDL_NumJoysticks()
        #self.app.log('%s gamepads found' % sticks)
        self.gamepad = None
        self.gamepad_left_x, self.gamepad_left_y = 0, 0
        # for now, just grab first pad
        if sticks > 0:
            pad = sdl2.SDL_JoystickOpen(0)
            pad_name = sdl2.SDL_JoystickName(pad).decode('utf-8')
            pad_axes = sdl2.SDL_JoystickNumAxes(pad)
            pad_buttons = sdl2.SDL_JoystickNumButtons(pad)
            self.app.log('Gamepad found: %s with %s axes, %s buttons' % (pad_name, pad_axes, pad_buttons))
            self.gamepad = pad
        # before main loop begins, set initial mouse position -
        # SDL_GetMouseState returns 0,0 if the mouse hasn't yet moved
        # in the new window!
        wx, wy = ctypes.c_int(0), ctypes.c_int(0)
        sdl2.SDL_GetWindowPosition(self.app.window, wx, wy)
        wx, wy = int(wx.value), int(wy.value)
        mx, my = ctypes.c_int(0), ctypes.c_int(0)
        sdl2.mouse.SDL_GetGlobalMouseState(mx, my)
        mx, my = int(mx.value), int(my.value)
        self.app.mouse_x, self.app.mouse_y = mx - wx, my - wy
        # set flag so we know whether handle_input's SDL_GetMouseState result
        # is accurate :/
        self.mouse_has_moved = False
    
    def parse_key_bind(self, in_string):
        "returns a tuple of (key, mod1, mod2) key bind data from given string"
        shift = False
        alt = False
        ctrl = False
        key = None
        for i in in_string.split():
            if i.lower() == 'shift':
                shift = True
            elif i.lower() == 'alt':
                alt = True
            elif i.lower() == 'ctrl':
                ctrl = True
            else:
                key = i
        return (key, shift, alt, ctrl)
    
    def get_bind_functions(self, keysym, shift, alt, ctrl):
        "returns a list of methods for the given key + mods if one exists"
        keystr = sdl2.SDL_GetKeyName(keysym).decode().lower()
        key_data = (keystr, shift, alt, ctrl)
        return self.edit_binds.get(key_data, [])
    
    def get_keysym(self, event):
        "get SDL2 keysym from event; right now only used to check numlock variants"
        numlock_on = bool(event.key.keysym.mod & sdl2.KMOD_NUM)
        keysym = event.key.keysym.sym
        # if numlock is on, treat numpad keys like numbers
        if numlock_on and keysym in NUMLOCK_ON_MAP:
            return NUMLOCK_ON_MAP[keysym]
        elif not numlock_on and keysym in NUMLOCK_OFF_MAP:
            return NUMLOCK_OFF_MAP[keysym]
        return keysym
    
    def get_command_shortcut(self, command_function):
        for bind in self.edit_bind_src:
            if command_function == self.edit_bind_src[bind]:
                return bind
        return ''
    
    def get_menu_items_for_command_function(self, function):
        # search both menus for items; command checks
        buttons = self.ui.art_menu_bar.menu_buttons + self.ui.game_menu_bar.menu_buttons
        items = []
        for button in buttons:
            # skip eg playscii button
            if not hasattr(button, 'menu_data'):
                continue
            for item in button.menu_data.items:
                if function.__name__ == 'BIND_%s' % item.command:
                    items.append(item)
        return items
    
    def is_command_function_allowed(self, function):
        "returns True if given function's menu bar item is available"
        items = self.get_menu_items_for_command_function(function)
        if not items:
            return True
        # return True if ANY items are active
        for item in items:
            if not item.always_active and item.should_dim(self.app):
                continue
            if item.art_mode_allowed and not self.app.game_mode:
                return True
            if item.game_mode_allowed and self.app.game_mode:
                return True
        return False
    
    def handle_input(self):
        app = self.app
        # get and store mouse state
        # (store everything in parent app object so stuff can access it easily)
        mx, my = ctypes.c_int(0), ctypes.c_int(0)
        mouse = sdl2.mouse.SDL_GetMouseState(mx, my)
        app.left_mouse = bool(mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_LEFT))
        app.middle_mouse = bool(mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_MIDDLE))
        app.right_mouse = bool(mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_RIGHT))
        mx, my = int(mx.value), int(my.value)
        # if mouse hasn't moved since init, disregard SDL_GetMouseState
        if self.mouse_has_moved:
            app.mouse_x, app.mouse_y = mx, my
        elif mx != 0 or my != 0:
            self.mouse_has_moved = True
        # relative mouse move state
        mdx, mdy = ctypes.c_int(0), ctypes.c_int(0)
        sdl2.mouse.SDL_GetRelativeMouseState(mdx, mdy)
        if self.mouse_has_moved:
            app.mouse_dx, app.mouse_dy = int(mdx.value), int(mdy.value)
        if app.mouse_dx != 0 or app.mouse_dy != 0:
            app.keyboard_editing = False
            # dragging a dialog?
            if app.left_mouse and self.ui.active_dialog in self.ui.hovered_elements:
                self.ui.active_dialog.update_drag(app.mouse_dx, app.mouse_dy)
        # get keyboard state so later we can directly query keys
        ks = sdl2.SDL_GetKeyboardState(None)
        # get modifier states
        self.shift_pressed, self.alt_pressed, self.ctrl_pressed = False, False, False
        if ks[sdl2.SDL_SCANCODE_LSHIFT] or ks[sdl2.SDL_SCANCODE_RSHIFT]:
            self.shift_pressed = True
        if ks[sdl2.SDL_SCANCODE_LALT] or ks[sdl2.SDL_SCANCODE_RALT]:
            self.alt_pressed = True
        if ks[sdl2.SDL_SCANCODE_LCTRL] or ks[sdl2.SDL_SCANCODE_RCTRL]:
            self.ctrl_pressed = True
        # macOS: treat command as interchangeable with control, is this kosher?
        if platform.system() == 'Darwin' and (ks[sdl2.SDL_SCANCODE_LGUI] or ks[sdl2.SDL_SCANCODE_RGUI]):
            self.ctrl_pressed = True
        if app.capslock_is_ctrl and ks[sdl2.SDL_SCANCODE_CAPSLOCK]:
            self.ctrl_pressed = True
        # pack mods into a tuple to save listing em all out repeatedly
        mods = self.shift_pressed, self.alt_pressed, self.ctrl_pressed
        # get controller state
        if self.gamepad:
            self.gamepad_left_x = sdl2.SDL_JoystickGetAxis(self.gamepad, sdl2.SDL_CONTROLLER_AXIS_LEFTX) / 32768
            self.gamepad_left_y = sdl2.SDL_JoystickGetAxis(self.gamepad, sdl2.SDL_CONTROLLER_AXIS_LEFTY) / -32768
        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                app.should_quit = True
            elif event.type == sdl2.SDL_WINDOWEVENT:
                if event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED:
                    # test window we create on init to detect resolution makes
                    # SDL think we've resized main app window on first tick!
                    if app.updates > 0:
                        app.resize_window(event.window.data1, event.window.data2)
            elif event.type == sdl2.SDL_JOYBUTTONDOWN:
                if not app.gw.paused and app.gw.player:
                    app.gw.player.button_pressed(event.jbutton.button)
            elif event.type == sdl2.SDL_JOYBUTTONUP:
                if not app.gw.paused and app.gw.player:
                    self.app.gw.player.button_unpressed(event.jbutton.button)
            elif event.type == sdl2.SDL_KEYDOWN:
                keysym = self.get_keysym(event)
                # if console is up, pass input to it
                if self.ui.console.visible:
                    self.ui.console.handle_input(keysym, *mods)
                # same with dialog box
                elif self.ui.active_dialog and self.ui.active_dialog is self.ui.keyboard_focus_element:
                    self.ui.active_dialog.handle_input(keysym, *mods)
                    # bail, process no further input
                    #sdl2.SDL_PumpEvents()
                    #return
                # handle text input if text tool is active
                elif self.ui.selected_tool is self.ui.text_tool and self.ui.text_tool.input_active:
                    self.ui.text_tool.handle_keyboard_input(keysym, *mods)
                # see if there's a function for this bind and run it
                else:
                    flist = self.get_bind_functions(keysym, *mods)
                    for f in flist:
                        # don't run any command whose menu bar item's dimmed / not allowed (ie wrong mode)
                        if self.is_command_function_allowed(f):
                            f()
                    # if game mode active, pass to world as well as any binds
                    if self.app.game_mode:
                        self.app.gw.handle_input(event, *mods)
            # for key up events, use the same binds but handle them special case
            # TODO: once there are enough key up events, figure out a more
            # elegant way than this
            elif event.type == sdl2.SDL_KEYUP:
                keysym = self.get_keysym(event)
                if self.app.game_mode:
                    self.app.gw.handle_input(event, *mods)
                # dismiss selector popup
                flist = self.get_bind_functions(keysym, *mods)
                if not flist:
                    pass
                elif self.ui.active_dialog:
                    # keyup shouldn't have any special meaning in a dialog
                    pass
                elif self.BIND_game_grab in flist:
                    if self.app.game_mode and not self.ui.active_dialog and self.app.gw.player:
                        self.app.gw.player.button_unpressed(0)
                        return
                elif self.BIND_toggle_picker in flist:
                    # ..but only for default hold-to-show setting
                    if self.ui.popup_hold_to_show:
                        self.ui.popup.hide()
                elif self.BIND_select_or_paint in flist:
                    app.keyboard_editing = True
                    if not self.ui.selected_tool is self.ui.text_tool and not self.ui.text_tool.input_active:
                        self.app.cursor.finish_paint()
            #
            # mouse events aren't handled by bind table for now
            #
            elif event.type == sdl2.SDL_MOUSEWHEEL:
                ui_wheeled = self.ui.wheel_moved(event.wheel.y)
                if not ui_wheeled:
                    if self.app.can_edit:
                        if event.wheel.y > 0:
                            # only zoom in should track towards cursor
                            app.camera.zoom(-self.wheel_zoom_amount,
                                            towards_cursor=True)
                        elif event.wheel.y < 0:
                            app.camera.zoom(self.wheel_zoom_amount)
                    else:
                        self.app.gw.mouse_wheeled(event.wheel.y)
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                # "consume" input if UI handled it
                ui_unclicked = self.ui.unclicked(event.button.button)
                if ui_unclicked:
                    sdl2.SDL_PumpEvents()
                    return
                if self.app.game_mode:
                    self.app.gw.unclicked(event.button.button)
                # LMB up: finish paint for most tools, end select drag
                if event.button.button == sdl2.SDL_BUTTON_LEFT:
                    if self.ui.selected_tool is self.ui.select_tool and self.ui.select_tool.selection_in_progress:
                        self.ui.select_tool.finish_select(self.shift_pressed, self.ctrl_pressed)
                    elif not self.ui.selected_tool is self.ui.text_tool and not self.ui.text_tool.input_active:
                        app.cursor.finish_paint()
            elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                ui_clicked = self.ui.clicked(event.button.button)
                # don't register edit commands if a menu is up
                if ui_clicked or self.ui.menu_bar.active_menu_name or self.ui.active_dialog:
                    sdl2.SDL_PumpEvents()
                    if self.app.game_mode:
                        self.app.gw.last_click_on_ui = True
                    return
                # pass clicks through to game world
                if self.app.game_mode:
                    if not ui_clicked:
                        self.app.gw.clicked(event.button.button)
                # LMB down: start text entry, start select drag, or paint
                elif event.button.button == sdl2.SDL_BUTTON_LEFT:
                    if not self.ui.active_art:
                        return
                    elif self.ui.selected_tool is self.ui.text_tool:
                        # text tool: only start entry if click is outside popup
                        if not self.ui.text_tool.input_active and \
                         not self.ui.popup in self.ui.hovered_elements:
                            self.ui.text_tool.start_entry()
                    elif self.ui.selected_tool is self.ui.select_tool:
                        # select tool: accept clicks if they're outside the popup
                        if not self.ui.select_tool.selection_in_progress and \
                            (not self.ui.keyboard_focus_element or \
                               (self.ui.keyboard_focus_element is self.ui.popup and \
                                not self.ui.popup in self.ui.hovered_elements)):
                                self.ui.select_tool.start_select()
                    else:
                        app.cursor.start_paint()
                elif event.button.button == sdl2.SDL_BUTTON_RIGHT:
                    if self.app.ui.active_art:
                        self.ui.quick_grab()
        # none of the below applies to cases where a dialog is up
        if self.ui.active_dialog:
            sdl2.SDL_PumpEvents()
            return
        # directly query keys we don't want affected by OS key repeat delay
        # TODO: these are hard-coded for the moment, think of a good way
        # to expose this functionality to the key bind system
        def pressing_up(ks):
            return ks[sdl2.SDL_SCANCODE_W] or ks[sdl2.SDL_SCANCODE_UP] or ks[sdl2.SDL_SCANCODE_KP_8]
        def pressing_down(ks):
            return ks[sdl2.SDL_SCANCODE_S] or ks[sdl2.SDL_SCANCODE_DOWN] or ks[sdl2.SDL_SCANCODE_KP_2]
        def pressing_left(ks):
            return ks[sdl2.SDL_SCANCODE_A] or ks[sdl2.SDL_SCANCODE_LEFT] or ks[sdl2.SDL_SCANCODE_KP_4]
        def pressing_right(ks):
            return ks[sdl2.SDL_SCANCODE_D] or ks[sdl2.SDL_SCANCODE_RIGHT] or ks[sdl2.SDL_SCANCODE_KP_6]
        # prevent camera move if: console is up, text input is active, editing
        # is not allowed
        if self.shift_pressed and not self.alt_pressed and not self.ctrl_pressed and not self.ui.console.visible and not self.ui.text_tool.input_active and self.app.can_edit and self.ui.keyboard_focus_element is None:
            if pressing_up(ks):
                app.camera.pan(0, 1, True)
            if pressing_down(ks):
                app.camera.pan(0, -1, True)
            if pressing_left(ks):
                app.camera.pan(-1, 0, True)
            if pressing_right(ks):
                app.camera.pan(1, 0, True)
            if ks[sdl2.SDL_SCANCODE_X]:
                app.camera.zoom(-self.keyboard_zoom_amount, keyboard=True,
                                towards_cursor=True)
            if ks[sdl2.SDL_SCANCODE_Z]:
                app.camera.zoom(self.keyboard_zoom_amount, keyboard=True)
        if self.app.can_edit and app.middle_mouse and (app.mouse_dx != 0 or app.mouse_dy != 0):
            app.camera.mouse_pan(app.mouse_dx, app.mouse_dy)
        # game mode: arrow keys and left gamepad stick move player
        if self.app.game_mode and not self.ui.console.visible and not self.ui.active_dialog and self.ui.keyboard_focus_element is None:
            if pressing_up(ks):
                # shift = move selected
                if self.shift_pressed and self.app.can_edit:
                    app.gw.move_selected(0, 1, 0)
                elif not self.ctrl_pressed and app.gw.player:
                    app.gw.player.move(0, 1)
            if pressing_down(ks):
                if self.shift_pressed and self.app.can_edit:
                    app.gw.move_selected(0, -1, 0)
                elif not self.ctrl_pressed and app.gw.player:
                    app.gw.player.move(0, -1)
            if pressing_left(ks):
                if self.shift_pressed and self.app.can_edit:
                    app.gw.move_selected(-1, 0, 0)
                elif not self.ctrl_pressed and app.gw.player:
                    app.gw.player.move(-1, 0)
            if pressing_right(ks):
                if self.shift_pressed and self.app.can_edit:
                    app.gw.move_selected(1, 0, 0)
                elif not self.ctrl_pressed and app.gw.player:
                    app.gw.player.move(1, 0)
            if abs(self.gamepad_left_x) > 0.15 and app.gw.player:
                app.gw.player.move(self.gamepad_left_x, 0)
            if abs(self.gamepad_left_y) > 0.15 and app.gw.player:
                app.gw.player.move(0, self.gamepad_left_y)
        sdl2.SDL_PumpEvents()
    
    def is_key_pressed(self, key):
        "returns True if given key is pressed"
        key = bytes(key, encoding='utf-8')
        scancode = sdl2.keyboard.SDL_GetScancodeFromName(key)
        return sdl2.SDL_GetKeyboardState(None)[scancode]
    
    #
    # bind functions
    #
    # function names correspond with key values in binds.cfg
    def BIND_quit(self):
        for art in self.app.art_loaded_for_edit:
            if art.unsaved_changes and self.app.can_edit:
                if self.app.game_mode:
                    self.app.exit_game_mode()
                self.ui.set_active_art(art)
                self.ui.open_dialog(QuitUnsavedChangesDialog)
                return
        self.app.should_quit = True
    
    def BIND_toggle_console(self):
        self.ui.console.toggle()
    
    def BIND_import_file(self):
        self.ui.open_dialog(ImportFileDialog)
    
    def BIND_export_file(self):
        self.ui.open_dialog(ExportFileDialog)
    
    def BIND_export_file_last(self):
        # if user hasn't exported this session, pick an exporter
        if self.ui.app.exporter:
            # redo export with appropriate filename & last options if they have
            out_filename = self.ui.active_art.filename
            out_filename = os.path.basename(out_filename)
            out_filename = os.path.splitext(out_filename)[0]
            ExportOptionsDialog.do_export(self.ui.app, out_filename,
                                          self.ui.app.last_export_options)
        else:
            self.ui.open_dialog(ExportFileDialog)
    
    def BIND_decrease_ui_scale(self):
        if self.ui.scale > SCALE_INCREMENT * 2:
            self.ui.set_scale(self.ui.scale - SCALE_INCREMENT)
    
    def BIND_increase_ui_scale(self):
        # cap UI scale at 2
        if self.ui.scale + SCALE_INCREMENT < 2.0:
            self.ui.set_scale(self.ui.scale + SCALE_INCREMENT)
    
    def BIND_toggle_fullscreen(self):
        self.app.toggle_fullscreen()
    
    def BIND_decrease_brush_size(self):
        self.ui.selected_tool.decrease_brush_size()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_increase_brush_size(self):
        self.ui.selected_tool.increase_brush_size()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_cycle_char_forward(self):
        self.ui.select_char(self.ui.selected_char+1)
    
    def BIND_cycle_char_backward(self):
        self.ui.select_char(self.ui.selected_char-1)
    
    def BIND_cycle_fg_forward(self):
        self.ui.select_fg(self.ui.selected_fg_color+1)
    
    def BIND_cycle_fg_backward(self):
        self.ui.select_fg(self.ui.selected_fg_color-1)
    
    def BIND_cycle_bg_forward(self):
        self.ui.select_bg(self.ui.selected_bg_color+1)
    
    def BIND_cycle_bg_backward(self):
        self.ui.select_bg(self.ui.selected_bg_color-1)
    
    def BIND_cycle_xform_forward(self):
        self.ui.cycle_selected_xform()
    
    def BIND_cycle_xform_backward(self):
        self.ui.cycle_selected_xform(True)
    
    def BIND_toggle_affects_char(self):
        self.ui.selected_tool.toggle_affects_char()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_affects_fg(self):
        self.ui.selected_tool.toggle_affects_fg()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_affects_bg(self):
        self.ui.selected_tool.toggle_affects_bg()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_affects_xform(self):
        self.ui.selected_tool.toggle_affects_xform()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_crt(self):
        self.app.fb.toggle_crt()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_select_pencil_tool(self):
        self.ui.set_selected_tool(self.ui.pencil_tool)
    
    def BIND_select_erase_tool(self):
        self.ui.set_selected_tool(self.ui.erase_tool)
    
    def BIND_select_rotate_tool(self):
        self.ui.set_selected_tool(self.ui.rotate_tool)
    
    def BIND_select_grab_tool(self):
        self.ui.set_selected_tool(self.ui.grab_tool)
    
    def BIND_select_text_tool(self):
        self.ui.set_selected_tool(self.ui.text_tool)
    
    def BIND_select_select_tool(self):
        self.ui.set_selected_tool(self.ui.select_tool)
    
    def BIND_cut_selection(self):
        self.ui.cut_selection()
        # switch to PasteTool
        self.ui.set_selected_tool(self.ui.paste_tool)
        # clear selection
        self.ui.select_none()
        self.ui.tool_settings_changed = True
    
    def BIND_copy_selection(self):
        self.ui.copy_selection()
        # switch to PasteTool
        self.ui.set_selected_tool(self.ui.paste_tool)
        # clear selection
        self.ui.select_none()
        self.ui.tool_settings_changed = True
    
    def BIND_select_paste_tool(self):
        self.ui.set_selected_tool(self.ui.paste_tool)
    
    def BIND_select_none(self):
        if self.app.game_mode:
            self.app.gw.deselect_all()
        else:
            self.ui.select_none()
    
    def BIND_cancel(self):
        # context-dependent:
        # game mode: deselect
        # normal painting mode: cancel current selection
        # menu bar active: bail out of current menu
        # either way: bail on image conversion if it's happening
        if self.app.converter:
            self.app.converter.finish(True)
        if self.ui.menu_bar.active_menu_name:
            self.ui.menu_bar.close_active_menu()
        elif self.app.game_mode:
            # bail out of list if it's active
            if self.ui.keyboard_focus_element is self.ui.edit_list_panel:
                self.ui.edit_list_panel.cancel()
            else:
                self.app.gw.deselect_all()
        else:
            self.ui.select_none()
    
    def BIND_select_all(self):
        self.ui.select_all()
    
    def BIND_select_invert(self):
        self.ui.invert_selection()
    
    def BIND_edit_cfg(self):
        self.ui.menu_bar.close_active_menu()
        self.app.edit_cfg()
    
    def BIND_erase_selection_or_art(self):
        # if in game mode, delete selected objects
        if self.app.game_mode:
            # operate on a copy of selected objects list,
            # as obj.destroy() removes itself from original
            for obj in self.app.gw.selected_objects[:]:
                # some objects can't be deleted
                if obj.deleteable:
                    obj.destroy()
        else:
            self.ui.erase_selection_or_art()
    
    def BIND_toggle_game_mode(self):
        if not self.app.can_edit:
            return
        if not self.app.game_mode:
            self.app.enter_game_mode()
        else:
            self.app.exit_game_mode()
        self.app.update_window_title()
    
    def BIND_new_game_dir(self):
        self.ui.open_dialog(NewGameDirDialog)
    
    def BIND_set_game_dir(self):
        if self.app.can_edit:
            # show available games in list panel
            self.ui.edit_list_panel.set_list_operation(LO_OPEN_GAME_DIR)
    
    def BIND_load_game_state(self):
        self.ui.edit_list_panel.set_list_operation(LO_LOAD_STATE)
    
    def BIND_save_game_state(self):
        self.ui.open_dialog(SaveGameStateDialog)
    
    def BIND_reset_game(self):
        if self.app.game_mode and self.app.gw.game_dir:
            self.app.gw.reset_game()
    
    def BIND_toggle_picker(self):
        if not self.ui.active_art:
            return
        if self.ui.popup_hold_to_show:
            self.ui.popup.show()
        else:
            self.ui.popup.toggle()
    
    def BIND_toggle_picker_hold(self):
        self.ui.popup_hold_to_show = not self.ui.popup_hold_to_show
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_swap_fg_bg_colors(self):
        if self.ui.active_art:
            self.ui.swap_fg_bg_colors()
    
    def BIND_save_current(self):
        # save current game state in game mode, else save current art
        if self.app.game_mode and self.app.gw.game_dir:
            # as with reset, save over last loaded state
            self.app.gw.save_last_state()
        elif self.ui.active_art:
            # if new document, ask for a name
            default_name = ART_DIR + 'new.' + ART_FILE_EXTENSION
            if self.ui.active_art.filename == default_name:
                self.ui.open_dialog(SaveAsDialog)
            else:
                self.ui.active_art.save_to_file()
    
    def BIND_toggle_ui_visibility(self):
        self.ui.visible = not self.ui.visible
    
    def BIND_toggle_grid_visibility(self):
        self.app.grid.visible = not self.app.grid.visible
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_bg_texture(self):
        self.app.show_bg_texture = not self.app.show_bg_texture
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_previous_frame(self):
        self.ui.set_active_frame(self.ui.active_art.active_frame - 1)
    
    def BIND_next_frame(self):
        self.ui.set_active_frame(self.ui.active_art.active_frame + 1)
    
    def BIND_toggle_anim_playback(self):
        # if game mode, pause/unpause
        if self.app.game_mode:
            self.toggle_pause()
            return
        for r in self.ui.active_art.renderables:
            if r.animating:
                r.stop_animating()
            else:
                r.start_animating()
        self.ui.menu_bar.refresh_active_menu()
    
    def toggle_pause(self):
        self.app.gw.toggle_pause()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_previous_layer(self):
        self.ui.set_active_layer(self.ui.active_art.active_layer - 1)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_next_layer(self):
        self.ui.set_active_layer(self.ui.active_art.active_layer + 1)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_previous_art(self):
        self.ui.previous_active_art()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_next_art(self):
        if len(self.app.art_loaded_for_edit) == 0:
            return
        self.ui.next_active_art()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_undo(self):
        self.ui.undo()
    
    def BIND_redo(self):
        self.ui.redo()
    
    def BIND_quick_grab(self):
        if not self.ui.active_art:
            return
        self.app.keyboard_editing = True
        self.ui.quick_grab()
    
    def BIND_set_camera_zoom(self):
        self.ui.open_dialog(SetCameraZoomDialog)
    
    def BIND_camera_zoom_in_proportional(self):
        self.app.camera.zoom_proportional(1)
    
    def BIND_camera_zoom_out_proportional(self):
        self.app.camera.zoom_proportional(-1)
    
    def BIND_toggle_zoom_extents(self):
        self.app.camera.toggle_zoom_extents()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_camera_tilt(self):
        if self.app.camera.y_tilt == 2:
            self.app.camera.y_tilt = 0
            self.ui.message_line.post_line('Camera tilt disengaged.')
        else:
            self.app.camera.y_tilt = 2
            self.ui.message_line.post_line('Camera tilt engaged.')
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_add_to_list_selection(self):
        if not self.ui.edit_list_panel.is_visible():
            return
        self.ui.edit_list_panel.keyboard_select_item()
    
    def BIND_remove_from_list_selection(self):
        if not self.ui.edit_list_panel.is_visible():
            return
        self.ui.edit_list_panel.keyboard_select_item()
    
    def BIND_select_or_paint(self):
        if self.ui.keyboard_focus_element:
            # save current focus element because kb_select_item might change it!
            selected_element = self.ui.keyboard_focus_element
            # get button pressed in case we need its item
            button = self.ui.keyboard_focus_element.keyboard_select_item()
            if selected_element is self.ui.pulldown:
                # mirror behavior from MenuItemButton.click: close on select if needed
                if button and button.item.close_on_select:
                    self.ui.menu_bar.close_active_menu()
            return
        if not self.ui.active_art:
            return
        elif self.ui.selected_tool is self.ui.text_tool and not self.ui.text_tool.input_active:
            self.ui.text_tool.start_entry()
        elif self.ui.selected_tool is self.ui.select_tool:
            if self.ui.select_tool.selection_in_progress:
                # pass in shift/alt for add/subtract
                self.ui.select_tool.finish_select(self.shift_pressed, self.ctrl_pressed)
            else:
                self.ui.select_tool.start_select()
        else:
            self.app.cursor.start_paint()
    
    def BIND_screenshot(self):
        self.app.screenshot()
    
    def BIND_run_test_mutate(self):
        if self.ui.active_art.is_script_running('conway'):
            self.ui.active_art.stop_script('conway')
        else:
            self.ui.active_art.run_script_every('conway', 0.05)
    
    def BIND_arrow_up(self):
        if self.ui.keyboard_focus_element:
            self.ui.keyboard_navigate(0, -1)
        else:
            self.app.cursor.keyboard_move(0, 1)
    
    def BIND_arrow_down(self):
        if self.ui.keyboard_focus_element:
            self.ui.keyboard_navigate(0, 1)
        else:
            self.app.cursor.keyboard_move(0, -1)
    
    def BIND_arrow_left(self):
        # navigate popup, menu bar etc
        if self.ui.keyboard_focus_element:
            self.ui.keyboard_navigate(-1, 0)
        else:
            self.app.cursor.keyboard_move(-1, 0)
    
    def BIND_arrow_right(self):
        if self.ui.keyboard_focus_element:
            self.ui.keyboard_navigate(1, 0)
        else:
            self.app.cursor.keyboard_move(1, 0)
    
    def BIND_cycle_inactive_layer_visibility(self):
        if not self.ui.active_art:
            return
        if self.ui.active_art.layers == 1:
            return
        message_text = 'Non-active layers: '
        if self.app.inactive_layer_visibility == LAYER_VIS_FULL:
            self.app.inactive_layer_visibility = LAYER_VIS_DIM
            message_text += 'dim'
        elif self.app.inactive_layer_visibility == LAYER_VIS_DIM:
            self.app.inactive_layer_visibility = LAYER_VIS_NONE
            message_text += 'invisible'
        else:
            self.app.inactive_layer_visibility = LAYER_VIS_FULL
            message_text += 'visible'
        self.ui.message_line.post_line(message_text)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_open_file_menu(self):
        self.ui.menu_bar.open_menu_by_name('file')
    
    def BIND_open_edit_menu(self):
        self.ui.menu_bar.open_menu_by_name('edit')
    
    def BIND_open_tool_menu(self):
        self.ui.menu_bar.open_menu_by_name('tool')
    
    def BIND_open_view_menu(self):
        self.ui.menu_bar.open_menu_by_name('view')
    
    def BIND_open_art_menu(self):
        self.ui.menu_bar.open_menu_by_name('art')
    
    def BIND_open_frame_menu(self):
        if self.app.game_mode:
            self.ui.menu_bar.open_menu_by_name('room')
        else:
            self.ui.menu_bar.open_menu_by_name('frame')
    
    def BIND_open_layer_menu(self):
        self.ui.menu_bar.open_menu_by_name('layer')
    
    def BIND_open_char_color_menu(self):
        self.ui.menu_bar.open_menu_by_name('char_color')
    
    def BIND_open_help_menu(self):
        self.ui.menu_bar.open_menu_by_name('help')
    
    def BIND_open_game_menu(self):
        self.ui.menu_bar.open_menu_by_name('game')
    
    def BIND_open_state_menu(self):
        self.ui.menu_bar.open_menu_by_name('state')
    
    def BIND_open_world_menu(self):
        self.ui.menu_bar.open_menu_by_name('world')
    
    def BIND_open_object_menu(self):
        self.ui.menu_bar.open_menu_by_name('object')
    
    def BIND_new_art(self):
        self.ui.open_dialog(NewArtDialog)
    
    def BIND_open_art(self):
        self.ui.open_dialog(ArtChooserDialog)
    
    def BIND_save_art_as(self):
        if self.app.game_mode:
            self.ui.open_dialog(SaveGameStateDialog)
        elif not self.ui.active_art:
            return
        else:
            self.ui.open_dialog(SaveAsDialog)
    
    def BIND_revert_art(self):
        if not self.ui.active_art:
            return
        if self.ui.active_art.unsaved_changes:
            self.ui.open_dialog(RevertChangesDialog)
    
    def BIND_close_art(self):
        if not self.ui.active_art:
            return
        if self.ui.active_art.unsaved_changes:
            self.ui.open_dialog(CloseUnsavedChangesDialog)
            return
        self.app.close_art(self.ui.active_art)
        # dismiss popup if no more arts are open
        if self.ui.popup.visible and len(self.app.art_loaded_for_edit) == 0:
            self.ui.popup.hide()
    
    def BIND_open_help_docs(self):
        self.app.open_help_docs()
    
    def BIND_generate_docs(self):
        self.app.generate_docs()
    
    def BIND_open_website(self):
        self.app.open_website()
    
    def BIND_crop_to_selection(self):
        self.ui.crop_to_selection(self.ui.active_art)
    
    def BIND_resize_art(self):
        self.ui.open_dialog(ResizeArtDialog)
    
    def BIND_art_flip_horizontal(self):
        self.ui.active_art.flip_horizontal(self.ui.active_art.active_frame,
                                           self.ui.active_art.active_layer)
    
    def BIND_art_flip_vertical(self):
        self.ui.active_art.flip_vertical(self.ui.active_art.active_frame,
                                         self.ui.active_art.active_layer)
    
    def BIND_art_toggle_flip_affects_xforms(self):
        self.ui.flip_affects_xforms = not self.ui.flip_affects_xforms
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_run_art_script(self):
        self.ui.open_dialog(RunArtScriptDialog)
    
    def BIND_run_art_script_last(self):
        # if user hasn't run a script this session, pick one
        if not self.ui.app.last_art_script:
            self.BIND_run_art_script()
        else:
            self.ui.active_art.run_script(self.ui.app.last_art_script, log=False)
    
    def BIND_art_switch_to(self, art_filename):
        self.ui.set_active_art_by_filename(art_filename)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_add_frame(self):
        self.ui.open_dialog(AddFrameDialog)
    
    def BIND_duplicate_frame(self):
        self.ui.open_dialog(DuplicateFrameDialog)
    
    def BIND_change_frame_delay(self):
        self.ui.open_dialog(FrameDelayDialog)
    
    def BIND_change_frame_delay_all(self):
        self.ui.open_dialog(FrameDelayAllDialog)
    
    def BIND_delete_frame(self):
        self.ui.active_art.delete_frame_at(self.ui.active_art.active_frame)
    
    def BIND_change_frame_index(self):
        self.ui.open_dialog(FrameIndexDialog)
    
    def BIND_add_layer(self):
        self.ui.open_dialog(AddLayerDialog)
    
    def BIND_duplicate_layer(self):
        self.ui.open_dialog(DuplicateLayerDialog)
    
    def BIND_layer_switch_to(self, layer_number):
        self.ui.set_active_layer(layer_number)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_change_layer_name(self):
        self.ui.open_dialog(SetLayerNameDialog)
    
    def BIND_change_layer_z(self):
        self.ui.open_dialog(SetLayerZDialog)
    
    def BIND_toggle_layer_visibility(self):
        art = self.ui.active_art
        is_visible = art.layers_visibility[art.active_layer]
        art.layers_visibility[art.active_layer] = not is_visible
        art.set_unsaved_changes(True)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_hidden_layers_visible(self):
        self.app.show_hidden_layers = not self.app.show_hidden_layers
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_delete_layer(self):
        self.ui.active_art.delete_layer(self.ui.active_art.active_layer)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_choose_charset(self):
        self.ui.open_dialog(CharSetChooserDialog)
    
    def BIND_choose_palette(self):
        self.ui.open_dialog(PaletteChooserDialog)
    
    def BIND_palette_from_file(self):
        self.ui.open_dialog(PaletteFromImageChooserDialog)
    
    def BIND_toggle_onion_visibility(self):
        self.app.onion_frames_visible = not self.app.onion_frames_visible
        if self.app.onion_frames_visible:
            self.ui.reset_onion_frames()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_cycle_onion_frames(self):
        self.app.onion_show_frames += 1
        self.app.onion_show_frames %= self.app.max_onion_frames + 1
        # start cycle at 1, not 0
        self.app.onion_show_frames = max(1, self.app.onion_show_frames)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_cycle_onion_ahead_behind(self):
        # cycle between next, previous, next & previous
        if self.app.onion_show_frames_behind and self.app.onion_show_frames_ahead:
            self.app.onion_show_frames_behind = False
        elif not self.app.onion_show_frames_behind and self.app.onion_show_frames_ahead:
            self.app.onion_show_frames_behind = True
            self.app.onion_show_frames_ahead = False
        else:
            self.app.onion_show_frames_ahead = True
            self.app.onion_show_frames_ahead = True
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_debug_text(self):
        self.ui.debug_text.visible = not self.ui.debug_text.visible
    
    def BIND_toggle_fps_counter(self):
        self.ui.fps_counter.visible = not self.ui.fps_counter.visible
    
    def BIND_open_all_game_assets(self):
        for game_obj in self.app.gw.objects.values():
            for art_filename in game_obj.get_all_art():
                self.app.load_art_for_edit(art_filename)
        # open all hud assets too
        for art in self.app.gw.hud.arts:
            self.app.load_art_for_edit(art.filename)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_all_collision_viz(self):
        self.app.gw.toggle_all_collision_viz()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_all_bounds_viz(self):
        self.app.gw.toggle_all_bounds_viz()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_all_origin_viz(self):
        self.app.gw.toggle_all_origin_viz()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_collision_on_selected(self):
        for obj in self.app.gw.selected_objects:
            if obj.orig_collision_type and obj.collision_type == CT_NONE:
                obj.enable_collision()
                self.ui.message_line.post_line('Collision enabled for %s' % obj.name)
            elif obj.collision_type != CT_NONE:
                obj.disable_collision()
                self.ui.message_line.post_line('Collision disabled for %s' % obj.name)
    
    def BIND_toggle_game_edit_ui(self):
        self.ui.toggle_game_edit_ui()
    
    #
    # game mode binds
    #
    def accept_normal_game_input(self):
        return self.app.game_mode and self.app.gw.player and not self.ui.active_dialog and not self.ui.pulldown.visible
    
    # TODO: generalize these two somehow
    def BIND_game_frob(self):
        if self.accept_normal_game_input():
            self.app.gw.player.button_pressed(1)
    
    def BIND_game_grab(self):
        if self.accept_normal_game_input():
            self.app.gw.player.button_pressed(0)
    
    def BIND_center_cursor_in_art(self):
        self.app.cursor.center_in_art()
    
    def BIND_choose_spawn_object_class(self):
        if self.app.game_mode and self.app.gw.game_dir:
            self.ui.edit_list_panel.set_list_operation(LO_SET_SPAWN_CLASS)
    
    def BIND_duplicate_selected_objects(self):
        self.app.gw.duplicate_selected_objects()
    
    def BIND_select_objects(self):
        if self.app.game_mode and self.app.gw.game_dir:
            self.ui.edit_list_panel.set_list_operation(LO_SELECT_OBJECTS)
    
    def BIND_edit_art_for_selected_objects(self):
        self.app.gw.edit_art_for_selected()
    
    def BIND_edit_world_properties(self):
        self.app.gw.deselect_all()
        self.app.gw.select_object(self.app.gw.properties, force=True)
    
    def BIND_change_current_room(self):
        self.ui.edit_list_panel.set_list_operation(LO_SET_ROOM)
    
    def BIND_change_current_room_to(self, new_room_name):
        self.app.gw.change_room(new_room_name)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_add_room(self):
        self.ui.open_dialog(AddRoomDialog)
    
    def BIND_remove_current_room(self):
        self.app.gw.remove_room(self.app.gw.current_room.name)
    
    def BIND_set_room_objects(self):
        self.ui.edit_list_panel.set_list_operation(LO_SET_ROOM_OBJECTS)
    
    def BIND_set_object_rooms(self):
        self.ui.edit_list_panel.set_list_operation(LO_SET_OBJECT_ROOMS)
    
    def BIND_toggle_all_rooms_visible(self):
        self.app.gw.show_all_rooms = not self.app.gw.show_all_rooms
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_toggle_room_camera_changes(self):
        self.app.gw.properties.set_object_property('room_camera_changes_enabled', not self.app.gw.room_camera_changes_enabled)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_set_room_camera_marker(self):
        self.ui.open_dialog(SetRoomCamDialog)
        self.ui.edit_list_panel.set_list_operation(LO_SET_ROOM_CAMERA)
    
    def BIND_objects_to_camera(self):
        cam = self.app.gw.camera
        for obj in self.app.gw.selected_objects:
            obj.set_loc(cam.x, cam.y, cam.z)
    
    def BIND_camera_to_objects(self):
        if len(self.app.gw.selected_objects) == 0:
            return
        obj = self.app.gw.selected_objects[0]
        self.app.gw.camera.set_loc_from_obj(obj)
    
    def BIND_add_selected_to_room(self):
        if not self.app.gw.current_room:
            return
        for obj in self.app.gw.selected_objects:
            self.app.gw.current_room.add_object(obj)
    
    def BIND_remove_selected_from_room(self):
        if not self.app.gw.current_room:
            return
        for obj in self.app.gw.selected_objects:
            self.app.gw.current_room.remove_object(obj)
    
    def BIND_switch_edit_panel_focus(self):
        self.ui.switch_edit_panel_focus()
    
    def BIND_switch_edit_panel_focus_reverse(self):
        self.ui.switch_edit_panel_focus(reverse=True)
    
    def BIND_set_room_edge_warps(self):
        # bring up dialog before setting list so list knows about it
        self.ui.open_dialog(SetRoomEdgeWarpsDialog)
        self.ui.edit_list_panel.set_list_operation(LO_SET_ROOM_EDGE_WARP)
    
    def BIND_set_room_bounds_obj(self):
        self.ui.open_dialog(SetRoomBoundsObjDialog)
        self.ui.edit_list_panel.set_list_operation(LO_SET_ROOM_EDGE_OBJ)
    
    def BIND_toggle_list_only_room_objects(self):
        self.app.gw.list_only_current_room_objects = not self.app.gw.list_only_current_room_objects
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_rename_current_room(self):
        self.ui.open_dialog(RenameRoomDialog)
    
    def BIND_toggle_debug_objects(self):
        if not self.app.gw.properties:
            return
        self.app.gw.properties.set_object_property('draw_debug_objects', not self.app.gw.draw_debug_objects)
        self.ui.menu_bar.refresh_active_menu()
