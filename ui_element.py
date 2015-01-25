import numpy as np
from math import ceil

from art import Art
from renderable import TileRenderable
from renderable_line import LineRenderable

class UIElement:
    
    # size, in tiles
    width, height = 1, 1
    snap_top, snap_bottom, snap_left, snap_right = False, False, False, False
    x, y = 0, 0
    visible = True
    
    def __init__(self, ui):
        self.ui = ui
        self.art = UIArt(None, self.ui.app, self.ui.charset, self.ui.palette, self.width, self.height)
        self.renderable = UIRenderable(self.ui.app, self.art)
        self.renderable.ui = self.ui
        self.reset_art()
        self.reset_loc()
    
    def reset_art(self):
        """
        restores this element's Art to its initial state;
        runs on init and resize
        """
        pass
    
    def reset_loc(self):
        if self.snap_top:
            self.y = 1
        elif self.snap_bottom:
            self.y = self.art.quad_height * self.height - 1
        if self.snap_left:
            self.x = -1
        elif self.snap_right:
            self.x = 1 - (self.art.quad_width * self.width)
        self.renderable.x, self.renderable.y = self.x, self.y
    
    def update(self):
        "runs every frame"
        pass
    
    def render(self, elapsed_time):
        self.renderable.render(elapsed_time)


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
    
    width, height = 10, 2
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
        x = self.width - len(text)
        self.art.write_string(0, 0, x, 0, text, color)
        # display last tick time; frame_time includes delay, is useless
        text = '%.1f ms ' % self.ui.app.last_tick_time
        x = self.width - len(text)
        self.art.write_string(0, 0, x, 1, text, color)


class UIRenderableX(LineRenderable):
    
    "Red X used to denote transparent color in various places"
    color = (1, 0, 0, 1)
    
    def build_geo(self):
        self.vert_array = np.array([(0, 0), (1, 1), (1, 0), (0, 1)], dtype=np.float32)
        self.elem_array = np.array([0, 1, 2, 3], dtype=np.uint32)
        self.color_array = np.array([self.color * 4], dtype=np.float32)
