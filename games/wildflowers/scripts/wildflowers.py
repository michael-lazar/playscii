
from game_object import GameObject
from game_util_objects import WorldGlobalsObject


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
