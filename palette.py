import os.path
from PIL import Image

from texture import Texture

PALETTE_DIR = 'palettes/'
MAX_COLORS = 255

class Palette:
    
    def __init__(self, src_filename):
        pal_filename = PALETTE_DIR + src_filename
        # auto-guess filename, but assume PNG
        if not os.path.exists(pal_filename):
            pal_filename += '.png'
            if not os.path.exists(pal_filename):
                print("Couldn't find palette image file" + pal_filename)
        src_img = Image.open(pal_filename)
        src_img = src_img.convert('RGBA')
        width, height = src_img.size
        # scan image L->R T->B for unique colors
        # color 0 is always fully transparent
        self.colors = [(0, 0, 0, 0)]
        for y in range(height):
            for x in range(width):
                color = src_img.getpixel((x, y))
                if not color in self.colors:
                    self.colors.append(color)
        #print('%s unique colors in source palette: %s' % (len(self.colors)-1, self.colors))
        # create new 1D image with unique colors
        img = Image.new('RGBA', (MAX_COLORS, 1), (0, 0, 0, 0))
        x = 0
        for color in self.colors:
            img.putpixel((x, 0), color)
            x += 1
        self.texture = Texture(img.tostring(), width, height)
