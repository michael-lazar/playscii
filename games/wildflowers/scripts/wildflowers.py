
from game_util_objects import WorldGlobalsObject

from games.wildflowers.scripts.flower import FlowerObject

"""
overall approach:
grow multiple  "fronds" from center of top left quadrant,
mirror these in the other three quadrants


2020-01-30:

last commit of first gen approach (before petals): commit a476248

growth_functions = [grow_vertical, grow_horizontal, grow_diagonal, grow_curl, grow_wander_outward]

self.get_growth_dir = random.choice(self.growth_functions)
self.growth_history = []
# how chaotic this frond will be
self.chaos = random.random()
update:
if len(growth_history) == 0:
    new_x, new_y = pick starting point
else:
    last_growth = self.growth_history[-1]
    penultimate_growth = self.growth_history[-2]
    last_dir = last_growth - penultimate_growth
    new_x, new_y = self.get_growth_dir(last_dir)
if random.random() < self.chaos:
    char = new random char
if random.random() < self.chaos:
    self.get_growth_dir = randomly choose a new growth function
paint at char, new_x, new_y, next ramp color
add to growth_history

def grow_diagonal(self, last_dir):
    return (-1, 1)
def grow_curl(self, last_dir):
    if last_dir == UP:
        return random.choice((0, 1), (1, 1))
    elif etc


2020-01-28 notes:

"frond style" - different evolution step functions that produce different shapes, eg curls/spirals, right angles, sawtooths, diagonal or straight lines, etc.
- each style iterator should log and refer to steps it's already done, eg for curls turn clockwise. "if the last bud was up and left, either keep going up and left, or go straight up; if the last bud was up, either keep going up or go up and right; etc
- one style: frond draws each growth dir from a deck, reshuffling when empty to avoid repetition?
- possibly optional: some fronds are "pure" ones of each style, others mix between styles depending on age (eg first half curl, second half straight line?)
- one style weights growth dirs differently depending on its remaining life?

each frond should have a "chaos" value that determines how frequently it changes its character.

random range of start locations? fronds not connected to the center would be nice. maybe weight in a radius, ie likely to start from center, but rarely can start further and further away.

approaches to generate solid color shapes beneath (before) the linework? blocks, diamonds. these need a whole separate generation function(s).
- do diamonds imply a particular character used?

2019-12-22 ideas for future development:
- character ramps based on direction changes, visual density, something else?
- strategies for sometimes filling in tile BG colors? quarter circles or other patterns that mesh interestingly with char/fg details?
-- use ramps, fade over distance from center in a circle, diamond, square etc pattern
alt generation methods:
https://terbium.io/2018/11/wave-function-collapse
https://www.conwaylife.com/wiki/Conway%27s_Game_of_Life
"""


class FlowerGlobals(WorldGlobalsObject):
    
    # if True, generate a 4x4 grid instead of just one
    test_gen = False
    
    def __init__(self, world, obj_data=None):
        WorldGlobalsObject.__init__(self, world, obj_data)
    
    def pre_first_update(self):
        #self.world.bg_color[0] = 0.1 # DEBUG: dim red background for visibility
        if self.test_gen:
            for x in range(4):
                for y in range(4):
                    flower = self.world.spawn_object_of_class('FlowerObject')
                    flower.set_loc(x * flower.art.width, y * flower.art.height)
            self.world.camera.set_loc(30, 20, 35)
        else:
            flower = self.world.spawn_object_of_class('FlowerObject')
            self.world.camera.set_loc(0, 0, 10)
            self.flower = flower
