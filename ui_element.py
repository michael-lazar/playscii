import time
import numpy as np
from math import ceil

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
    renderables = None
    can_hover = True
    buttons = []
    # renders in "game mode"
    game_mode_visible = False
    
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
        for button in self.buttons:
            if button.visible:
                button.draw()
    
    def hovered(self):
        self.log_event('hovered')
    
    def unhovered(self):
        self.log_event('unhovered')
    
    def clicked(self, button):
        self.log_event('clicked', button)
        # return if a button did something
        handled = False
        # tell any hovered buttons they've been clicked
        for b in self.hovered_buttons:
            if b.can_click:
                b.click()
                if b.callback:
                    if b.cb_arg:
                        b.callback(b.cb_arg)
                    else:
                        b.callback()
                    handled = True
        return handled
    
    def unclicked(self, button):
        self.log_event('unclicked', button)
        for b in self.hovered_buttons:
            b.unclick()
    
    def log_event(self, event_type, mouse_button=None):
        mouse_button = mouse_button or '[n/a]'
        if self.ui.logg:
            self.ui.app.log('UIElement: %s %s with mouse button %s' % (self.__class__.__name__, event_type, mouse_button))
    
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


class MessageLineUI(UIElement):
    
    "when console outputs something new, show last line here before fading out"
    
    tile_y = 2
    snap_left = True
    # just info, don't bother with hover, click etc
    can_hover = False
    default_hold_time = 1
    fade_rate = 0.025
    game_mode_visible = True
    
    def __init__(self, ui):
        UIElement.__init__(self, ui)
        # line we're currently displaying (even after fading out)
        self.line = ''
        self.last_post = self.ui.app.elapsed_time
        self.hold_time = self.default_hold_time
        self.alpha = 1
    
    def reset_art(self):
        self.tile_width = ceil(self.ui.width_tiles)
        self.art.resize(self.tile_width, self.tile_height)
        self.art.clear_frame_layer(0, 0, 0, self.ui.colors.white)
        # one line from top
        self.y = 1- self.art.quad_height
        UIElement.reset_loc(self)
    
    def post_line(self, new_line, hold_time=None):
        self.hold_time = hold_time or self.default_hold_time
        "write a line to this element (without polluting console log with it)"
        self.line = new_line
        self.art.clear_frame_layer(0, 0, 0, self.ui.colors.white)
        self.art.write_string(0, 0, 1, 0, self.line)
        self.alpha = 1
        self.last_post = self.ui.app.elapsed_time
    
    def update(self):
        if self.ui.app.elapsed_time > self.last_post + (self.hold_time * 1000):
            if self.alpha >= self.fade_rate:
                self.alpha -= self.fade_rate
            if self.alpha <= self.fade_rate:
                self.alpha = 0
        self.renderable.alpha = self.alpha
    
    def render(self):
        # TODO: draw if popup is visible but not obscuring message line?
        if not self.ui.popup.visible and not self.ui.console.visible:
            UIElement.render(self)
