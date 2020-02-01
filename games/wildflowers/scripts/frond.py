
import random

from games.wildflowers.scripts.ramps import PALETTE_RAMPS, FROND_CHARS


# growth direction consts
LEFT       = (-1, 0)
LEFT_UP    = (-1, -1)
UP         = (0, -1)
RIGHT_UP   = (1, -1)
RIGHT      = (1, 0)
RIGHT_DOWN = (1, 1)
DOWN       = (0, 1)
LEFT_DOWN  = (-1, 1)


class Frond:
    
    min_life, max_life = 2, 8
    # layer all fronds should paint on
    layer = 0
    
    def __init__(self, flower, index):
        self.flower = flower
        self.index = index
        self.finished_growing = False
        self.growth_functions = [self.grow_diagonal]
        # TODO: choose growth function
        self.get_grow_dir = self.growth_functions[0]
        self.growth_history = []
        self.chaos = random.random()
        self.life = random.randint(self.min_life, self.max_life)
        # pick a starting point near center
        w, h = self.flower.art_width, self.flower.art_height
        self.x = random.randint(int(w / 4), int(w / 2))
        self.y = random.randint(int(h / 4), int(h / 2))
        # pick a random color ramp from flower's palette this frond will use
        self.ramp = random.choice(PALETTE_RAMPS[self.flower.art.palette.name])
        # we only need to remember the stride
        ramp_start, ramp_length, self.ramp_stride = self.ramp
        # calc ramp end index
        self.ramp_end = ramp_start + (ramp_length * self.ramp_stride)
        # determine starting color, somewhere along ramp
        start_step = random.randint(0, ramp_length - 1)
        self.color = ramp_start + (start_step * self.ramp_stride)
        # chance to try a fully random character
        if random.random() < self.chaos:
            self.char = random.choice(FROND_CHARS)
        else:
            self.char = random.randint(0, 255)
        print(' frond %i at (%i, %i)' % (self.index, self.x, self.y))
        # first grow() will paint first character
    
    def grow(self):
        if self.life <= 0 or self.color == self.ramp_end:
            self.finished_growing = True
            print(' frond %i finished.' % self.index)
            return
        print(' frond %i at (%i, %i)' % (self.index, self.x, self.y))
        # if we're out of bounds, simply don't paint;
        # we might go back in bounds next grow
        # TODO: return True/False if we painted, so flower can skip frame wait
        if 0 <= self.x < self.flower.art_width and \
           0 <= self.y < self.flower.art_height:
            self.flower.paint_mirrored(self.layer, self.x, self.y,
                                       self.char, self.color)
        self.growth_history.append((self.x, self.y))
        self.life -= 1
        self.color += self.ramp_stride
        # TODO: roll against chaos to mutate character
        # determine last grow direction and base next grow on it
        last_growth = self.growth_history[-1]
        if len(self.growth_history) > 1:
            penultimate_growth = self.growth_history[-2]
            last_x = penultimate_growth[0] - last_growth[0]
            last_y = penultimate_growth[1] - last_growth[1]
        else:
            last_x, last_y = 0, 0
        grow_x, grow_y = self.get_grow_dir((last_x, last_y))
        self.x, self.y = self.x + grow_x, self.y + grow_y
    
    # paint and growth functions work in top left quadrant, then mirrored
    
    def grow_diagonal(self, last_dir):
        # TODO: ability for these to *consistently* go in different diagonal
        # directions, based on seed?
        return LEFT_UP
    
    def grow_vertical(self, last_dir):
        return UP
    
    def grow_horizontal(self, last_dir):
        return LEFT
    
    def grow_wander_outward(self, last_dir):
        # TODO: adapt original growth algo
        pass
    
    def grow_curl(self, last_dir):
        pass
