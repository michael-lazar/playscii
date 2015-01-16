from art import Art
from renderable import Renderable

class UIElement:
    
    # size, in tiles
    width, height = 1, 1
    snap_top, snap_bottom, snap_left, snap_right = False, False, False, False
    x, y = 0, 0
    
    def __init__(self, ui):
        self.ui = ui
        self.art = UIArt(None, self.ui.app, self.ui.charset, self.ui.palette, self.width, self.height)
        self.renderable = UIRenderable(self.ui.app, self.art)
        self.renderable.ui = self.ui
        self.reset_loc()
    
    def reset_loc(self):
        inv_aspect = self.ui.app.window_width / self.ui.app.window_height
        if self.snap_top:
            self.y = 1
        elif self.snap_bottom:
            self.y = self.art.quad_height * self.height - 1
        if self.snap_left:
            self.x = -inv_aspect
        elif self.snap_right:
            self.x = inv_aspect - (self.art.quad_width * self.width)
        self.renderable.x, self.renderable.y = self.x, self.y
    
    def update(self):
        pass


class UIArt(Art):
    recalc_quad_height = False


class UIRenderable(Renderable):
    
    grain_strength = 0.2
    
    def get_projection_matrix(self):
        return self.ui.projection_matrix
    
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
        text = '%.1f ms ' % self.ui.app.frame_time
        x = self.width - len(text)
        self.art.write_string(0, 0, x, 1, text, color)
