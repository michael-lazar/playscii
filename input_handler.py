import ctypes, os
import sdl2
import webbrowser
from sys import exit

from ui import SCALE_INCREMENT
from renderable import LAYER_VIS_FULL, LAYER_VIS_DIM, LAYER_VIS_NONE
from ui_dialog import NewArtDialog, OpenArtDialog, SaveAsDialog, QuitUnsavedChangesDialog, CloseUnsavedChangesDialog, ResizeArtDialog, AddFrameDialog, DuplicateFrameDialog, FrameDelayDialog, FrameIndexDialog, AddLayerDialog, DuplicateLayerDialog, SetLayerNameDialog, SetLayerZDialog
from ui_info_dialog import PagedInfoDialog, HelpScreenDialog
from ui_chooser_dialog import CharSetChooserDialog, PaletteChooserDialog

BINDS_FILENAME = 'binds.cfg'
BINDS_TEMPLATE_FILENAME = 'binds.cfg.default'

class InputLord:
    
    "sets up key binds and handles input"
    
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
        binds_outdated = not os.path.exists(BINDS_FILENAME) or os.path.getmtime(BINDS_FILENAME) < os.path.getmtime(BINDS_TEMPLATE_FILENAME)
        if not binds_outdated and os.path.exists(BINDS_FILENAME):
            exec(open(BINDS_FILENAME).read())
        else:
            default_data = open(BINDS_TEMPLATE_FILENAME).readlines()[1:]
            new_binds = open(BINDS_FILENAME, 'w')
            new_binds.writelines(default_data)
            new_binds.close()
            self.app.log('Created new binds file %s' % BINDS_FILENAME)
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
            bind_function_name = 'BIND_%s' % self.edit_bind_src[bind_string]
            if not hasattr(self, bind_function_name):
                continue
            bind_function = getattr(self, bind_function_name)
            self.edit_binds[bind] = bind_function
    
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
    
    def get_bind_function(self, event, shift, alt, ctrl):
        "returns a method for the given event + mods if one exists"
        keystr = sdl2.SDL_GetKeyName(event.key.keysym.sym).decode().lower()
        key_data = (keystr, shift, alt, ctrl)
        return self.edit_binds.get(key_data, None)
    
    def input(self):
        app = self.app
        # get and store mouse state
        # (store everything in parent app object so stuff can access it easily)
        mx, my = ctypes.c_int(0), ctypes.c_int(0)
        mouse = sdl2.mouse.SDL_GetMouseState(mx, my)
        app.left_mouse = bool(mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_LEFT))
        app.middle_mouse = bool(mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_MIDDLE))
        app.right_mouse = bool(mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_RIGHT))
        app.mouse_x, app.mouse_y = int(mx.value), int(my.value)
        # relative mouse move state
        mdx, mdy = ctypes.c_int(0), ctypes.c_int(0)
        sdl2.mouse.SDL_GetRelativeMouseState(mdx, mdy)
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
        if app.capslock_is_ctrl and ks[sdl2.SDL_SCANCODE_CAPSLOCK]:
            self.ctrl_pressed = True
        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                app.should_quit = True
            elif event.type == sdl2.SDL_WINDOWEVENT:
                if event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED:
                    app.resize_window(event.window.data1, event.window.data2)
            elif event.type == sdl2.SDL_KEYDOWN:
                # if console is up, pass input to it
                if self.ui.console.visible:
                    self.ui.console.handle_input(event.key.keysym.sym,
                        self.shift_pressed, self.alt_pressed, self.ctrl_pressed)
                # same with dialog box
                elif self.ui.active_dialog:
                    self.ui.active_dialog.handle_input(event.key.keysym.sym,
                        self.shift_pressed, self.alt_pressed, self.ctrl_pressed)
                # handle text input if text tool is active
                elif self.ui.selected_tool is self.ui.text_tool and self.ui.text_tool.input_active:
                    self.ui.text_tool.handle_keyboard_input(event.key.keysym.sym,
                        self.shift_pressed, self.ctrl_pressed, self.alt_pressed)
                # see if there's a function for this bind and run it
                else:
                    f = self.get_bind_function(event, self.shift_pressed, self.alt_pressed, self.ctrl_pressed)
                    if f:
                        f()
                # TEST: alt + arrow keys control game mode test renderable
                if self.app.game_mode and self.alt_pressed:
                    if event.key.keysym.sym == sdl2.SDLK_UP:
                        app.player.y += 1
                    elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                        app.player.y -= 1
                    elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                        app.player.x -= 1
                    elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                        app.player.x += 1
                    elif event.key.keysym.sym == sdl2.SDLK_a:
                        app.player.z += 0.5
                    elif event.key.keysym.sym == sdl2.SDLK_z:
                        app.player.z -= 0.5
            # for key up events, use the same binds but handle them special case
            # TODO: once there are enough key up events, figure out a more
            # elegant way than this
            elif event.type == sdl2.SDL_KEYUP:
                # dismiss selector popup
                f = self.get_bind_function(event, self.shift_pressed, self.alt_pressed, self.ctrl_pressed)
                if f == self.BIND_toggle_picker:
                    # ..but only for default hold-to-show setting
                    if self.ui.popup_hold_to_show:
                        self.ui.popup.hide()
                elif f == self.BIND_select_or_paint:
                    app.keyboard_editing = True
                    if not self.ui.selected_tool is self.ui.text_tool and not self.ui.text_tool.input_active:
                        self.app.cursor.finish_paint()
            #
            # mouse events aren't handled by bind table for now
            #
            elif event.type == sdl2.SDL_MOUSEWHEEL:
                if event.wheel.y > 0:
                    # use wheel to scroll chooser dialogs
                    if self.ui.active_dialog:
                        # TODO: look up "up arrow" bind instead? how to get
                        # an SDL keycode from that?
                        self.ui.active_dialog.handle_input(sdl2.SDLK_UP, self.shift_pressed, self.alt_pressed, self.ctrl_pressed)
                    else:
                        app.camera.zoom(-3)
                elif event.wheel.y < 0:
                    if self.ui.active_dialog:
                        self.ui.active_dialog.handle_input(sdl2.SDLK_DOWN, self.shift_pressed, self.alt_pressed, self.ctrl_pressed)
                    else:
                        app.camera.zoom(3)
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                self.ui.unclicked(event.button.button)
                # LMB up: finish paint for most tools, end select drag
                if event.button.button == sdl2.SDL_BUTTON_LEFT:
                    if self.ui.selected_tool is self.ui.select_tool and self.ui.select_tool.selection_in_progress:
                        self.ui.select_tool.finish_select(self.shift_pressed, self.ctrl_pressed)
                    elif not self.ui.selected_tool is self.ui.text_tool and not self.ui.text_tool.input_active:
                        app.cursor.finish_paint()
            elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                self.ui.clicked(event.button.button)
                # don't register edit commands if a menu is up
                if self.ui.menu_bar.active_menu_name or self.ui.active_dialog:
                    return
                # LMB down: start text entry, start select drag, or paint
                if event.button.button == sdl2.SDL_BUTTON_LEFT:
                    if not self.ui.active_art:
                        return
                    if self.ui.selected_tool is self.ui.text_tool and not self.ui.text_tool.input_active:
                        self.ui.text_tool.start_entry()
                    elif self.ui.selected_tool is self.ui.select_tool:
                        if not self.ui.select_tool.selection_in_progress:
                            self.ui.select_tool.start_select()
                    else:
                        app.cursor.start_paint()
                elif event.button.button == sdl2.SDL_BUTTON_RIGHT:
                    self.ui.quick_grab()
        # directly query keys we don't want affected by OS key repeat delay
        # TODO: these are hard-coded for the moment, think of a good way
        # to expose this functionality to the key bind system
        if self.shift_pressed and not self.alt_pressed and not self.ctrl_pressed and not self.ui.console.visible and not self.ui.text_tool.input_active:
            if ks[sdl2.SDL_SCANCODE_W] or ks[sdl2.SDL_SCANCODE_UP]:
                app.camera.pan(0, 1, True)
            if ks[sdl2.SDL_SCANCODE_S] or ks[sdl2.SDL_SCANCODE_DOWN]:
                app.camera.pan(0, -1, True)
            if ks[sdl2.SDL_SCANCODE_A] or ks[sdl2.SDL_SCANCODE_LEFT]:
                app.camera.pan(-1, 0, True)
            if ks[sdl2.SDL_SCANCODE_D] or ks[sdl2.SDL_SCANCODE_RIGHT]:
                app.camera.pan(1, 0, True)
            if ks[sdl2.SDL_SCANCODE_X]:
                app.camera.zoom(-1, True)
            if ks[sdl2.SDL_SCANCODE_Z]:
                app.camera.zoom(1, True)
        if app.middle_mouse and (app.mouse_dx != 0 or app.mouse_dy != 0):
            app.camera.mouse_pan(app.mouse_dx, app.mouse_dy)
        sdl2.SDL_PumpEvents()
    
    #
    # bind functions
    #
    # function names correspond with key values in binds.cfg
    
    def BIND_quit(self):
        for art in self.app.art_loaded_for_edit:
            if art.unsaved_changes:
                self.ui.set_active_art(art)
                self.ui.open_dialog(QuitUnsavedChangesDialog)
                return
        self.app.should_quit = True
    
    def BIND_toggle_console(self):
        self.ui.console.toggle()
    
    def BIND_export_image(self):
        if not self.ui.active_art:
            return
        self.app.export_image(self.ui.active_art)
    
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
    
    def BIND_increase_brush_size(self):
        self.ui.selected_tool.increase_brush_size()
    
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
    
    def BIND_toggle_affects_fg(self):
        self.ui.selected_tool.toggle_affects_fg()
    
    def BIND_toggle_affects_bg(self):
        self.ui.selected_tool.toggle_affects_bg()
    
    def BIND_toggle_affects_xform(self):
        self.ui.selected_tool.toggle_affects_xform()
    
    def BIND_toggle_crt(self):
        self.app.fb.toggle_crt()
    
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
    
    def BIND_copy_selection(self):
        self.ui.copy_selection()
    
    def BIND_select_paste_tool(self):
        self.ui.set_selected_tool(self.ui.paste_tool)
    
    def BIND_select_none(self):
        self.ui.select_none()
    
    def BIND_cancel(self):
        # context-dependent:
        # normal painting mode: cancel current selection
        # menu bar active: bail out of current menu
        if self.ui.menu_bar.active_menu_name:
            self.ui.menu_bar.close_active_menu()
        else:
            self.ui.select_none()
    
    def BIND_select_all(self):
        self.ui.select_all()
    
    def BIND_select_invert(self):
        self.ui.invert_selection()
    
    def BIND_erase_selection_or_art(self):
        self.ui.erase_selection_or_art()
    
    def BIND_toggle_game_mode(self):
        if not self.app.game_mode:
            self.app.enter_game_mode()
        else:
            self.app.exit_game_mode()
    
    def BIND_toggle_picker(self):
        if not self.ui.active_art:
            return
        if self.ui.popup_hold_to_show:
            self.ui.popup.show()
        else:
            self.ui.popup.toggle()
    
    def BIND_swap_fg_bg_colors(self):
        self.ui.swap_fg_bg_colors()
    
    def BIND_save_art(self):
        if self.ui.active_art:
            self.ui.active_art.save_to_file()
    
    def BIND_toggle_ui_visibility(self):
        self.ui.visible = not self.ui.visible
    
    def BIND_toggle_grid_visibility(self):
        self.app.grid.visible = not self.app.grid.visible
    
    def BIND_previous_frame(self):
        self.ui.set_active_frame(self.ui.active_frame - 1)
    
    def BIND_next_frame(self):
        self.ui.set_active_frame(self.ui.active_frame + 1)
    
    def BIND_toggle_anim_playback(self):
        animating = False
        for r in self.ui.active_art.renderables:
            r.animating = not r.animating
            animating = r.animating
        # restore to active frame if stopping
        if not animating:
            r.set_frame(self.ui.active_frame)
    
    def BIND_previous_layer(self):
        self.ui.set_active_layer(self.ui.active_layer - 1)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_next_layer(self):
        self.ui.set_active_layer(self.ui.active_layer + 1)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_previous_art(self):
        self.ui.previous_active_art()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_next_art(self):
        self.ui.next_active_art()
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_undo(self):
        self.ui.undo()
    
    def BIND_redo(self):
        self.ui.redo()
    
    def BIND_quick_grab(self):
        self.app.keyboard_editing = True
        self.ui.quick_grab()
    
    def BIND_toggle_camera_tilt(self):
        if self.app.camera.y_tilt == 2:
            self.app.camera.y_tilt = 0
            self.ui.message_line.post_line('Camera tilt disengaged.')
        else:
            self.app.camera.y_tilt = 2
            self.ui.message_line.post_line('Camera tilt engaged.')
    
    def BIND_select_or_paint(self):
        # select menu item if navigating pulldown
        if self.ui.menu_bar.active_menu_name:
            self.ui.pulldown.keyboard_select_item()
        if not self.ui.active_art:
            return
        if self.ui.popup.visible:
            # simulate left/right click in popup to select stuff
            self.ui.popup.select_key_pressed(self.shift_pressed)
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
    
    def BIND_run_game_mode_test(self):
        self.app.game_mode_test()
        self.app.enter_game_mode()
    
    def BIND_run_test_mutate(self):
        if self.ui.active_art.is_script_running('conway'):
            self.ui.active_art.stop_script('conway')
        else:
            self.ui.active_art.run_script_every('conway', 0.05)
    
    def BIND_arrow_up(self):
        if self.ui.popup.visible:
            self.ui.popup.move_popup_cursor(0, 1)
        elif self.ui.menu_bar.active_menu_name:
            self.ui.pulldown.keyboard_navigate(-1)
        else:
            self.app.cursor.move(0, 1)
    
    def BIND_arrow_down(self):
        if self.ui.popup.visible:
            self.ui.popup.move_popup_cursor(0, -1)
        elif self.ui.menu_bar.active_menu_name:
            self.ui.pulldown.keyboard_navigate(1)
        else:
            self.app.cursor.move(0, -1)
    
    def BIND_arrow_left(self):
        if self.ui.popup.visible:
            self.ui.popup.move_popup_cursor(-1, 0)
        # navigate menu bar
        elif self.ui.menu_bar.active_menu_name:
            self.ui.menu_bar.previous_menu()
        else:
            self.app.cursor.move(-1, 0)
    
    def BIND_arrow_right(self):
        if self.ui.popup.visible:
            self.ui.popup.move_popup_cursor(1, 0)
        elif self.ui.menu_bar.active_menu_name:
            self.ui.menu_bar.next_menu()
        else:
            self.app.cursor.move(1, 0)
    
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
    
    def BIND_open_art_menu(self):
        self.ui.menu_bar.open_menu_by_name('art')
    
    def BIND_open_frame_menu(self):
        self.ui.menu_bar.open_menu_by_name('frame')
    
    def BIND_open_layer_menu(self):
        self.ui.menu_bar.open_menu_by_name('layer')
    
    def BIND_open_char_color_menu(self):
        self.ui.menu_bar.open_menu_by_name('char_color')
    
    def BIND_open_help_menu(self):
        self.ui.menu_bar.open_menu_by_name('help')
    
    def BIND_new_art(self):
        self.ui.open_dialog(NewArtDialog)
    
    def BIND_open_art(self):
        self.ui.open_dialog(OpenArtDialog)
    
    def BIND_save_art_as(self):
        if not self.ui.active_art:
            return
        self.ui.open_dialog(SaveAsDialog)
    
    def BIND_close_art(self):
        if not self.ui.active_art:
            return
        if self.ui.active_art.unsaved_changes:
            self.ui.open_dialog(CloseUnsavedChangesDialog)
            return
        self.app.close_art(self.ui.active_art)
    
    def BIND_open_help_screen(self):
        self.ui.open_dialog(HelpScreenDialog)
    
    def BIND_open_readme(self):
        os.system('./readme.txt')
    
    def BIND_open_website(self):
        webbrowser.open('http://vectorpoem.com/playscii')
    
    def BIND_crop_to_selection(self):
        self.ui.crop_to_selection(self.ui.active_art)
    
    def BIND_resize_art(self):
        self.ui.open_dialog(ResizeArtDialog)
    
    def BIND_art_switch_to(self, art_filename):
        self.ui.set_active_art_by_filename(art_filename)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_add_frame(self):
        self.ui.open_dialog(AddFrameDialog)
    
    def BIND_duplicate_frame(self):
        self.ui.open_dialog(DuplicateFrameDialog)
    
    def BIND_change_frame_delay(self):
        self.ui.open_dialog(FrameDelayDialog)
    
    def BIND_delete_frame(self):
        self.ui.active_art.delete_frame_at(self.ui.active_frame)
    
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
    
    def BIND_delete_layer(self):
        self.ui.active_art.delete_layer(self.ui.active_layer)
        self.ui.menu_bar.refresh_active_menu()
    
    def BIND_choose_charset(self):
        self.ui.open_dialog(CharSetChooserDialog)
    
    def BIND_choose_palette(self):
        self.ui.open_dialog(PaletteChooserDialog)
