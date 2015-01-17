import numpy as np
from PIL import Image
from OpenGL import GL

from texture import Texture
from ui_element import UIArt, StatusBarUI, FPSCounterUI

UI_ASSET_DIR = 'ui/'

class UI:
    
    # user-configured UI scale factor
    scale = 1.0
    charset_name = 'ui'
    palette_name = 'c64'
    # low-contrast background texture that distinguishes UI from flat color
    grain_texture = 'bgnoise_alpha.png'
    
    def __init__(self, app):
        self.app = app
        aspect = self.app.window_height / self.app.window_width
        self.projection_matrix = np.array([[aspect, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
        self.view_matrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
        self.charset = self.app.load_charset(self.charset_name)
        self.palette = self.app.load_palette(self.palette_name)
        # create elements
        self.elements = []
        # set geo sizes, force scale update
        self.set_scale(self.scale, True)
        fps_counter = FPSCounterUI(self)
        status_bar = StatusBarUI(self)
        self.elements.append(fps_counter)
        self.elements.append(status_bar)
        # grain texture
        img = Image.open(UI_ASSET_DIR + self.grain_texture)
        img = img.convert('RGBA')
        width, height = img.size
        self.grain_texture = Texture(img.tostring(), width, height)
        self.grain_texture.set_wrap(GL.GL_REPEAT)
        self.grain_texture.set_filter(GL.GL_LINEAR, GL.GL_LINEAR_MIPMAP_LINEAR)
    
    def set_scale(self, new_scale, force_update=False):
        new_scale = max(1, new_scale)
        if new_scale == self.scale and not force_update:
            return
        self.scale = max(1, new_scale)
        # update UI renderable geo sizes for new scale
        # determine width and height of current window in chars
        # use floats, window might be a fractional # of chars wide/tall
        aspect = self.app.window_height / self.app.window_width
        self.width_tiles = self.app.window_width / self.charset.char_width
        self.height_tiles = self.app.window_height / self.charset.char_height
        UIArt.quad_width = (2 / self.width_tiles) * self.scale * aspect
        UIArt.quad_height = (2 / self.height_tiles) * self.scale * aspect
        # tell elements to refresh
        for e in self.elements:
            e.reset_loc()
            e.art.geo_changed = True
    
    def window_resized(self):
        # adjust for new aspect ratio
        self.projection_matrix[0][0] = self.app.window_height / self.app.window_width
        # tell all elements to resize for new window
        for e in self.elements:
            e.reset_loc()
    
    def update(self):
        for e in self.elements:
            e.update()
            # art update: tell renderables to refresh buffers
            e.art.update()
    
    def clicked(self, button):
        pass
    
    def unclicked(self, button):
        pass
    
    def destroy(self):
        for e in self.elements:
            e.renderable.destroy()
        self.grain_texture.destroy()
    
    def render(self, elapsed_time):
        for e in self.elements:
            e.renderable.render(elapsed_time)
