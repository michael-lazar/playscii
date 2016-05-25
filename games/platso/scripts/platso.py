
import math

from game_object import GameObject
from game_util_objects import Player, StaticTileBG
from collision import CST_AABB

class PlatformWorld(StaticTileBG):
    draw_col_layer = True

class PlatformPlayer(Player):
    art_src = 'player'
    #collision_shape_type = CST_AABB
    col_width = 2
    col_height = 3
    handle_input_events = True
    fast_move_steps = 1
    col_radius = 1.75
    move_accel_x = 400
    move_accel_y = 2500
    ground_friction = 20
    air_friction = 15
    max_jump_press_time = 0.15
    editable = Player.editable + ['max_jump_press_time']
    # set False while in air
    jump_released = True
    
    def __init__(self, world, obj_data=None):
        Player.__init__(self, world, obj_data)
        self.jump_time = 0
    
    def started_colliding(self, other):
        Player.started_colliding(self, other)
    
    def is_affected_by_gravity(self):
        return True
    
    def allow_move_y(self, dy):
        # disable regular up/down movement, jump button sets move_y directly
        return False
    
    def update_state(self):
        self.state = 'stand' if self.is_on_ground() and (self.move_x, self.move_y) == (0, 0) else 'walk'
    
    def moved_this_frame(self):
        delta = math.sqrt(abs(self.last_x - self.x) ** 2 + abs(self.last_y - self.y) ** 2 + abs(self.last_z - self.z) ** 2)
        return delta > self.stop_velocity
    
    def is_on_ground(self):
        # works for now: just check for -Y contact with first world object
        ground = self.world.get_first_object_of_type('PlatformWorld')
        contact = self.collision.contacts.get(ground.name, None)
        if not contact:
            return False
        return contact.overlap.y < 0
    
    def update(self):
        on_ground = self.is_on_ground()
        if on_ground and self.jump_time > 0:
            self.jump_time = 0
        # poll jump key for variable length jump
        if self.world.app.il.is_key_pressed('x'):
            self.jump_time += self.get_time_since_last_update() / 1000
            if self.jump_time < self.max_jump_press_time:
                self.move_y += 1
        Player.update(self)
        # wobble as we walk a la ELC2
        if self.state == 'walk' and on_ground:
            self.y += math.sin(self.world.app.updates) / 5
