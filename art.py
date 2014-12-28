
from random import randint

class Art:
    
    init_random_chars = True
    
    def __init__(self, charset, width, height):
        self.width, self.height = width, height
        # initialize char table
        # TODO: finalize decision that list-of-row-lists is best format
        self.chars = []
        for y in range(self.height):
            line = []
            for x in range(self.width):
                new_char_index = 0
                if self.init_random_chars:
                    new_char_index = randint(0, 255)
                line.append(new_char_index)
            self.chars.append(line)
        # test
        self.set_char_index_at(1, 1, charset.get_char_index('H'))
        self.set_char_index_at(2, 1, charset.get_char_index('e'))
        self.set_char_index_at(3, 1, charset.get_char_index('l'))
        self.set_char_index_at(4, 1, charset.get_char_index('l'))
        self.set_char_index_at(5, 1, charset.get_char_index('o'))
        self.set_char_index_at(6, 1, charset.get_char_index('!'))
    
    def set_char_index_at(self, x, y, index):
        self.chars[y][x] = index
    
    def get_char_index_at(self, x, y):
        return self.chars[y][x]
