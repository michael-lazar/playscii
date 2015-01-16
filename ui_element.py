from art import Art
from renderable import Renderable

class UIElement:
    
    width, height = 1, 1
    
    def __init__(self, ui):
        self.ui = ui
        self.art = UIArt(None, self.ui.app, self.ui.charset, self.ui.palette, self.width, self.height)
        self.renderable = UIRenderable(self.ui.app, self.art)
        self.renderable.ui = self.ui
    
    def update(self):
        pass


class UIArt(Art):
    quad_width,quad_height = 0.1, 0.1


class UIRenderable(Renderable):
    grain_strength = 0.2
    def get_projection_matrix(self):
        return self.ui.projection_matrix
    
    def get_view_matrix(self):
        return self.ui.view_matrix


class FPSCounterUI(UIElement):
    width, height = 9, 2
    def update(self):
        text = '%.1ffps' % self.ui.app.fps
        x = self.width - len(text)
        bg = 2
        self.art.clear_frame_layer(0, 0, bg)
        color = self.ui.palette.lightest_index
        self.art.write_string(0, 0, x, 0, text, color)
        text = '%.1fms ' % self.ui.app.frame_time
        x = self.width - len(text)
        self.art.write_string(0, 0, x, 1, text, color)
