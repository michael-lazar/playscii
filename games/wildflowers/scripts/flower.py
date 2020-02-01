
import time, random

from game_object import GameObject
from art import UV_FLIPX, UV_FLIPY, UV_ROTATE180

from games.wildflowers.scripts.ramps import PALETTE_RAMPS
from games.wildflowers.scripts.petal import Petal
from games.wildflowers.scripts.frond import Frond


# draw in top left quadrant; grow up and to left
GROW_DIRS = [
    (-1, -1),
    (-1, 0),
    (0, -1)
]


# TODO: random size range?
FLOWER_WIDTH, FLOWER_HEIGHT = 16, 16


class FlowerObject(GameObject):
    
    generate_art = True
    should_save = False
    physics_move = False
    art_width, art_height = FLOWER_WIDTH, FLOWER_HEIGHT
    
    min_petals, max_petals = 0, 3
    min_fronds, max_fronds = 2, 8
    
    def __init__(self, world, obj_data=None):
        GameObject.__init__(self, world, obj_data)
        # set random seed based on date, a different flower each day
        t = time.localtime()
        year, month, day = t.tm_year, t.tm_mon, t.tm_mday
        weekday = t.tm_wday # 0 = monday
        date = year * 10000 + month * 100 + day
        # DEBUG: make date seed a highly specific decimal with seconds
        # (note: this turns the seed from an int into a float)
        date += t.tm_hour * 0.01 + t.tm_min * 0.0001 + t.tm_sec * 0.000001
        self.seed = date
        random.seed(self.seed)
        #random.seed(20200129.214757) # DEBUG: manually set seed for testing
        self.app.log('seed: %s' % self.seed)
        # set up art with character set, size, and a random (supported) palette
        self.art.set_charset_by_name('jpetscii')
        palette = random.choice(list(PALETTE_RAMPS.keys()))
        self.art.set_palette_by_name(palette)
        self.art.resize(self.art_width, self.art_height)
        self.app.ui.adjust_for_art_resize(self) # grid etc
        self.art.clear_frame_layer(0, 0)
        # petals on a layer underneath fronds
        self.art.add_layer(z=-0.001, name='petals')
        #self.world.bg_color = self.art.palette.colors[random.choice(PALETTE_RAMPS[self.art.palette.name])[-1]] # DEBUG: BG is random color from end of a ramp
        self.finished_growing = False
        self.petals = []
        for i in range(random.randint(self.min_petals, self.max_petals)):
            self.petals.append(Petal(self, i))
        self.fronds = []
        for i in range(random.randint(self.min_fronds, self.max_fronds)):
            self.fronds.append(Frond(self, i))
    
    def update(self):
        GameObject.update(self)
        if self.app.get_elapsed_time() % 2 != 0:
            return
        if not self.finished_growing:
            self.update_growth()
    
    def update_growth(self):
        print('update growth:')
        grew = False
        for p in self.petals:
            if not p.finished_growing:
                grew = True
                p.grow()
        for f in self.fronds:
            if not f.finished_growing:
                grew = True
                f.grow()
                # break so that each frond grows one at a time
                break
        if not grew:
            self.finished_growing = True
            print('flower finished')
    
    def paint_mirrored(self, layer, x, y, char, fg, bg=0):
        # draw in top left
        self.art.set_tile_at(0, layer, x, y, char, fg, bg)
        # mirror in other three quadrants
        top_right = (self.art_width - 1 - x, y)
        bottom_left = (x, self.art_height - 1 - y)
        bottom_right = (self.art_width - 1 - x, self.art_height - 1 - y)
        self.art.set_tile_at(0, layer, *top_right,
                             char, fg, bg, transform=UV_FLIPX)
        self.art.set_tile_at(0, layer, *bottom_left,
                             char, fg, bg, transform=UV_FLIPY)
        self.art.set_tile_at(0, layer, *bottom_right,
                             char, fg, bg, transform=UV_ROTATE180)
    
    def generate_petals(self):
        petal_count = random.randint(0, 3)
        self.app.log('%s petal%s' % (petal_count, 's' if petal_count != 1 else ''))
        for i in range(petal_count):
            #
            # TODO: move this to Petal.init
            #
            size = random.randint(2, int(self.art_width / 3))
            start_x = random.randint(0, int(self.art_width / 3))
            start_y = random.randint(0, int(self.art_height / 3))
            char = random.choice(PETAL_CHARS)
            fg = self.art.palette.get_random_color_index()
            #fg = random.choice(PALETTE_RAMPS[self.art.palette.name])[-1]
            #
            # TODO: move this to Petal.grow
            #
            for y in range(start_y, start_y + size):
                for x in range(start_x, start_x + size):
                    self.paint_mirrored(1, x, y, char, fg)
    
    def generate_fronds(self):
        frond_count = random.randint(2, 8)
        self.app.log('%s fronds' % frond_count)
        for frond in range(frond_count):
            #
            # TODO: move all of this to Frond.init!
            #
            frond_life = random.randint(2, 8)
            # start at center
            x, y = int(self.art_width / 2) - 1, int(self.art_height / 2) - 1
            # color ramp from palette this frond will use
            ramp_start, ramp_length, ramp_stride = random.choice(PALETTE_RAMPS[self.art.palette.name])
            ramp_end = ramp_start + (ramp_length * ramp_stride)
            # determine starting color, somewhere along ramp
            start_step = random.randint(0, ramp_length - 1)
            fg = ramp_start + (start_step * ramp_stride)
            # 50% chance to try a truly random character
            if random.random() < 0.5:
                char = random.choice(FROND_CHARS)
            else:
                char = random.randint(0, 255)
            #
            # TODO: move all of this to Frond.grow!
            #
            while frond_life > 0 and fg != ramp_end:
                self.paint_mirrored(0, x, y, char, fg)
                # tick frond
                frond_life -= 1
                # shift color
                fg += ramp_stride
                # mutate char occasionally
                if random.random() < 0.2:
                    char = random.choice(FROND_CHARS)
                # grow frond
                grow_dir = random.choice(GROW_DIRS)
                x += grow_dir[0]
                y += grow_dir[1]
