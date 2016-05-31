
import math, random

from art import TileIter
from game_object import GameObject
from game_util_objects import Player, StaticTileBG
from collision import CST_NONE, CST_CIRCLE, CST_AABB, CST_TILE, CT_NONE, CT_GENERIC_STATIC, CT_GENERIC_DYNAMIC, CT_PLAYER, CTG_STATIC, CTG_DYNAMIC

class MazeBG(StaticTileBG):
    z = -0.1

class MazeNPC(GameObject):
    art_src = 'npc'
    use_art_instance = True
    col_radius = 0.5
    collision_shape_type = CST_CIRCLE
    collision_type = CT_GENERIC_STATIC
    bark = 'Well hello there!'
    
    def started_colliding(self, other):
        if not isinstance(other, Player):
            return
        self.world.hud.post_msg(self.bark)
    
    def pre_first_update(self):
        self.z = 0.1
        # TODO: investigate why this random color set doesn't seem to work
        random.seed(self.name)
        random_color = random.randint(3, len(self.art.palette.colors))
        for art in self.arts.values():
            art.set_all_non_transparent_colors(random_color)

class MazeBaker(MazeNPC):
    bark = 'Sorry, all outta bread today!'

class MazeCritter(MazeNPC):
    
    "dynamically-spawned NPC that wobbles around"
    
    collision_type = CT_GENERIC_DYNAMIC
    should_save = False
    move_rate = 0.25
    bark = 'wheee!'
    
    def update(self):
        # skitter around randomly
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
    sound_filenames = {'pickup': 'pickup.ogg'}
    
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
    
    def picked_up(self, new_holder):
        self.holder = new_holder
        self.world.hud.post_msg('got %s!' % self.display_name)
        self.disable_collision()
        self.play_sound('pickup')
    
    def used(self, user):
        if 'used' in self.sound_filenames:
            self.play_sound('used')
        if self.consume_on_use:
            self.destroy()
    
    def destroy(self):
        if self.holder:
            self.holder.held_object = None
            self.holder = None
        GameObject.destroy(self)
    
    def update(self):
        GameObject.update(self)
        if not self.holder:
            return
        # if held, shadow holder
        self.x = self.holder.x
        # bob slightly above holder's head
        bob_y = math.sin(self.world.get_elapsed_time()  / 100) / 10
        self.y = self.holder.y + self.hold_offset_y + bob_y
        self.z = self.holder.z


class MazeKey(MazePickup):
    art_src = 'key'
    display_name = 'a gold key'
    used_message = 'unlocked!'

class MazeAx(MazePickup):
    art_src = 'ax'
    display_name = 'an ax'
    consume_on_use = False
    used_message = 'chop!'
    # TODO: see if there's a way to add to MazePickup's sound dict here :/
    sound_filenames = {'pickup': 'pickup.ogg',
                       'used': 'break.ogg'}

class MazePortalKey(MazePickup):
    art_src = 'artifact'
    display_name = 'the Artifact of Zendor'
    used_message = '!!??!?!!?!?!?!!'
    consume_on_use = False
    sound_filenames = {'pickup': 'artifact.ogg',
                       'used': 'portal.ogg'}
    
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
    mass = 0.0
    key_type = MazeKey
    
    def started_colliding(self, other):
        if not isinstance(other, Player):
            return
        if other.held_object and type(other.held_object) is self.key_type:
            self.unlocked(other)
        else:
            self.world.hud.post_msg('blocked - need %s!' % self.key_type.display_name)
    
    def unlocked(self, other):
        self.disable_collision()
        self.visible = False
        other.use_item()


class MazeBlockage(MazeLock):
    art_src = 'debris'
    key_type = MazeAx


class MazePortalGate(MazeLock):
    
    art_src = 'portalgate'
    key_type = MazePortalKey
    collision_shape_type = CST_TILE
    collision_type = CT_GENERIC_STATIC
    
    def update(self):
        MazeLock.update(self)
        if self.collision_type == CT_NONE:
            if not self.art.is_script_running('evap'):
                self.art.run_script_every('evap')
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
            if fg != BLACK and fg != 0:
                fg += 1
                if fg > LAST_COLOR:
                    fg = 2
            if bg != BLACK and bg != 0:
                bg += 1
                if bg > LAST_COLOR:
                    bg = 2
            self.art.set_tile_at(frame, layer, x, y, ch, fg, bg, xform)


class MazePortal(GameObject):
    art_src = 'portal'
    def update(self):
        GameObject.update(self)
        if self.app.updates % 2 != 0:
            return
        ramps = {11: 10, 10: 3, 3: 11}
        for frame, layer, x, y in TileIter(self.art):
            ch, fg, bg, xform = self.art.get_tile_at(frame, layer, x, y)
            fg = ramps.get(fg, None)
            self.art.set_tile_at(frame, layer, x, y, ch, fg, bg, xform)


class MazeStandingNPC(GameObject):
    art_src = 'npc'
    col_radius = 0.5
    collision_shape_type = CST_CIRCLE
    collision_type = CT_GENERIC_DYNAMIC
    bark = 'Well hello there!'
    
    def started_colliding(self, other):
        if not isinstance(other, Player):
            return
        self.world.hud.post_msg(self.bark)
