
from game_util_objects import WorldGlobalsObject, GameObject
from image_export import export_animation

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
    handle_key_events = True
    
    def __init__(self, world, obj_data=None):
        WorldGlobalsObject.__init__(self, world, obj_data)
    
    def pre_first_update(self):
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
            self.world.spawn_object_of_class('SeedDisplay')
    
    def handle_key_down(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        if key != 'e':
            return
        if not self.flower:
            return
        #self.flower.exportable_art.save_to_file()
        #self.app.load_art_for_edit(self.flower.exportable_art.filename)
        #export_animation(self.app, self.flower.exportable_art,
        #                 self.flower.export_filename + '.gif',
        #                 bg_color=self.world.bg_color, loop=False)
        #self.app.log('Exported %s.gif' % self.flower.export_filename)


class SeedDisplay(GameObject):
    
    generate_art = True
    art_width, art_height = 30, 1
    art_charset = 'ui'
    art_palette = 'c64_original'
    
    def __init__(self, world, obj_data=None):
        GameObject.__init__(self, world, obj_data)
        self.art.clear_frame_layer(0, 0)
        f = world.globals.flower
        self.art.write_string(0, 0, 0, 0, str(f.seed), 12, 0)
        self.set_scale(0.275, 0.275, 1)
        self.set_loc(f.art_width, f.art_height / -2)