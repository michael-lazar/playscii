import numpy as np
from math import ceil

from art import Art
from renderable import TileRenderable
from renderable_line import LineRenderable

class UIElement:
    
    # size, in tiles
    tile_width, tile_height = 1, 1
    snap_top, snap_bottom, snap_left, snap_right = False, False, False, False
    x, y = 0, 0
    visible = True
    
    def __init__(self, ui):
        self.ui = ui
        self.art = UIArt(None, self.ui.app, self.ui.charset, self.ui.palette, self.tile_width, self.tile_height)
        self.renderable = UIRenderable(self.ui.app, self.art)
        self.renderable.ui = self.ui
        self.reset_art()
        self.reset_loc()
    
    def is_inside(self, x, y):
        "returns True if given point is inside this element's bounds"
        w = self.tile_width * self.art.quad_width
        h = self.tile_height * self.art.quad_height
        return self.x <= x <= self.x+w and self.y >= y >= self.y-h
    
    def reset_art(self):
        """
        restores this element's Art to its initial state;
        runs on init and resize
        """
        pass
    
    def hovered(self):
        if self.ui.logg:
            self.ui.app.log('%s hovered' % self.__class__)
    
    def unhovered(self):
        if self.ui.logg:
            self.ui.app.log('%s unhovered' % self.__class__)
    
    def clicked(self, button):
        if self.ui.logg:
            self.ui.app.log('%s clicked with button %s' % (self.__class__, button))
    
    def unclicked(self, button):
        if self.ui.logg:
            self.ui.app.log('%s unclicked with button %s' % (self.__class__, button))
    
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
    
    def update(self):
        "runs every frame"
        pass
    
    def render(self, elapsed_time):
        self.renderable.render(elapsed_time)
    
    def destroy(self):
        self.renderable.destroy()


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
    
    tile_width, tile_height = 10, 2
    snap_top = True
    snap_right = True
    
    def update(self):
        bg = 0
        self.art.clear_frame_layer(0, 0, bg)
        color = self.ui.palette.lightest_index
        # yellow or red if framerate dips
        if self.ui.app.fps < 30:
            color = 6
        if self.ui.app.fps < 10:
            color = 2
        text = '%.1f fps' % self.ui.app.fps
        x = self.tile_width - len(text)
        self.art.write_string(0, 0, x, 0, text, color)
        # display last tick time; frame_time includes delay, is useless
        text = '%.1f ms ' % self.ui.app.last_tick_time
        x = self.tile_width - len(text)
        self.art.write_string(0, 0, x, 1, text, color)
