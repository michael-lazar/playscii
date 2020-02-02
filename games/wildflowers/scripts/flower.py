
import time, random

from game_object import GameObject
from art import UV_FLIPX, UV_FLIPY, UV_ROTATE180, ART_DIR
from renderable import TileRenderable

from games.wildflowers.scripts.ramps import PALETTE_RAMPS
from games.wildflowers.scripts.petal import Petal
from games.wildflowers.scripts.frond import Frond


# TODO: random size range?
# (should also change camera zoom, probably frond/petal counts)
FLOWER_WIDTH, FLOWER_HEIGHT = 16, 16


class FlowerObject(GameObject):
    
    generate_art = True
    should_save = False
    physics_move = False
    art_width, art_height = FLOWER_WIDTH, FLOWER_HEIGHT
    
    min_petals, max_petals = 0, 4
    min_fronds, max_fronds = 0, 8
    # every flower must have at least this many petals + fronds
    minimum_complexity = 4
    
    # DEBUG: if True, add current time to date seed as a decimal,
    # to test with highly specific values
    # (note: this turns the seed from an int into a float)
    seed_includes_time = False
    # DEBUG: if nonzero, use this seed for testing
    debug_seed = 0
    debug_log = False
    
    def __init__(self, world, obj_data=None):
        GameObject.__init__(self, world, obj_data)
        # set random seed based on date, a different flower each day
        t = time.localtime()
        year, month, day = t.tm_year, t.tm_mon, t.tm_mday
        weekday = t.tm_wday # 0 = monday
        date = year * 10000 + month * 100 + day
        if self.seed_includes_time:
            date += t.tm_hour * 0.01 + t.tm_min * 0.0001 + t.tm_sec * 0.000001
        if self.debug_seed != 0:
            self.seed = self.debug_seed
        else:
            self.seed = date
        random.seed(self.seed)
        # set screen to random dark BG color
        self.world.bg_color[0] = random.random() / 10
        self.world.bg_color[1] = random.random() / 10
        self.world.bg_color[2] = random.random() / 10
        self.world.bg_color[3] = 1.0 # set here or alpha is zero?
        # set up art with character set, size, and a random (supported) palette
        self.art.set_charset_by_name('jpetscii')
        palette = random.choice(list(PALETTE_RAMPS.keys()))
        self.art.set_palette_by_name(palette)
        self.art.resize(self.art_width, self.art_height)
        self.app.ui.adjust_for_art_resize(self) # grid etc
        self.art.clear_frame_layer(0, 0)
        # petals on a layer underneath fronds?
        #self.art.add_layer(z=-0.001, name='petals')
        self.finished_growing = False
        # some flowers can be more petal-centric or frond-centric,
        # but keep a certain minimum complexity
        petal_count = random.randint(self.min_petals, self.max_petals)
        frond_count = random.randint(self.min_fronds, self.max_fronds)
        while petal_count + frond_count < self.minimum_complexity:
            petal_count = random.randint(self.min_petals, self.max_petals)
            frond_count = random.randint(self.min_fronds, self.max_fronds)
        self.petals = []
        #petal_count = 5 # DEBUG
        for i in range(petal_count):
            self.petals.append(Petal(self, i))
        # sort petals by radius largest to smallest,
        # so big ones don't totally stomp smaller ones
        self.petals.sort(key=lambda item: item.goal_radius, reverse=True)
        self.fronds = []
        #frond_count = 0 # DEBUG
        for i in range(frond_count):
            self.fronds.append(Frond(self, i))
        # track # of growth updates we've had
        self.grows = 0
        # create an art document we can add frames to and later export
        self.export_filename = '%s%swildflower_%s' % (self.app.documents_dir, ART_DIR, self.seed)
        self.exportable_art = self.app.new_art(self.export_filename,
                                               self.art_width, self.art_height,
                                               self.art.charset.name,
                                               self.art.palette.name)
        # re-set art's filename to be in documents dir rather than game dir :/
        self.exportable_art.set_filename(self.export_filename)
        # image export process needs a renderable
        r = TileRenderable(self.app, self.exportable_art)
    
    def update(self):
        GameObject.update(self)
        # only grow every other frame?
        #if self.app.get_elapsed_time() % 2 != 0:
        #    return
        if not self.finished_growing:
            self.update_growth()
    
    def update_growth(self):
        if self.debug_log:
            print('update growth:')
        grew = False
        for p in self.petals:
            if not p.finished_growing:
                grew = True
                p.grow()
                # break so that each petal grows one at a time
                break
        for f in self.fronds:
            # break if still growing petals
            if grew:
                break
            if not f.finished_growing:
                grew = True
                painted = f.grow()
                while not painted and not f.finished_growing:
                    painted = f.grow()
                # break so that each frond grows one at a time
                break
        self.copy_new_frame()
        self.grows += 1
        if not grew:
            self.finished_growing = True
            self.exportable_art.set_active_frame(self.exportable_art.frames - 1)
            if self.debug_log:
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
    
    def copy_new_frame(self):
        # add new frame to art for export
        # (art starts with 1 frame, only do this after first frame written)
        if self.grows > 0:
            self.exportable_art.add_frame_to_end(delay=0.01, log=False)
        self.exportable_art.chars[-1] = self.art.chars[0].copy()
        self.exportable_art.fg_colors[-1] = self.art.fg_colors[0].copy()
        self.exportable_art.bg_colors[-1] = self.art.bg_colors[0].copy()
        self.exportable_art.uv_mods[-1] = self.art.uv_mods[0].copy()
        self.exportable_art.uv_maps[-1] = self.art.uv_maps[0].copy()
