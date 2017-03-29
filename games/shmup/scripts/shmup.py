
import math, random

from game_object import GameObject
from game_util_objects import Player, Character, Projectile, StaticTileBG, ObjectSpawner

class ShmupPlayer(Player):
    state_changes_art = False
    move_state = 'stand'
    art_src = 'player'
    handle_key_events = True
    invincible = False # DEBUG
    serialized = Player.serialized + ['invincible']
    respawn_delay = 3
    # refire delay, else holding X chokes game
    fire_delay = 0.15
    
    def __init__(self, world, obj_data=None):
        Player.__init__(self, world, obj_data)
        # track last death and last fire time for respawn and refire delays
        self.last_death_time = 0
        self.last_fire_time = 0
        # save our start position
        self.start_x, self.start_y = self.x, self.y
    
    def handle_key_down(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        if key == 'x' and self.state == 'dead':
            # respawn after short delay
            time = self.world.get_elapsed_time() / 1000
            if time >= self.last_death_time + self.respawn_delay:
                self.state = 'stand'
                self.set_loc(self.start_x, self.start_y)
                self.visible = True
    
    def update_state(self):
        # only two states, ignore stuff parent class does for this
        pass
    
    def die(self, killer):
        if self.invincible or self.state == 'dead':
            return
        boom = Boom(self.world)
        boom.set_loc(self.x, self.y)
        self.state = 'dead'
        self.last_death_time = self.world.get_elapsed_time() / 1000
        self.visible = False
    
    def update(self):
        Player.update(self)
        # poll fire key directly for continuous fire (with refire delay)
        if self.state != 'dead' and self.world.app.il.is_key_pressed('x'):
            time = self.world.get_elapsed_time() / 1000
            if time >= self.last_fire_time + self.fire_delay:
                proj = ShmupPlayerProjectile(self.world)
                proj.fire(self, 0, 1)
                self.last_fire_time = self.world.get_elapsed_time() / 1000


class PlayerBlocker(StaticTileBG):
    "keeps player from advancing too far upfield"
    art_src = 'blockline_horiz'
    noncolliding_classes = ['Projectile', 'ShmupEnemy']

class EnemySpawner(ObjectSpawner):
    "sits at top of screen and spawns enemies"
    art_src = 'spawn_area'
    spawn_random_in_bounds = True
    trigger_on_room_enter = False
    
    def __init__(self, world, obj_data=None):
        ObjectSpawner.__init__(self, world, obj_data)
        self.next_spawn_time = 0
        self.target_enemy_count = 1
    
    def can_spawn(self):
        player = self.world.get_first_object_of_type('ShmupPlayer')
        # only spawn if player has fired, there's room, and it's time
        return player and player.state != 'dead' and \
                player.last_fire_time > 0 and \
                len(self.spawned_objects) < self.target_enemy_count and \
                self.world.get_elapsed_time() >= self.next_spawn_time
    
    def get_spawn_class_name(self):
        roll = random.random()
        # pick random enemy type to spawn
        if roll > 0.8:
            return 'Enemy1'
        elif roll > 0.6:
            return 'Enemy2'
        else:
            return 'Asteroid'
    
    def update(self):
        StaticTileBG.update(self)
        # bump up enemy counts as time goes on
        time = self.world.get_elapsed_time() / 1000
        if time > 60:
            self.target_enemy_count = 4
        elif time > 30:
            self.target_enemy_count = 3
        elif time > 10:
            self.target_enemy_count = 2
        enemy = self.trigger()
        # if we spawned, pick next spawn time within random range
        if enemy:
            next_delay = random.random() * 3
            self.next_spawn_time = self.world.get_elapsed_time() + next_delay * 1000

class EnemyDeleter(StaticTileBG):
    "deletes enemies once they hit a certain point on screen"
    art_src = 'blockline_horiz'
    def started_colliding(self, other):
        if isinstance(other, ShmupEnemy):
            other.destroy()

class ShmupEnemy(Character):
    state_changes_art = False
    move_state = 'stand'
    should_save = False
    invincible = False # DEBUG
    serialized = Character.serialized + ['invincible']
    
    def started_colliding(self, other):
        if isinstance(other, ShmupPlayer):
            other.die(self)
    
    def fire_proj(self):
        proj = ShmupEnemyProjectile(self.world)
        # fire downward
        proj.fire(self, 0, -1)
    
    def update(self):
        self.move(0, -1)
        Character.update(self)

class Enemy1(ShmupEnemy):
    art_src = 'enemy1'
    move_accel_y = 100
    
    def update(self):
        # sine wave motion in X
        time = self.world.get_elapsed_time()
        self.x = math.sin(time / 200) * 6
        # fire very occasionally
        if random.random() < 0.05:
            self.fire_proj()
        ShmupEnemy.update(self)

class Enemy2(ShmupEnemy):
    art_src = 'enemy2'
    animating = True
    move_accel_y = 50
    
    def pre_first_update(self):
        ShmupEnemy.pre_first_update(self)
        # pick random lateral movement goal
        self.goal_x, y = self.spawner.get_spawn_location()
    
    def update(self):
        # move to random goal X
        dx = self.goal_x - self.x
        if 0 < abs(dx) < 0.5:
            self.x = self.goal_x
        elif dx > 0:
            self.move(1, 0)
        elif dx < 0:
            self.move(-1, 0)
        else:
            # fire salvo
            if random.random() < 0.1:
                self.fire_proj()
        ShmupEnemy.update(self)

class Asteroid(ShmupEnemy):
    "totally inert, just moves slowly down the screen"
    art_src = 'asteroid'
    move_accel_y = 200

class ShmupPlayerProjectile(Projectile):
    animating = True
    art_src = 'player_proj'
    use_art_instance = True
    noncolliding_classes = Projectile.noncolliding_classes + ['Boom', 'Player']
    def started_colliding(self, other):
        if isinstance(other, ShmupEnemy) and not other.invincible:
            boom = Boom(self.world)
            boom.set_loc(self.x, self.y)
            # spawn burst, destroy enemy
            other.destroy()
        self.destroy()

class ShmupEnemyProjectile(Projectile):
    animating = True
    art_src = 'enemy_proj'
    use_art_instance = True
    noncolliding_classes = Projectile.noncolliding_classes + ['Boom', 'ShmupEnemy']
    def started_colliding(self, other):
        if isinstance(other, ShmupPlayer) and other.state != 'dead':
            other.die(self)
        self.destroy()

class Boom(GameObject):
    art_src = 'boom'
    animating = True
    use_art_instance = True
    should_save = False
    z = 0.5
    scale_x, scale_y = 3, 3
    lifespan = 0.5
    def get_acceleration(self, vel_x, vel_y, vel_z):
        return 0, 0, -100

class Starfield(GameObject):
    
    "scrolling background with stars generated on-the-fly - no PSCI file!"
    
    generate_art = True
    art_width, art_height = 30, 41
    art_charset = 'jpetscii'
    alpha = 0.25
    # indices of star characters
    star_chars = [201]
    
    def pre_first_update(self):
        self.art.clear_frame_layer(0, 0)
    
    def create_star(self):
        "create a star at a random point along the top edge"
        x = int(random.random() * self.art_width)
        char = random.choice(self.star_chars)
        color = self.art.palette.get_random_color_index()
        self.art.set_tile_at(0, 0, x, 0, char, color)
    
    def update(self):
        # maybe create a star at the top, clear bottom line, then shift-wrap
        if random.random() < 0.25:
            self.create_star()
        self.art.clear_line(0, 0, self.art_height - 1)
        self.art.shift_all_frames(0, 1)
        GameObject.update(self)
