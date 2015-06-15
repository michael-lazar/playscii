import os.path, math
from random import randint
from PIL import Image

from texture import Texture

PALETTE_DIR = 'palettes/'
MAX_COLORS = 255

class Palette:
    
    def __init__(self, app, src_filename, log):
        self.init_success = False
        self.app = app
        self.filename = src_filename
        # auto-guess filename, but assume PNG
        if not os.path.exists(self.filename):
            self.filename += '.png'
        if self.app.gw.game_dir:
            game_palette_filename = self.app.gw.get_game_dir() + PALETTE_DIR + self.filename
            if os.path.exists(game_palette_filename):
                self.filename = game_palette_filename
        if not os.path.exists(self.filename) or os.path.isdir(self.filename):
            self.filename = PALETTE_DIR + self.filename
        if not os.path.exists(self.filename):
            self.app.log("Couldn't find palette image file %s" % self.filename)
            return
        self.name = os.path.basename(self.filename)
        self.name = os.path.splitext(self.name)[0]
        src_img = Image.open(self.filename)
        src_img = src_img.convert('RGBA')
        width, height = src_img.size
        # store texture for chooser preview etc
        self.src_texture = Texture(src_img.tostring(), width, height)
        # scan image L->R T->B for unique colors, store em as tuples
        # color 0 is always fully transparent
        self.colors = [(0, 0, 0, 0)]
        # determine lightest and darkest colors in palette for defaults
        lightest = 0
        darkest = 255 * 3 + 1
        self.lightest_index, self.darkest_index = 0, 0
        for y in range(height):
            for x in range(width):
                # bail if we've now read max colors
                if len(self.colors) >= MAX_COLORS:
                    break
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
        if log and not self.app.game_mode:
            self.app.log("loaded palette '%s' from %s:" % (self.name, self.filename))
            self.app.log('  unique colors found: %s' % int(len(self.colors)-1))
            self.app.log('  darkest color index: %s' % self.darkest_index)
            self.app.log('  lightest color index: %s' % self.lightest_index)
        self.init_success = True
    
    def export_as_image(self):
        #width = math.floor(math.sqrt(len(self.colors) - 1))
        width = min(16, len(self.colors) - 1)
        #width = min(math.sqrt(len(self.colors)), math.sqrt(MAX_COLORS + 1))
        height = math.floor((len(self.colors) - 1) / width)
        block_size = 8
        # new PIL image, blank (0 alpha) pixels
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        # set each pixel from color list (minus first, transparent color)
        color_index = 1
        for y in range(height):
            for x in range(width):
                if color_index > len(self.colors) - 1:
                    break
                img.putpixel((x, y), self.colors[color_index])
                color_index += 1
        # scale up
        img = img.resize((width * block_size, height * block_size),
                         resample=Image.NEAREST)
        # write to file
        img_filename = PALETTE_DIR + self.name + '.png'
        img.save(img_filename)
    
    def all_colors_opaque(self):
        "returns True if we have any non-opaque (<1 alpha) colors"
        for color in self.colors[1:]:
            if color[3] < 255:
                return False
        return True
    
    def get_palettized_image(self, src_img):
        "returns a copy of source image quantized to this palette"
        pal_img = Image.new('P', (1, 1))
        # source must be in RGB (no alpha) format
        out_img = src_img.convert('RGB')
        # Image.putpalette needs a flat tuple :/
        colors = []
        for i,color in enumerate(self.colors):
            # ignore alpha for palettized image output
            for channel in color[:-1]:
                colors.append(channel)
        # PIL will fill out <256 color palettes with bogus values :/
        while len(colors) < 256 * 3:
            for i in range(3):
                colors.append(0)
        pal_img.putpalette(tuple(colors))
        return out_img.quantize(palette=pal_img)
    
    def are_colors_similar(self, color_index_a, palette_b, color_index_b,
                           tolerance=50):
        """
        returns True if color index A is similar to color index B from
        another palette.
        """
        color_a = self.colors[color_index_a]
        color_b = palette_b.colors[color_index_b % len(palette_b.colors)]
        r_diff = abs(color_a[0] - color_b[0])
        g_diff = abs(color_a[1] - color_b[1])
        b_diff = abs(color_a[2] - color_b[2])
        return (r_diff + g_diff + b_diff) <= tolerance
    
    def get_random_color_index(self):
        # exclude transparent first index
        return randint(1, len(self.colors))


class PaletteFromFile(Palette):
    
    def __init__(self, app, src_filename, palette_filename, colors=256):
        self.init_success = False
        # dither source image, re-save it, use that as the source for a palette
        if not os.path.exists(src_filename):
            app.log("Couldn't find palette source image file %s" % src_filename)
            return
        src_img = Image.open(src_filename)
        # method:
        src_img = src_img.convert('P', None, Image.FLOYDSTEINBERG, Image.ADAPTIVE, colors)
        src_img = src_img.convert('RGBA')
        # write converted source image w/ same name as final palette image
        if not palette_filename.lower().endswith('.png'):
            palette_filename += '.png'
        if not palette_filename.startswith(PALETTE_DIR):
            palette_filename = '%s%s' % (PALETTE_DIR, palette_filename)
        src_img.save(palette_filename)
        # create the actual palette and export it as an image
        Palette.__init__(self, app, palette_filename, True)
        self.export_as_image()
