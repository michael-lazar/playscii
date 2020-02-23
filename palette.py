import os.path, math, time
from random import randint
from PIL import Image

from texture import Texture
from lab_color import rgb_to_lab, lab_color_diff

PALETTE_DIR = 'palettes/'
PALETTE_EXTENSIONS = ['png', 'gif', 'bmp']
MAX_COLORS = 1024

class PaletteLord:
    
    # time in ms between checks for hot reload
    hot_reload_check_interval = 2 * 1000
    
    def __init__(self, app):
        self.app = app
        self.last_check = 0
    
    def check_hot_reload(self):
        if self.app.get_elapsed_time() - self.last_check < self.hot_reload_check_interval:
            return
        self.last_check = self.app.get_elapsed_time()
        changed = None
        for palette in self.app.palettes:
            if palette.has_updated():
                changed = palette.filename
                try:
                    palette.load_image()
                    self.app.log('PaletteLord: success reloading %s' % palette.filename)
                except:
                    self.app.log('PaletteLord: failed reloading %s' % palette.filename, True)


class Palette:
    
    def __init__(self, app, src_filename, log):
        self.init_success = False
        self.app = app
        self.filename = self.app.find_filename_path(src_filename, PALETTE_DIR,
                                                    PALETTE_EXTENSIONS)
        if self.filename is None:
            self.app.log("Couldn't find palette image %s" % src_filename)
            return
        self.last_image_change = os.path.getmtime(self.filename)
        self.name = os.path.basename(self.filename)
        self.name = os.path.splitext(self.name)[0]
        self.load_image()
        self.base_filename = os.path.splitext(os.path.basename(self.filename))[0]
        if log and not self.app.game_mode:
            self.app.log("loaded palette '%s' from %s:" % (self.name, self.filename))
            self.app.log('  unique colors found: %s' % int(len(self.colors)-1))
            self.app.log('  darkest color index: %s' % self.darkest_index)
            self.app.log('  lightest color index: %s' % self.lightest_index)
        self.init_success = True
    
    def load_image(self):
        "loads palette data from the given bitmap image"
        src_img = Image.open(self.filename)
        src_img = src_img.convert('RGBA')
        width, height = src_img.size
        # store texture for chooser preview etc
        self.src_texture = Texture(src_img.tobytes(), width, height)
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
        self.texture = Texture(img.tobytes(), MAX_COLORS, 1)
    
    def has_updated(self):
        "return True if source image file has changed since last check"
        changed = os.path.getmtime(self.filename) > self.last_image_change
        if changed:
            self.last_image_change = time.time()
        return changed
    
    def generate_image(self):
        width = min(16, len(self.colors) - 1)
        height = math.floor((len(self.colors) - 1) / width)
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
        return img
    
    def export_as_image(self):
        img = self.generate_image()
        block_size = 8
        # scale up
        width, height = img.size
        img = img.resize((width * block_size, height * block_size),
                         resample=Image.NEAREST)
        # write to file
        img_filename = self.app.documents_dir + PALETTE_DIR + self.name + '.png'
        img.save(img_filename)
    
    def all_colors_opaque(self):
        "returns True if we have any non-opaque (<1 alpha) colors"
        for color in self.colors[1:]:
            if color[3] < 255:
                return False
        return True
    
    def get_random_non_palette_color(self):
        "returns random color not in this palette, eg for 8-bit transparency"
        def rand_byte():
            return randint(0, 255)
        # assume full alpha
        r, g, b, a = rand_byte(), rand_byte(), rand_byte(), 255
        while (r, g, b, a) in self.colors:
            r, g, b = rand_byte(), rand_byte(), rand_byte()
        return r, g, b, a
    
    def get_palettized_image(self, src_img, transparent_color=(0, 0, 0),
                             force_no_transparency=False):
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
        # user-defined color 0 in case we want to do 8-bit transparency
        if not force_no_transparency:
            colors[0:3] = transparent_color
        # PIL will fill out <256 color palettes with bogus values :/
        while len(colors) < MAX_COLORS * 3:
            for i in range(3):
                colors.append(0)
        # palette for PIL must be exactly 256 colors
        colors = colors[:256*3]
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
    
    def get_closest_color_index(self, r, g, b):
        "returns index of closest color in this palette to given color (kinda slow?)"
        closest_diff = 99999999999
        closest_diff_index = -1
        for i,color in enumerate(self.colors):
            l1, a1, b1 = rgb_to_lab(r, g, b)
            l2, a2, b2 = rgb_to_lab(*color[:3])
            diff = lab_color_diff(l1, a1, b1, l2, a2, b2)
            if diff < closest_diff:
                closest_diff = diff
                closest_diff_index = i
        #print('%s is closest to input color %s' % (self.colors[closest_diff_index], (r, g, b)))
        return closest_diff_index
    
    def get_random_color_index(self):
        # exclude transparent first index
        return randint(1, len(self.colors))


class PaletteFromList(Palette):
    
    "palette created from list of 3/4-tuple base-255 colors instead of image"
    
    def __init__(self, app, src_color_list, log):
        self.init_success = False
        self.app = app
        # generate a unique non-user-facing palette name
        name = 'PaletteFromList_%s' % time.time()
        self.filename = self.name = self.base_filename = name
        colors = []
        for color in src_color_list:
            # assume 1 alpha if not given
            if len(color) == 3:
                colors.append((color[0], color[1], color[2], 255))
            else:
                colors.append(color)
        self.colors = [(0, 0, 0, 0)] + colors
        lightest = 0
        darkest = 255 * 3 + 1
        for color in self.colors:
            luminosity = color[0]*0.21 + color[1]*0.72 + color[2]*0.07
            if luminosity < darkest:
                darkest = luminosity
                self.darkest_index = len(self.colors) - 1
            elif luminosity > lightest:
                lightest = luminosity
                self.lightest_index = len(self.colors) - 1
        # create texture
        img = Image.new('RGBA', (MAX_COLORS, 1), (0, 0, 0, 0))
        x = 0
        for color in self.colors:
            img.putpixel((x, 0), color)
            x += 1
        self.texture = Texture(img.tobytes(), MAX_COLORS, 1)
        if log and not self.app.game_mode:
            self.app.log("generated new palette '%s'" % (self.name))
            self.app.log('  unique colors: %s' % int(len(self.colors)-1))
            self.app.log('  darkest color index: %s' % self.darkest_index)
            self.app.log('  lightest color index: %s' % self.lightest_index)
    
    def has_updated(self):
        "No bitmap source for this type of palette, so no hot-reload"
        return False


class PaletteFromFile(Palette):
    
    def __init__(self, app, src_filename, palette_filename, colors=MAX_COLORS):
        self.init_success = False
        src_filename = app.find_filename_path(src_filename)
        if not src_filename:
            app.log("Couldn't find palette source image %s" % src_filename)
            return
        # dither source image, re-save it, use that as the source for a palette
        src_img = Image.open(src_filename)
        # method:
        src_img = src_img.convert('P', None, Image.FLOYDSTEINBERG, Image.ADAPTIVE, colors)
        src_img = src_img.convert('RGBA')
        # write converted source image with new filename
        # snip path & extension if it has em
        palette_filename = os.path.basename(palette_filename)
        palette_filename = os.path.splitext(palette_filename)[0]
        # get most appropriate path for palette image
        palette_path = app.get_dirnames(PALETTE_DIR, False)[0]
        # if new filename exists, add a number to avoid overwriting
        if os.path.exists(palette_path + palette_filename + '.png'):
            i = 0
            while os.path.exists('%s%s%s.png' % (palette_path, palette_filename, str(i))):
                i += 1
            palette_filename += str(i)
        # (re-)add path and PNG extension
        palette_filename = palette_path + palette_filename + '.png'
        src_img.save(palette_filename)
        # create the actual palette and export it as an image
        Palette.__init__(self, app, palette_filename, True)
        self.export_as_image()
