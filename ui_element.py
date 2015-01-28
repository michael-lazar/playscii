import time
import numpy as np
from math import ceil

from art import Art
from renderable import TileRenderable
from renderable_line import LineRenderable
from ui_colors import UIColors

class UIElement:
    
    # size, in tiles
    tile_width, tile_height = 1, 1
    snap_top, snap_bottom, snap_left, snap_right = False, False, False, False
    x, y = 0, 0
    visible = True
    renderables = None
    buttons = []
    
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
        # write button captions
        for button in self.buttons:
            if button.caption != '':
                x, y = button.x, button.y + button.caption_y
                text = button.caption
                if button.caption_justify == TEXT_CENTER:
                    text = text.center(button.width)
                elif button.caption_justify == TEXT_RIGHT:
                    text = text.rjust(button.width)
                self.art.write_string(0, 0, x, y, text, button.normal_fg_color)
    
    def hovered(self):
        self.log_event('hovered')
    
    def unhovered(self):
        self.log_event('unhovered')
    
    def clicked(self, button):
        self.log_event('clicked', button)
        # tell any hovered buttons they've been clicked
        for b in self.hovered_buttons:
            if b.can_click:
                if b.callback:
                    b.callback()
                self.click_button(b)
    
    def unclicked(self, button):
        self.log_event('unclicked', button)
        for b in self.hovered_buttons:
            self.unclick_button(b)
    
    def log_event(self, event_type, mouse_button=None):
        #mousebutton = button or '[n/a]'
        if self.ui.logg:
            self.ui.app.log('%s %s with mouse button %s' % (self.__class__.__name__, event_type, mouse_button))
    
    def reset_loc(self):
        if self.snap_top:
            self.y = 1
        elif self.snap_bottom:
            self.y = self.art.quad_height * self.tile_height - 1
        if self.snap_left:
            self.x = -1
        elif self.snap_right:
            self.x = 1 - (self.art.quad_width * self.tile_width)
        self.renderable.x, self.renderable.y = self.x, self.y
    
    def get_button_state_colors(self, button, state):
        fg = getattr(button, '%s_fg_color' % state)
        bg = getattr(button, '%s_bg_color' % state)
        return fg, bg
    
    def set_button_state_colors(self, button, state):
        fg, bg = self.get_button_state_colors(button, state)
        for y in range(button.height):
            for x in range(button.width):
                self.art.set_tile_at(0, 0, button.x + x, button.y + y, None, fg, bg)
    
    def hover_button(self, button):
        self.log_button_event(button, 'hovered')
        self.set_button_state_colors(button, 'hovered')
    
    def unhover_button(self, button):
        self.log_button_event(button, 'unhovered')
        self.set_button_state_colors(button, 'normal')
    
    def click_button(self, button):
        self.log_button_event(button, 'clicked')
        self.set_button_state_colors(button, 'clicked')
    
    def unclick_button(self, button):
        self.log_button_event(button, 'unclicked')
        if button in self.hovered_buttons:
            self.hover_button(button)
        else:
            self.unhover_button(button)
    
    def log_button_event(self, button, event_type):
        "common code for button event logging"
        if self.ui.logg:
            self.ui.app.log("%s's %s %s" % (self.__class__.__name__, button.__class__.__name__, event_type))
    
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
            if b.can_hover and self.is_inside_button(mx, my, b):
                self.hovered_buttons.append(b)
                if not b in was_hovering:
                    self.hover_button(b)
        for b in was_hovering:
            if not b in self.hovered_buttons:
                self.unhover_button(b)
        # tiles might have just changed
        self.art.update()
    
    def render(self, elapsed_time):
        self.renderable.render(elapsed_time)
    
    def destroy(self):
        for r in self.renderables:
            r.destroy()


TEXT_LEFT = 0
TEXT_CENTER = 1
TEXT_RIGHT = 2

class UIButton:
    "clickable button that does something in a UIElement"
    # x/y/width/height given in tile scale
    x, y = 0, 0
    width, height = 1, 1
    caption = 'TEST'
    caption_justify = TEXT_LEFT
    caption_y = 0
    callback = None
    normal_fg_color = UIColors.black
    normal_bg_color = UIColors.lightgrey
    hovered_fg_color = UIColors.black
    hovered_bg_color = UIColors.white
    clicked_fg_color = UIColors.white
    clicked_bg_color = UIColors.black
    dimmed_fg_color = UIColors.black
    dimmed_bg_color = UIColors.medgrey
    # state variables
    can_hover = True
    can_click = True


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
    
    tile_width, tile_height = 12, 2
    snap_top = True
    snap_right = True
    
    def update(self):
        bg = 0
        self.art.clear_frame_layer(0, 0, bg)
        color = self.ui.colors.white
        # yellow or red if framerate dips
        if self.ui.app.fps < 30:
            color = 6
        if self.ui.app.fps < 10:
            color = 2
        text = '%.1f fps' % self.ui.app.fps
        x = self.tile_width - 1
        self.art.write_string(0, 0, x, 0, text, color, None, True)
        # display last tick time; frame_time includes delay, is useless
        text = '%.1f ms ' % self.ui.app.last_tick_time
        self.art.write_string(0, 0, x, 1, text, color, None, True)
