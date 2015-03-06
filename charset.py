import os.path
from PIL import Image

from texture import Texture

CHARSET_DIR = 'charsets/'
CHARSET_FILE_EXTENSION = 'char'

class CharacterSet:
    
    transparent_color = (0, 0, 0)
    
    def __init__(self, app, src_filename, log):
        self.init_success = False
        self.app = app
        self.filename = src_filename
        # small chance we have a filename that == a dir name, eg "ui"
        if not os.path.exists(self.filename) or os.path.isdir(self.filename):
            self.filename = CHARSET_DIR + self.filename
        if not os.path.exists(self.filename):
            self.filename += '.%s' % CHARSET_FILE_EXTENSION
        if not os.path.exists(self.filename):
            self.app.log("Couldn't find character set data file %s" % self.filename)
            return
        self.name = os.path.basename(self.filename)
        self.name = os.path.splitext(self.name)[0]
        char_data_src = open(self.filename).readlines()
        # allow comments: discard any line in char data starting with //
        # (make sure this doesn't muck up legit mapping data)
        char_data = []
        for line in char_data_src:
            if not line.startswith('//'):
                char_data.append(line)
        # first line = image file
        image_filename = char_data.pop(0).strip()
        image_filename = os.path.splitext(image_filename)[0]
        if not os.path.exists(image_filename) or os.path.isdir(image_filename):
            image_filename = CHARSET_DIR + image_filename
            if not os.path.exists(image_filename):
                image_filename += '.png'
                if not os.path.exists(image_filename):
                    # if no image found, try name of data file w/ png extension
                    image_filename = self.filename.replace('.%s' % CHARSET_FILE_EXTENSION, '.png')
                if not os.path.exists(image_filename):
                    self.app.log("Couldn't find character set image file %s" % image_filename)
                    return
        # second line = character set dimensions
        second_line = char_data.pop(0).strip().split(',')
        self.map_width, self.map_height = int(second_line[0]), int(second_line[1])
        # strip newlines from mapping
        for row in range(self.map_height):
            char_data[row] = char_data[row].strip('\r\n')
        # char mapping: a dict
        self.char_mapping = {}
        index = 0
        for line in char_data:
            for char in line:
                if not char in self.char_mapping:
                    self.char_mapping[char] = index
                index += 1
            if index >= self.map_width * self.map_height:
                break
        # last valid index a character can be
        self.last_index = index
        # load and process image
        img = Image.open(image_filename)
        img = img.convert('RGBA')
        # flip for openGL
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        self.image_width, self.image_height = img.size
        # any pixel that is "transparent color" will be made fully transparent
        # any pixel that isn't will be opaque + tinted FG color
        for y in range(self.image_height):
            for x in range(self.image_width):
                color = img.getpixel((x, y))
                if color[:3] == self.transparent_color[:3]:
                    # MAYBE-TODO: does keeping non-alpha color improve sampling?
                    img.putpixel((x, y), (color[0], color[1], color[2], 0))
        self.texture = Texture(img.tostring(), self.image_width, self.image_height)
        # save image data for later, eg image conversion
        self.image_data = img
        # store character dimensions and UV size
        self.char_width = int(self.image_width / self.map_width)
        self.char_height = int(self.image_height / self.map_height)
        self.u_width = self.char_width / self.image_width
        self.v_height = self.char_height / self.image_height
        # report
        if log:
            self.app.log("loaded charmap '%s' from %s:" % (self.name, self.filename))
            self.app.log('  source texture %s is %s x %s pixels' % (image_filename, self.image_width, self.image_height))
            self.app.log('  char pixel width/height is %s x %s' % (self.char_width, self.char_height))
            self.app.log('  char map width/height is %s x %s' % (self.map_width, self.map_height))
            self.app.log('  last character index: %s' % self.last_index)
        self.init_success = True
    
    def get_char_index(self, char):
        return self.char_mapping.get(char, 0)
