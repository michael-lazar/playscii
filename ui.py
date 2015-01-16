import numpy as np
from PIL import Image
from OpenGL import GL

from texture import Texture
from ui_element import FPSCounter

UI_ASSET_DIR = 'ui/'

class UI:
    
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
        # TODO: determine width and height of current window in chars
        self.elements = []
        test = FPSCounter(self)
        self.elements.append(test)
        # grain texture
        img = Image.open(UI_ASSET_DIR + self.grain_texture)
        img = img.convert('RGBA')
        width, height = img.size
        self.grain_texture = Texture(img.tostring(), width, height)
        self.grain_texture.set_wrap(GL.GL_REPEAT)
        self.grain_texture.set_filter(GL.GL_LINEAR, GL.GL_LINEAR_MIPMAP_LINEAR)
    
    def window_resized(self, new_width, new_height):
        # adjust for new aspect ratio
        self.projection_matrix[0][0] = new_height / new_width
    
    def update(self):
        for e in self.elements:
            e.update_art()
            e.art.update()
    
    def destroy(self):
        pass
    
    def render(self, elapsed_time):
        for e in self.elements:
            e.renderable.render(elapsed_time)
