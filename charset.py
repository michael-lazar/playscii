import os.path
from PIL import Image

from texture import Texture

CHARSET_DIR = 'charsets/'

class CharacterSet:
    
    logg = False
    transparent_color = (0, 0, 0)
    
    def __init__(self, src_filename):
        self.name = os.path.basename(src_filename)
        self.name = os.path.splitext(self.name)[0]
        char_data_filename = CHARSET_DIR + src_filename + '.char'
        if not os.path.exists(char_data_filename):
            print("Couldn't find character set data file " + char_data_filename)
            return
        char_data_src = open(char_data_filename).readlines()
        # allow comments: discard any line in char data starting with //
        # (make sure this doesn't muck up legit mapping data)
        char_data = []
        for line in char_data_src:
            if not line.startswith('//'):
                char_data.append(line)
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
        # TODO: why is /2 necessary here?!?
        self.u_width = (self.map_width / self.image_width) / 2
        self.v_height = (self.map_height / self.image_height) / 2
        # report
        if self.logg:
            print('new charmap from %s:' % char_data_filename)
            print('  image %s is %s x %s' % (image_filename, self.image_width, self.image_height))
            #print('  %s characters' % len(self.chars))
            char_width = int(self.image_width / self.map_width)
            char_height = int(self.image_height / self.map_height)
            print('  char pixel width / height: %s x %s' % (char_width, char_height))
            print('  map columns/rows: %s/%s' % (self.map_width, self.map_height))
            #print('  alphabet starts at index %s' % self.a)
            #print('  blank character at index %s' % self.blank)
        # TODO: account for / prevent non-square images!
    
    def get_char_index(self, char):
        i = 0
        for line in self.char_mapping:
            for other_char in line:
                if char == other_char:
                    return i
                i += 1
        return 0
    
    def get_uvs(self, char_value):
        "returns u,v coordinates for our texture from given char value"
        u = char_value % self.map_width
        v = self.map_height - ((char_value - u) / self.map_height)
        return u * self.u_width, v * self.v_height
