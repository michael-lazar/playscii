
import math, random

from art import TileIter
from game_object import GameObject
from game_util_objects import Player, StaticTileBG
from collision import CST_NONE, CST_CIRCLE, CST_AABB, CST_TILE, CT_NONE, CT_GENERIC_STATIC, CT_GENERIC_DYNAMIC, CT_PLAYER, CTG_STATIC, CTG_DYNAMIC

class MazeBG(StaticTileBG):
    z = -0.1

class MazeCritter(GameObject):
    art_src = 'npc'
    col_radius = 0.5
    collision_shape_type = CST_CIRCLE
    collision_type = CT_GENERIC_DYNAMIC
    should_save = False
    move_rate = 0.5
    
    def pre_first_update(self):
        self.z = 0.1
        # TODO: each critter should have its own ArtInstance
        random_color = random.randint(3, len(self.art.palette.colors))
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
    consume_on_use = True
    
    def __init__(self, world, obj_data=None):
        GameObject.__init__(self, world, obj_data)
        self.holder = None
    
    def started_colliding(self, other):
        if not isinstance(other, Player):
            return
        if self is other.held_object:
            return
        other.pick_up(self)
    
    def stopped_colliding(self, other):
        if not isinstance(other, Player):
            return
        if self is not other.held_object:
            self.enable_collision()
    
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
    display_name = 'a gold key'
    used_message = 'unlocked!'

class MazeAx(MazePickup):
    art_src = 'ax'
    display_name = 'an ax'
    consume_on_use = False
    used_message = 'chop!'

class MazePortalKey(MazePickup):
    art_src = 'artifact'
    display_name = 'the Artifact of Zendor'
    used_message = '!!??!?!!?!?!?!!'
    
    def update(self):
        MazePickup.update(self)
        ch, fg, bg, xform = self.art.get_tile_at(0, 0, 0, 0)
        # before artifact is held, fluctuate char
        if not self.holder:
            ch += 1
            ch %= self.art.charset.last_index
            if ch == 0:
                ch = 1
        # always fluctuate its color
        fg += 1
        fg %= len(self.art.palette.colors)
        self.art.set_tile_at(0, 0, 0, 0, ch, fg, bg, xform)


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
            self.world.hud.post_msg('need %s!' % self.key_type.display_name)
    
    def unlocked(self, other):
        self.disable_collision()
        self.visible = False
        other.use_item()


class MazeBlockage(MazeLock):
    art_src = 'debris'
    key_type = MazeAx


class MazePortalGate(MazeLock):
    
    art_src = 'portal'
    key_type = MazePortalKey
    collision_shape_type = CST_TILE
    collision_type = CT_GENERIC_STATIC
    
    def update(self):
        MazeLock.update(self)
        if self.collision_type == CT_NONE:
            if not self.art.is_script_running('conway'):
                self.art.run_script_every('conway')
            return
        # cycle non-black colors
        BLACK = 1
        LAST_COLOR = len(self.art.palette.colors) - 1
        for frame, layer, x, y in TileIter(self.art):
            ch, fg, bg, xform = self.art.get_tile_at(frame, layer, x, y)
            # alternate wedge characters
            if ch == 148:
                ch = 149
            elif ch == 149:
                ch = 148
            if fg != BLACK:
                fg += 1
                if fg > LAST_COLOR:
                    fg = 2
            if bg != BLACK:
                bg += 1
                if bg > LAST_COLOR:
                    bg = 2
            self.art.set_tile_at(frame, layer, x, y, ch, fg, bg, xform)
