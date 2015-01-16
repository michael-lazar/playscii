from random import randint

from art import Art
from renderable import Renderable

class UIElement:
    
    width, height = 1, 1
    
    def __init__(self, ui):
        self.ui = ui
        self.art = UIArt(None, self.ui.app, self.ui.charset, self.ui.palette, self.width, self.height)
        self.renderable = UIRenderable(self.ui.app, self.art)
        self.renderable.ui = self.ui
    
    def update_art(self):
        pass


class UIArt(Art):
    quad_width,quad_height = 0.1, 0.1


class UIRenderable(Renderable):
    grain_strength = 0.2
    def get_projection_matrix(self):
        return self.ui.projection_matrix
    
    def get_view_matrix(self):
        return self.ui.view_matrix


class FPSCounter(UIElement):
    width, height = 10, 2
    def update_art(self):
        color = 0
        self.art.clear_frame_layer(0, 0, color)
        color = self.ui.palette.lightest_index
        self.art.write_string(0, 0, 0, 0, 'Testing 1!', color)
        color = randint(1, len(self.ui.palette.colors))
        self.art.write_string(0, 0, 0, 1, 'Testing 2!', color)
