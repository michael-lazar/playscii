
from game_object import GameObject
from game_util_objects import WorldGlobalsObject

"""

- size art to 8 x 8
- jpetscii set and dpaint palette
-- support multiple palettes + ramps? eg doom, heretic, quake too. atari = vertical ascending ramps
- clear (bg 0)

- starting at bottom right, create N "fronds" that grow out towards edges
-- pick an end point, or roll randomly to see if it's finished?
- define start (last index) of color ramps, increment through them as a frond grows
- choose different, pre-defined characters - how? chains of character mutations?

- when done, copy + mirror about X axis
- then copy + mirror about Y axis to complete the 2-axis symmetry

"""

class FlowerGlobals(WorldGlobalsObject):
    
    def __init__(self, world, obj_data=None):
        WorldGlobalsObject.__init__(self, world, obj_data)
    
    def pre_first_update(self):
        flower = FlowerObject(self.world)
        flower.art.run_script('generate_flower')
        self.world.camera.set_loc(flower.art_width / 2,
                                  -flower.art_height / 2, 10)
        self.flower = flower


class FlowerObject(GameObject):
    generate_art = True
    should_save = False
    physics_move = False
