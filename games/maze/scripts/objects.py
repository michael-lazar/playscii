
import random

from game_object import GameObject
from collision import CST_NONE, CST_CIRCLE, CST_AABB, CST_TILE, CT_NONE, CT_GENERIC_STATIC, CT_GENERIC_DYNAMIC, CT_PLAYER, CTG_STATIC, CTG_DYNAMIC

class MazeCritter(GameObject):
    art_src = 'player'
    state_changes_art = True
    move_state = 'stand'
    col_radius = 0.5
    collision_shape_type = CST_CIRCLE
    collision_type = CT_GENERIC_DYNAMIC
    should_save = False
    move_rate = 0.5
    
    def pre_first_update(self):
        self.z = 0.1
        # TODO: each critter should have its own ArtInstance
        random_color = random.randint(0, len(self.art.palette.colors))
        for art in self.arts.values():
            art.set_all_non_transparent_colors(random_color)
    
    def update(self):
        x, y = (random.random() * 2) - 1, (random.random() * 2) - 1
        x *= self.move_rate
        y *= self.move_rate
        self.move(x, y)
        GameObject.update(self)
