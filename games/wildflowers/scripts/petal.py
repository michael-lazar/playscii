
import random

from games.wildflowers.scripts.ramps import PALETTE_RAMPS


class Petal:
    
    def __init__(self, flower, index):
        self.flower = flower
        self.index = index
        self.finished_growing = False
        self.chaos = random.random()
    
    def grow(self):
        # TODO: grow outward (up and left) from center? in horiz/verti/diagonal slices;
        # chance to change character when starting a new slice
        self.finished_growing = True # DEBUG
