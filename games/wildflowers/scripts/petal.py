
import random

from games.wildflowers.scripts.ramps import PALETTE_RAMPS

PETAL_CHARS = [
    # solid block
    255,
    # shaded boxes
    254, 253,
    # solid circle
    122,
    # curved corner lines, NW NE SE SW
    105, 107, 139, 137,
    # mostly-solid curved corners, NW NE SE SW
    144, 146, 178, 176,
    # solid inward wedges, NW NE SE SW
    148, 149, 164, 165
]


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
