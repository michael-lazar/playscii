
from game_object import GameObject
from game_util_objects import WorldGlobalsObject


class FlowerGlobals(WorldGlobalsObject):
    
    # if True, generate a 4x4 grid instead of just one
    test_gen = False
    
    def __init__(self, world, obj_data=None):
        WorldGlobalsObject.__init__(self, world, obj_data)
    
    def pre_first_update(self):
        if self.test_gen:
            for x in range(4):
                for y in range(4):
                    flower = self.world.spawn_object_of_class('FlowerObject')
                    flower.set_loc(x * flower.art.width, y * flower.art.height)
            self.world.camera.set_loc(30, 20, 35)
        else:
            flower = self.world.spawn_object_of_class('FlowerObject')
            self.world.camera.set_loc(flower.art_width / 2,
                                  -flower.art_height / 2, 10)
            self.flower = flower


class FlowerObject(GameObject):
    
    generate_art = True
    should_save = False
    physics_move = False
    
    def __init__(self, world, obj_data=None):
        GameObject.__init__(self, world, obj_data)
        self.art.run_script('generate_flower')
