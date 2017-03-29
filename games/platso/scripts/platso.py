
import math, random

from game_object import GameObject
from game_util_objects import StaticTileBG, Player, Character, WarpTrigger
from collision import CST_AABB

class PlatformWorld(StaticTileBG):
    draw_col_layer = True

class PlatformPlayer(Player):
    
    # from http://www.piratehearts.com/blog/2010/08/30/40/:
    # JumpSpeed = sqrt(2.0f * Gravity * JumpHeight);
    
    art_src = 'player'
    #collision_shape_type = CST_AABB
    col_width = 2
    col_height = 3
    handle_key_events = True
    fast_move_steps = 1
    col_radius = 1.75
    move_accel_x = 400
    move_accel_y = 2500
    ground_friction = 20
    air_friction = 15
    max_jump_press_time = 0.15
    editable = Player.editable + ['max_jump_press_time']
    jump_key = 'x'
    
    def __init__(self, world, obj_data=None):
        Player.__init__(self, world, obj_data)
        self.jump_time = 0
        # don't jump again until jump is released and pressed again
        self.jump_ready = True
        self.started_jump = False
    
    def started_colliding(self, other):
        Player.started_colliding(self, other)
        if isinstance(other, PlatformMonster):
            # landing atop monster?
            dx, dy = other.x - self.x, other.y - self.y
            if abs(dy) > abs(dx) and dy < -1:
                other.destroy()
    
    def is_affected_by_gravity(self):
        return True
    
    def handle_key_down(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        if key == self.jump_key and self.jump_ready:
            self.jump()
            self.jump_ready = False
            self.started_jump = True
    
    def handle_key_up(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        if key == self.jump_key:
            self.jump_ready = True
    
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
    
    def jump(self):
        self.jump_time += self.get_time_since_last_update() / 1000
        if self.jump_time < self.max_jump_press_time:
            self.move_y += 1
    
    def update(self):
        on_ground = self.is_on_ground()
        if on_ground and self.jump_time > 0:
            self.jump_time = 0
        # poll jump key for variable length jump
        if self.world.app.il.is_key_pressed(self.jump_key) and \
           (self.started_jump or not on_ground):
            self.jump()
            self.started_jump = False
        Player.update(self)
        # wobble as we walk a la ELC2
        if self.state == 'walk' and on_ground:
            self.y += math.sin(self.world.app.updates) / 5

class PlatformMonster(Character):
    art_src = 'monster'
    move_state = 'stand'
    animating = True
    fast_move_steps = 2
    move_accel_x = 100
    col_radius = 1
    
    def pre_first_update(self):
        # pick random starting direction
        self.move_dir_x = random.choice([-1, 1])
        self.set_timer_function('hit_wall', self.check_wall_hits, 0.2)
    
    def is_affected_by_gravity(self):
        return True
    
    def allow_move_y(self, dy):
        return False
    
    def check_wall_hits(self):
        "Turn around if a wall is immediately ahead of direction we're moving."
        # check collision in direction we're moving
        margin = 0.1
        if self.move_dir_x > 0:
            x = self.x + self.col_radius + margin
        else:
            x = self.x - self.col_radius - margin
        y = self.y
        # DEBUG see trace destination
        #lines = [(self.x, self.y, 0), (x, y, 0)]
        #self.app.debug_line_renderable.set_lines(lines)
        hits, shapes = self.world.get_colliders_at_point(x, y,
                                    #include_object_names=[],
                                    include_class_names=['PlatformWorld',
                                                         'PlatformMonster'],
                                     exclude_object_names=[self.name])
        if len(hits) > 0:
            self.move_dir_x = -self.move_dir_x
    
    def update(self):
        self.move(self.move_dir_x, 0)
        Character.update(self)


class PlatformWarpTrigger(WarpTrigger):
    warp_class_names = ['Player', 'PlatformMonster']
