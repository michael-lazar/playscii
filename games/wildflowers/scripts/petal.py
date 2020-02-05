
import random, math

from games.wildflowers.scripts.ramps import RampIterator


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
    
    min_radius = 3
    mutate_char_chance = 0.2
    # layer all petals should paint on
    layer = 0
    debug = False
    
    def __init__(self, flower, index):
        self.flower = flower
        self.index = index
        self.finished_growing = False
        self.chaos = random.random()
        max_radius = int(self.flower.art_width / 2)
        self.goal_radius = random.randint(self.min_radius, max_radius)
        self.radius = 0
        ring_styles = [self.get_ring_tiles_box, self.get_ring_tiles_wings,
                       self.get_ring_tiles_diamond, self.get_ring_tiles_circle]
        self.get_ring_tiles = random.choice(ring_styles)
        # pick a starting point near center
        w, h = self.flower.art_width, self.flower.art_height
        self.x = random.randint(int(w / 4), int(w / 2) - 1)
        self.y = random.randint(int(h / 4), int(h / 2) - 1)
        # get a random color ramp from flower's palette
        self.ramp = RampIterator(self.flower)
        self.color = self.ramp.color
        # random char from predefined list
        self.char = random.choice(PETAL_CHARS)
    
    def grow(self):
        # grow outward (up and left) from center in "rings"
        if self.radius >= self.goal_radius:
            self.finished_growing = True
            return
        if self.debug:
            print(' petal %i at (%i, %i) at radius %i using %s' % (self.index, self.x, self.y, self.radius, self.get_ring_tiles.__name__))
        self.paint_ring()
        # grow and change
        self.radius += 1
        self.color = self.ramp.go_to_next_color()
        # roll against chaos to mutate character
        if random.random() < self.chaos * self.mutate_char_chance:
            self.char = random.choice(PETAL_CHARS)
    
    def paint_ring(self):
        tiles = self.get_ring_tiles()
        for t in tiles:
            x = self.x - t[0]
            y = self.y - t[1]
            # don't paint out of bounds
            if 0 <= x < self.flower.art_width - 1 and \
               0 <= y < self.flower.art_height - 1:
                self.flower.paint_mirrored(self.layer, x, y,
                                           self.char, self.color)
                #print('%s, %s' % (x, y))
    
    def get_ring_tiles_box(self):
        tiles = []
        for x in range(self.radius + 1):
            tiles.append((x, self.radius))
        for y in range(self.radius + 1):
            tiles.append((self.radius, y))
        return tiles
    
    def get_ring_tiles_dealieX(self):
        # not sure what to call this but it's a nice shape
        tiles = []
        for y in range(self.radius):
            for x in range(self.radius):
                tiles.append((x - self.radius, y - self.radius))
        return tiles
    
    def get_ring_tiles_wings(self):
        # not sure what to call this but it's a nice shape
        tiles = []
        cut_size = int(self.chaos * 4)
        for y in range(self.radius - cut_size):
            for x in range(self.radius - cut_size):
                x = x - self.radius
                y = y - self.radius
                tiles.append((x, y))
        return tiles

    
    def get_ring_tiles_diamond(self):
        tiles = []
        for y in range(self.radius, -1, -1):
            for x in range(0, self.radius + 1):
                if x + y == self.radius:
                    tiles.append((x, y))
        return tiles
    
    def get_ring_tiles_circle(self):
        tiles = []
        angle = 0
        resolution = 30
        for i in range(resolution):
            angle += math.radians(90.0 / resolution)
            x = round(math.cos(angle) * self.radius)
            y = round(math.sin(angle) * self.radius)
            if not (x, y) in tiles:
                tiles.append((x, y))
        return tiles
