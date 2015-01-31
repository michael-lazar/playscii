import os.path
from random import randint
from PIL import Image

from texture import Texture

PALETTE_DIR = 'palettes/'
MAX_COLORS = 255

class Palette:
    
    def __init__(self, app, src_filename, log):
        self.init_success = False
        self.app = app
        self.name = os.path.basename(src_filename)
        self.name = os.path.splitext(self.name)[0]
        pal_filename = PALETTE_DIR + src_filename
        # auto-guess filename, but assume PNG
        if not os.path.exists(pal_filename):
            pal_filename += '.png'
            if not os.path.exists(pal_filename):
                self.app.log("Couldn't find palette image file %s" % pal_filename)
                return
        src_img = Image.open(pal_filename)
        src_img = src_img.convert('RGBA')
        width, height = src_img.size
        # scan image L->R T->B for unique colors, store em as tuples
        # color 0 is always fully transparent
        self.colors = [(0, 0, 0, 0)]
        # determine lightest and darkest colors in palette for defaults
        lightest = 0
        darkest = 255 * 3 + 1
        self.lightest_index, self.darkest_index = 0, 0
        for y in range(height):
            for x in range(width):
                color = src_img.getpixel((x, y))
                if not color in self.colors:
                    self.colors.append(color)
                    # is this lightest/darkest unique color so far? save index
                    luminosity = color[0]*0.21 + color[1]*0.72 + color[2]*0.07
                    if luminosity < darkest:
                        darkest = luminosity
                        self.darkest_index = len(self.colors) - 1
                    elif luminosity > lightest:
                        lightest = luminosity
                        self.lightest_index = len(self.colors) - 1
        # create new 1D image with unique colors
        img = Image.new('RGBA', (MAX_COLORS, 1), (0, 0, 0, 0))
        x = 0
        for color in self.colors:
            img.putpixel((x, 0), color)
            x += 1
        # debug: save out generated palette texture
        #img.save('palette.png')
        self.texture = Texture(img.tostring(), MAX_COLORS, 1)
        if log:
            self.app.log("loaded palette '%s' from %s:" % (self.name, pal_filename))
            self.app.log('  unique colors found: %s' % int(len(self.colors)-1))
            self.app.log('  darkest color index: %s' % self.darkest_index)
            self.app.log('  lightest color index: %s' % self.lightest_index)
        self.init_success = True
    
    def get_random_color_index(self):
        # exclude transparent first index
        return randint(1, len(self.colors))
