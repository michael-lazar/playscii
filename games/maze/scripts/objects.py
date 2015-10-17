
import math, random

from game_object import GameObject
from game_util_objects import Player, StaticTileBG
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


class MazePickup(GameObject):
    
    collision_shape_type = CST_CIRCLE
    collision_type = CT_GENERIC_DYNAMIC
    col_radius = 0.5
    
    hold_offset_y = 1.2
    
    def __init__(self, world, obj_data=None):
        GameObject.__init__(self, world, obj_data)
        self.holder = None
    
    def started_colliding(self, other):
        if not isinstance(other, Player):
            return
        if self is other.held_object:
            return
        self.picked_up(other)
    
    def picked_up(self, other):
        other.held_object = self
        self.holder = other
        print('got %s!' % self.name)
        self.collision_type = CT_NONE
    
    def update(self):
        GameObject.update(self)
        if not self.holder:
            return
        # if held, shadow holder
        self.x = self.holder.x
        # bob slightly above holder's head
        bob_y = math.sin(self.world.app.get_elapsed_time()  / 100) / 10
        self.y = self.holder.y + self.hold_offset_y + bob_y


class MazeKey(MazePickup):
    art_src = 'key'


class MazeLock(StaticTileBG):
    art_src = 'lock'
    collision_shape_type = CST_CIRCLE
    collision_type = CT_GENERIC_DYNAMIC
    col_radius = 0.5
    key_type = MazeKey
    
    def started_colliding(self, other):
        if not isinstance(other, Player):
            return
        if other.held_object and type(other.held_object) is self.key_type:
            self.unlocked(other)
        else:
            self.world.hud.post_msg('need a key!')
    
    def unlocked(self, other):
        self.collision_type = CT_NONE
        self.visible = False
        # consume key
        other.held_object.destroy()
        other.held_object = None
        # TODO: any benefit to destroying? (savegame?)
