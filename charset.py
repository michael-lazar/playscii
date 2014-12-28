import os.path
from PIL import Image

from texture import Texture

CHARSET_DIR = 'charsets/'

class CharacterSet:
    
    transparent_color = (0, 0, 0)
    
    def __init__(self, src_filename):
        char_data_filename = CHARSET_DIR + src_filename + '.char'
        if not os.path.exists(char_data_filename):
            print("Couldn't find character set data file " + char_data_filename)
            return
        char_data = open(char_data_filename).readlines()
        # TODO: allow comments: discard any line in char data starting with //
        # (make sure this doesn't muck up legit mapping data)
        # first line = image file
        image_filename = char_data.pop(0).strip()
        # if not provided, guess a PNG
        if not os.path.exists(image_filename):
            image_filename = CHARSET_DIR + src_filename + '.png'
            if not os.path.exists(image_filename):
                print("Couldn't find character set image file " + image_filename)
                return
        # second line = character set dimensions
        second_line = char_data.pop(0).strip().split(',')
        self.map_width, self.map_height = int(second_line[0]), int(second_line[1])
        # strip newlines from mapping
        for row in range(self.map_height):
            char_data[row] = char_data[row].strip('\r\n')
        self.char_mapping = char_data
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
                    # TODO: does keeping non-alpha color improve sampling?
                    img.putpixel((x, y), (color[0], color[1], color[2], 0))
        self.texture = Texture(img.tostring(), self.image_width, self.image_height)
        self.u_width = self.map_width / self.image_width
        self.v_height = self.map_height / self.image_height
        # report
        print('new charmap from "%s":' % image_filename)
        #print('  %s characters' % len(self.chars))
        char_width = self.image_width / self.map_width
        char_height = self.image_height / self.map_height
        print('  char width/height: %s/%s' % (char_width, char_height))
        print('  map columns/rows: %s/%s' % (self.map_width, self.map_height))
        #print('  alphabet starts at index %s' % self.a)
        #print('  blank character at index %s' % self.blank)
        # TODO: account for / prevent non-square images!
    
    def get_uvs(self, char_value):
        "returns u,v coordinates for our texture from given char value"
        u = char_value % self.map_width
        v = self.map_height - ((char_value - u) / self.map_height)
        return u * self.u_width, v * self.v_height
