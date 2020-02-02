
import random

from game_util_objects import WorldGlobalsObject

from games.wildflowers.scripts.flower import FlowerObject

"""
overall approach:
grow multiple "petals" (shapes) and "fronds" (lines) from ~center of top left
quadrant, mirror these in the other three quadrants.

last commit of first gen approach (before rewrite & petals): commit a476248

display today's random seed in corner?
animated GIF output? paint each grow update to a new art frame, export that

frond style ideas:
- frond draws each growth dir from a deck, reshuffling when empty to avoid repetition?
- frond weights growth dirs differently depending on its remaining life?

maybe weight frond start locations in a radius, ie likely to start from center, but rarely can start further and further away.

character ramps based on direction changes, visual density, something else?
"""


class FlowerGlobals(WorldGlobalsObject):
    
    # if True, generate a 4x4 grid instead of just one
    test_gen = False
    
    def __init__(self, world, obj_data=None):
        WorldGlobalsObject.__init__(self, world, obj_data)
    
    def pre_first_update(self):
        # random dark BG color
        self.world.bg_color[0] = random.random() / 10
        self.world.bg_color[1] = random.random() / 10
        self.world.bg_color[2] = random.random() / 10
        if self.test_gen:
            for x in range(4):
                for y in range(4):
                    flower = self.world.spawn_object_of_class('FlowerObject')
                    flower.set_loc(x * flower.art.width, y * flower.art.height)
            self.world.camera.set_loc(25, 25, 35)
        else:
            flower = self.world.spawn_object_of_class('FlowerObject')
            self.world.camera.set_loc(0, 0, 10)
            self.flower = flower
