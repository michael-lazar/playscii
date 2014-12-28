
from random import randint

class Art:
    
    def __init__(self, width, height):
        self.width, self.height = width, height
    
    def get_char_at(self, x, y):
        return randint(0, 255)
