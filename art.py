
from random import randint
from random import choice

class Art:
    
    init_random = True
    
    def __init__(self, charset, palette, width, height):
        self.width, self.height = width, height
        # initialize char table
        # TODO: finalize decision that list-of-row-lists is best format
        self.chars, self.fg_colors, self.bg_colors = [], [], []
        for y in range(self.height):
            char_line, fg_line, bg_line = [], [], []
            for x in range(self.width):
                new_char_index = 0
                new_fg_color = (1, 1, 1, 1)
                new_bg_color = (0, 0, 0, 1)
                if self.init_random:
                    new_char_index = randint(0, 255)
                    new_fg_color = choice(palette.colors)
                    new_bg_color = choice(palette.colors)
                char_line.append(new_char_index)
                fg_line.append(new_fg_color)
                bg_line.append(new_bg_color)
            self.chars.append(char_line)
            self.fg_colors.append(fg_line)
            self.bg_colors.append(bg_line)
        # test
        self.set_char_index_at(1, 1, charset.get_char_index('H'))
        self.set_char_index_at(2, 1, charset.get_char_index('e'))
        self.set_char_index_at(3, 1, charset.get_char_index('l'))
        self.set_char_index_at(4, 1, charset.get_char_index('l'))
        self.set_char_index_at(5, 1, charset.get_char_index('o'))
        self.set_char_index_at(6, 1, charset.get_char_index('!'))
    
    # set methods
    def set_char_index_at(self, x, y, index):
        self.chars[y][x] = index
    
    # get methods
    def get_char_index_at(self, x, y):
        return self.chars[y][x]
    
    def get_fg_color_at(self, x, y):
        # TODO: where's the best place to convert colors from tuple of bytes
        # to tuple of normalized floats?
        # probably palette init so we never have to worry about it again
        c = self.fg_colors[y][x]
        return (c[0] / 255, c[1] / 255, c[2] / 255, c[3] / 255)
    
    def get_bg_color_at(self, x, y):
        c = self.bg_colors[y][x]
        return (c[0] / 255, c[1] / 255, c[2] / 255, c[3] / 255)
