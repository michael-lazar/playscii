
import random

from game_util_objects import WorldGlobalsObject

from games.wildflowers.scripts.flower import FlowerObject

"""
overall approach:
grow multiple  "fronds" from center of top left quadrant,
mirror these in the other three quadrants

last commit of first gen approach (before rewrite & petals): commit a476248

frond style idea: frond draws each growth dir from a deck, reshuffling when empty to avoid repetition?
a frond style that weights growth dirs differently depending on its remaining life?

maybe weight frond start locations in a radius, ie likely to start from center, but rarely can start further and further away.

approaches to generate solid color shapes beneath (before) the linework? blocks, diamonds. these need a whole separate generation function(s).
- do diamonds imply a particular character used?

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
