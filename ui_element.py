import time
import numpy as np
from math import ceil

import vector
from art import Art
from renderable import TileRenderable
from renderable_line import LineRenderable
from ui_button import UIButton

class UIElement:
    
    # size, in tiles
    tile_width, tile_height = 1, 1
    snap_top, snap_bottom, snap_left, snap_right = False, False, False, False
    # location in tile coords; snap_* trumps these
    tile_x, tile_y = 0, 0
    # location in screen (GL) coords
    x, y = 0, 0
    visible = True
    # UI calls our update() even when we're invisible
    update_when_invisible = False
    # cheapo drop shadow effect, draws renderable dark at a small offset
    drop_shadow = False
    renderables = None
    can_hover = True
    # always return True for clicked/unclicked, "consuming" the input
    always_consume_input = False
    buttons = []
    # if True, use shared keyboard navigation controls
    support_keyboard_navigation = False
    support_scrolling = False
    keyboard_nav_left_right = False
    # renders in "game mode"
    game_mode_visible = False
    all_modes_visible = False
    keyboard_nav_offset = 0
    
    def __init__(self, ui):
        self.ui = ui
        self.hovered_buttons = []
        # generate a unique name
        art_name = '%s_%s' % (int(time.time()), self.__class__.__name__)
        self.art = UIArt(art_name, self.ui.app, self.ui.charset, self.ui.palette, self.tile_width, self.tile_height)
        self.renderable = UIRenderable(self.ui.app, self.art)
        self.renderable.ui = self.ui
        # some elements add their own renderables before calling this
        # constructor, make sure we're not erasing any
        if not self.renderables:
            self.renderables = []
        self.renderables.append(self.renderable)
        self.reset_art()
        self.reset_loc()
        if self.support_keyboard_navigation:
            self.keyboard_nav_index = 0
    
    def is_inside(self, x, y):
        "returns True if given point is inside this element's bounds"
        w = self.tile_width * self.art.quad_width
        h = self.tile_height * self.art.quad_height
        return self.x <= x <= self.x+w and self.y >= y >= self.y-h
    
    def is_inside_button(self, x, y, button):
        "returns True if given point is inside the given button's bounds"
        aqw, aqh = self.art.quad_width, self.art.quad_height
        # put negative values in range
        bx, by = (button.x % self.art.width) * aqw, (button.y % self.art.height) * aqh
        bw, bh = button.width * aqw, button.height * aqh
        bxmin, bymin = self.x + bx, self.y - by
        bxmax, bymax = bxmin + bw, bymin - bh
        return bxmin <= x <= bxmax and bymin >= y >= bymax
    
    def reset_art(self):
        """
        runs on init and resize, restores state.
        """
        self.draw_buttons()
    
    def draw_buttons(self):
        for button in self.buttons:
            if button.visible:
                button.draw()
    
    def hovered(self):
        self.log_event('hovered')
    
    def unhovered(self):
        self.log_event('unhovered')
    
    def wheel_moved(self, wheel_y):
        handled = False
        return handled
    
    def clicked(self, mouse_button):
        self.log_event('clicked', mouse_button)
        # return if a button did something
        handled = False
        # tell any hovered buttons they've been clicked
        for b in self.hovered_buttons:
            if b.can_click:
                b.click()
                if b.callback:
                    # button callback might need extra data (cb_arg)
                    if b.cb_arg is not None:
                        # button might want to know which mouse button clicked
                        if b.pass_mouse_button:
                            b.callback(mouse_button, b.cb_arg)
                        else:
                            b.callback(b.cb_arg)
                    else:
                        if b.pass_mouse_button:
                            b.callback(mouse_button)
                        else:
                            b.callback()
                handled = True
        if self.always_consume_input:
            return True
        return handled
    
    def unclicked(self, mouse_button):
        self.log_event('unclicked', mouse_button)
        handled = False
        for b in self.hovered_buttons:
            b.unclick()
            handled = True
        if self.always_consume_input:
            return True
        return handled
    
    def log_event(self, event_type, mouse_button=None):
        mouse_button = mouse_button or '[n/a]'
        if self.ui.logg:
            self.ui.app.log('UIElement: %s %s with mouse button %s' % (self.__class__.__name__, event_type, mouse_button))
    
    def is_visible(self):
        if self.all_modes_visible:
            return self.visible
        elif not self.ui.app.game_mode and self.game_mode_visible:
            return False
        elif self.ui.app.game_mode and not self.game_mode_visible:
            return False
        return self.visible
    
    def reset_loc(self):
        if self.snap_top:
            self.y = 1
        elif self.snap_bottom:
            self.y = self.art.quad_height * self.tile_height - 1
        elif self.tile_y:
            self.y = 1 - (self.tile_y * self.art.quad_height)
        if self.snap_left:
            self.x = -1
        elif self.snap_right:
            self.x = 1 - (self.art.quad_width * self.tile_width)
        elif self.tile_x:
            self.x = -1 + (self.tile_x * self.art.quad_width)
        self.renderable.x, self.renderable.y = self.x, self.y
    
    def keyboard_navigate(self, move_x, move_y):
        if not self.support_keyboard_navigation:
            return
        if self.keyboard_nav_left_right:
            if move_x < 0:
                self.ui.menu_bar.previous_menu()
                return
            elif move_x > 0:
                self.ui.menu_bar.next_menu()
                return
        old_idx = self.keyboard_nav_index
        new_idx = self.keyboard_nav_index + move_y
        self.keyboard_nav_index += move_y
        if not self.support_scrolling:
            # if button list starts at >0 Y, use an offset
            self.keyboard_nav_index %= len(self.buttons) + self.keyboard_nav_offset
            tries = 0
            # recognize two different kinds of inactive items: empty caption and dim state
            while tries < len(self.buttons) and (self.buttons[self.keyboard_nav_index].caption == '' or self.buttons[self.keyboard_nav_index].state == 'dimmed'):
                # move_y might be zero, give it a direction to avoid infinite loop
                # if menu item 0 is dimmed
                self.keyboard_nav_index += move_y or 1
                self.keyboard_nav_index %= len(self.buttons) + self.keyboard_nav_offset
                tries += 1
            if tries == len(self.buttons):
                return
        self.post_keyboard_navigate()
        self.update_keyboard_hover()
    
    def update_keyboard_hover(self):
        if not self.support_keyboard_navigation:
            return
        for i,button in enumerate(self.buttons):
            # don't higlhight if this panel doesn't have focus
            if self.keyboard_nav_index == i and self is self.ui.keyboard_focus_element:
                button.set_state('hovered')
            elif button.state != 'dimmed':
                button.set_state('normal')
    
    def keyboard_select_item(self):
        if not self.support_keyboard_navigation:
            return
        button = self.buttons[self.keyboard_nav_index]
        # don't allow selecting dimmed buttons
        if button.state == 'dimmed':
            return
        # check for None; cb_arg could be 0
        if button.cb_arg is not None:
            button.callback(button.cb_arg)
        else:
            button.callback()
        return button
    
    def post_keyboard_navigate(self):
        # subclasses can put stuff here to check scrolling etc
        pass
    
    def update(self):
        "runs every frame, checks button states"
        # this is very similar to UI.update, implying an alternative structure
        # in which UIElements can contain other UIElements.  i've seen this get
        # really confusing on past projects though, so let's try a flatter
        # architecture - UI w/ UIelements, UIElements w/ UIButtons - for now.
        mx, my = self.ui.get_screen_coords(self.ui.app.mouse_x, self.ui.app.mouse_y)
        was_hovering = self.hovered_buttons[:]
        self.hovered_buttons = []
        for b in self.buttons:
            # element.clicked might have been set it non-hoverable, acknowledge
            # its hoveredness here so it can unhover correctly
            if b.visible and (b.can_hover or b.state == 'clicked') and self.is_inside_button(mx, my, b):
                self.hovered_buttons.append(b)
                if not b in was_hovering:
                    b.hover()
        for b in was_hovering:
            if not b in self.hovered_buttons:
                b.unhover()
        # tiles might have just changed
        self.art.update()
    
    def render(self):
        # ("is visible" check happens in UI.render, calls our is_visible)
        # render drop shadow first
        if self.drop_shadow:
            # offset in X and Y, render then restore position
            orig_x, orig_y = self.renderable.x, self.renderable.y
            self.renderable.x += UIArt.quad_width / 10
            self.renderable.y -= UIArt.quad_height / 10
            self.renderable.render(brightness=0.1)
            self.renderable.x, self.renderable.y = orig_x, orig_y
        self.renderable.render()
    
    def destroy(self):
        for r in self.renderables:
            r.destroy()


class UIArt(Art):
    recalc_quad_height = False
    log_creation = False


class UIRenderable(TileRenderable):
    
    grain_strength = 0.2
    
    def get_projection_matrix(self):
        # don't use projection matrix, ie identity[0][0]=aspect;
        # rather do all aspect correction in UI.set_scale when determining quad size
        return self.ui.view_matrix
    
    def get_view_matrix(self):
        return self.ui.view_matrix


class FPSCounterUI(UIElement):
    
    tile_y = 1
    tile_width, tile_height = 12, 2
    snap_right = True
    game_mode_visible = True
    all_modes_visible = True
    visible = False
    
    def update(self):
        bg = 0
        self.art.clear_frame_layer(0, 0, bg)
        color = self.ui.colors.white
        # yellow or red if framerate dips
        if self.ui.app.fps < 30:
            color = self.ui.colors.yellow
        if self.ui.app.fps < 10:
            color = self.ui.colors.red
        text = '%.1f fps' % self.ui.app.fps
        x = self.tile_width - 1
        self.art.write_string(0, 0, x, 0, text, color, None, True)
        # display last tick time; frame_time includes delay, is useless
        text = '%.1f ms ' % self.ui.app.frame_time
        self.art.write_string(0, 0, x, 1, text, color, None, True)
    
    def render(self):
        # always show FPS if low
        if self.visible or self.ui.app.fps < 30:
            self.renderable.render()


class MessageLineUI(UIElement):
    
    "when console outputs something new, show last line here before fading out"
    
    tile_y = 2
    snap_left = True
    # just info, don't bother with hover, click etc
    can_hover = False
    default_hold_time = 1
    fade_rate = 0.025
    game_mode_visible = True
    all_modes_visible = True
    drop_shadow = True
    
    def __init__(self, ui):
        UIElement.__init__(self, ui)
        # line we're currently displaying (even after fading out)
        self.line = ''
        self.last_post = self.ui.app.get_elapsed_time()
        self.hold_time = self.default_hold_time
        self.alpha = 1
    
    def reset_art(self):
        self.tile_width = ceil(self.ui.width_tiles)
        self.art.resize(self.tile_width, self.tile_height)
        self.art.clear_frame_layer(0, 0, 0, self.ui.colors.white)
        UIElement.reset_loc(self)
    
    def post_line(self, new_line, hold_time=None, error=False):
        "write a line to this element (ie so as not to spam console log)"
        self.hold_time = hold_time or self.default_hold_time
        # use a different color if it's an error
        color = self.ui.error_color_index if error else self.ui.colors.white
        start_x = 1
        # trim to screen width
        self.line = str(new_line)[:self.tile_width-start_x-1]
        self.art.clear_frame_layer(0, 0, 0, color)
        self.art.write_string(0, 0, start_x, 0, self.line)
        self.alpha = 1
        self.last_post = self.ui.app.get_elapsed_time()
    
    def update(self):
        if self.ui.app.get_elapsed_time() > self.last_post + (self.hold_time * 1000):
            if self.alpha >= self.fade_rate:
                self.alpha -= self.fade_rate
            if self.alpha <= self.fade_rate:
                self.alpha = 0
        self.renderable.alpha = self.alpha
    
    def render(self):
        # TODO: draw if popup is visible but not obscuring message line?
        if not self.ui.popup in self.ui.hovered_elements and not self.ui.console.visible:
            UIElement.render(self)


class DebugTextUI(UIElement):
    
    "simple UI element for posting debug text"
    
    tile_x, tile_y = 1, 4
    tile_height = 20
    clear_lines_after_render = True
    game_mode_visible = True
    visible = False
    
    def __init__(self, ui):
        UIElement.__init__(self, ui)
        self.lines = []
    
    def reset_art(self):
        self.tile_width = ceil(self.ui.width_tiles)
        self.art.resize(self.tile_width, self.tile_height)
        self.art.clear_frame_layer(0, 0, 0, self.ui.colors.white)
        UIElement.reset_loc(self)
    
    def post_lines(self, lines):
        if type(lines) is list:
            self.lines += lines
        else:
            self.lines += [lines]
    
    def update(self):
        self.art.clear_frame_layer(0, 0, 0, self.ui.colors.white)
        for y,line in enumerate(self.lines):
            self.art.write_string(0, 0, 0, y, line)
    
    def render(self):
        UIElement.render(self)
        if self.clear_lines_after_render:
            self.lines = []
            #self.art.clear_frame_layer(0, 0, 0, self.ui.colors.white)


class GameLabel(UIElement):
    tile_width, tile_height = 50, 1
    game_mode_visible = True
    drop_shadow = True
    update_when_invisible = True


class GameSelectionLabel(GameLabel):
    
    multi_select_label = '[%s selected]'
    
    def update(self):
        self.visible = False
        if self.ui.pulldown.visible or not self.ui.is_game_edit_ui_visible():
            return
        if len(self.ui.app.gw.selected_objects) == 0:
            return
        self.visible = True
        if len(self.ui.app.gw.selected_objects) == 1:
            obj = self.ui.app.gw.selected_objects[0]
            text = obj.name[:self.tile_width-1]
            x, y, z = obj.x, obj.y, obj.z
        else:
            # draw "[N selected]" at avg of selected object locations
            text = self.multi_select_label % len(self.ui.app.gw.selected_objects)
            x, y, z = 0, 0, 0
            for obj in self.ui.app.gw.selected_objects:
                x += obj.x
                y += obj.y
                z += obj.z
            x /= len(self.ui.app.gw.selected_objects)
            y /= len(self.ui.app.gw.selected_objects)
            z /= len(self.ui.app.gw.selected_objects)
        self.art.clear_line(0, 0, 0, self.ui.colors.white, -1)
        self.art.write_string(0, 0, 0, 0, text)
        self.x, self.y = vector.world_to_screen_normalized(self.ui.app, x, y, z)
        self.reset_loc()

class GameHoverLabel(GameLabel):
    
    alpha = 0.75
    
    def update(self):
        self.visible = False
        if self.ui.pulldown.visible or not self.ui.is_game_edit_ui_visible():
            return
        if not self.ui.app.gw.hovered_focus_object:
            return
        self.visible = True
        obj = self.ui.app.gw.hovered_focus_object
        text = obj.name[:self.tile_width-1]
        x, y, z = obj.x, obj.y, obj.z
        self.art.clear_line(0, 0, 0, self.ui.colors.white, -1)
        self.art.write_string(0, 0, 0, 0, text)
        self.x, self.y = vector.world_to_screen_normalized(self.ui.app, x, y, z)
        self.reset_loc()
        self.renderable.alpha = self.alpha
