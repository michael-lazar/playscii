import os.path

from texture import TextureFromFile

CHARSET_DIR = 'charsets/'

class CharacterSet:
    
    def __init__(self, src_filename):
        char_data_filename = CHARSET_DIR + src_filename + '.char'
        if not os.path.exists(char_data_filename):
            print("Couldn't find character set data file " + char_data_filename)
            return
        char_data = open(char_data_filename).readlines()
        # TODO: allow comments: discard any line in char data starting with //
        # first line = image file
        image_filename = char_data.pop(0).strip()
        # if not provided, guess a PNG
        if not os.path.exists(image_filename):
            image_filename = CHARSET_DIR + src_filename + '.png'
            if not os.path.exists(image_filename):
                print("Couldn't find character set image file " + image_filename)
                return
        self.texture = TextureFromFile(image_filename)
        # second line = character set dimensions
        second_line = char_data.pop(0).strip().split(',')
        self.map_width, self.map_height = int(second_line[0]), int(second_line[1])
        # strip newlines from mapping
        for row in range(self.map_height):
            char_data[row] = char_data[row].strip('\r\n')
        self.char_mapping = char_data
    
    def get_uvs(self, char_value):
        "returns u,v coordinates for our texture from given char value"
        u = char_value % self.map_width
        v = self.map_height - ((char_value - u) / self.map_height)
        return u * self.texture.width, v * self.texture.height
