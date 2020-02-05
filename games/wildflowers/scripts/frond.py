
import random

from games.wildflowers.scripts.ramps import RampIterator


# growth direction consts
NONE       = (0, 0)
LEFT       = (-1, 0)
LEFT_UP    = (-1, -1)
UP         = (0, -1)
RIGHT_UP   = (1, -1)
RIGHT      = (1, 0)
RIGHT_DOWN = (1, 1)
DOWN       = (0, 1)
LEFT_DOWN  = (-1, 1)
DIRS = [LEFT, LEFT_UP, UP, RIGHT_UP, RIGHT, RIGHT_DOWN, DOWN, LEFT_DOWN]

FROND_CHARS = [
    # thick and skinny \
    151, 166,
    # thick and skinny /
    150, 167,
    # thick and skinny X
    183, 182,
    # solid inward wedges, NW NE SE SW
    148, 149, 164, 165
]


class Frond:
    
    min_life, max_life = 3, 16
    random_char_chance = 0.5
    mutate_char_chance = 0.2
    # layer all fronds should paint on
    layer = 0
    debug = False
    
    def __init__(self, flower, index):
        self.flower = flower
        self.index = index
        self.finished_growing = False
        # choose growth function
        self.growth_functions = [self.grow_straight_line, self.grow_curl,
                                 self.grow_wander_outward]
        self.get_grow_dir = random.choice(self.growth_functions)
        #self.get_grow_dir = self.grow_curl # DEBUG
        # for straight line growers, set a consistent direction
        if self.get_grow_dir == self.grow_straight_line:
            self.grow_line = random.choice(DIRS)
        self.growth_history = []
        self.chaos = random.random()
        self.life = random.randint(self.min_life, self.max_life)
        # pick a starting point near center
        w, h = self.flower.art_width, self.flower.art_height
        self.x = random.randint(int(w / 4), int(w / 2) - 1)
        self.y = random.randint(int(h / 4), int(h / 2) - 1)
        # get a random color ramp from flower's palette
        self.ramp = RampIterator(self.flower)
        self.color = self.ramp.color
        # chance to use a fully random (non-blank) character
        if random.random() < self.chaos * self.random_char_chance:
            self.char = random.choice(FROND_CHARS)
        else:
            self.char = random.randint(1, 255)
        # first grow() will paint first character
    
    def grow(self):
        """
        grows this frond by another tile
        return True if we painted, so flower can skip frame wait
        """
        painted = False
        if self.life <= 0 or self.color == self.ramp.end:
            self.finished_growing = True
            if self.debug:
                print(' frond %i finished.' % self.index)
            return painted
        if self.debug:
            print(' frond %i at (%i, %i) using %s' % (self.index, self.x, self.y, self.get_grow_dir.__name__))
        # if we're out of bounds, simply don't paint;
        # we might go back in bounds next grow
        if 0 <= self.x < self.flower.art_width - 1 and \
           0 <= self.y < self.flower.art_height - 1:
            self.flower.paint_mirrored(self.layer, self.x, self.y,
                                       self.char, self.color)
            painted = True
        self.growth_history.append((self.x, self.y))
        self.life -= 1
        self.color = self.ramp.go_to_next_color()
        # roll against chaos to mutate character
        if random.random() < self.chaos * self.mutate_char_chance:
            self.char = random.choice(FROND_CHARS)
        # TODO: roll against chaos to change grow function?
        # determine last grow direction and base next grow on it
        last_growth = self.growth_history[-1]
        if len(self.growth_history) > 1:
            penultimate_growth = self.growth_history[-2]
            last_x = last_growth[0] - penultimate_growth[0]
            last_y = last_growth[1] - penultimate_growth[1]
        else:
            last_x, last_y = 0, 0
        grow_x, grow_y = self.get_grow_dir((last_x, last_y))
        self.x, self.y = self.x + grow_x, self.y + grow_y
        return painted
    
    # paint and growth functions work in top left quadrant, then mirrored
    
    def grow_straight_line(self, last_dir):
        return self.grow_line
    
    def grow_wander_outward(self, last_dir):
        # (original prototype growth algo)
        return random.choice([LEFT_UP, LEFT, UP])
    
    def grow_curl(self, last_dir):
        if last_dir == NONE:
            return random.choice([LEFT, LEFT_UP, UP])
        # 2:1 weighting for current dir
        elif last_dir == LEFT:
            return random.choice([LEFT, LEFT, LEFT_UP])
        elif last_dir == LEFT_UP:
            return random.choice([LEFT_UP, LEFT_UP, UP])
        elif last_dir == UP:
            return random.choice([UP, UP, RIGHT_UP])
        elif last_dir == RIGHT_UP:
            return random.choice([RIGHT_UP, RIGHT_UP, RIGHT])
        elif last_dir == RIGHT:
            return random.choice([RIGHT, RIGHT, RIGHT_DOWN])
        elif last_dir == RIGHT_DOWN:
            return random.choice([RIGHT_DOWN, RIGHT_DOWN, DOWN])
        elif last_dir == DOWN:
            return random.choice([DOWN, DOWN, LEFT_DOWN])
        elif last_dir == LEFT_DOWN:
            return random.choice([LEFT_DOWN, LEFT_DOWN, LEFT])
