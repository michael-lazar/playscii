
import random

from game_object import GameObject
from game_util_objects import Player, Character, Projectile, StaticTileBG

class ShmupPlayer(Player):
    state_changes_art = False
    art_src = 'player'
    handle_input_events = True
    invincible = False # DEBUG
    serialized = Player.serialized + ['invincible']
    respawn_delay = 3
    # refire delay, else holding X chokes game
    fire_delay = 0.1
    
    def __init__(self, world, obj_data=None):
        Player.__init__(self, world, obj_data)
        self.last_death_time = 0
        self.last_fire_time = 0
        self.start_x, self.start_y = self.x, self.y
    
    def handle_key(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        if key == 'x':
            time = self.world.get_elapsed_time() / 1000
            if self.state == 'dead':
                if time >= self.death_time + self.respawn_delay:
                    self.state = 'stand'
                    self.set_loc(self.start_x, self.start_y)
            else:
                if time >= self.last_fire_time + self.fire_delay:
                    self.fire_proj()
                    self.last_fire_time = self.world.get_elapsed_time() / 1000
    
    def fire_proj(self):
        proj = ShmupPlayerProjectile(self.world)
        proj.fire(self, 0, 1)
    
    def die(self, killer):
        if self.invincible:
            return
        boom = Boom(self.world)
        boom.set_loc(self.x, self.y)
        self.state = 'dead'
        self.last_death_time = self.world.get_elapsed_time() / 1000
    
    def update(self):
        Player.update(self)
        if self.world.app.il.is_key_pressed('x'):
            # TODO: move firing to here
            pass

class PlayerBlocker(StaticTileBG):
    "keeps player from advancing too far upfield"
    art_src = 'blockline_horiz'
    noncolliding_classes = ['Projectile', 'ShmupEnemy']

class EnemySpawner(StaticTileBG):
    art_src = 'blockline_horiz'
    
    def __init__(self, world, obj_data=None):
        StaticTileBG.__init__(self, world, obj_data)
        self.enemies = []
    
    def spawn(self):
        roll = random.random()
        spawn_class = None
        if roll > 0.8:
            spawn_class = Enemy1
        elif roll > 0.6:
            spawn_class = Enemy2
        else:
            spawn_class = Asteroid
        # TODO: spawn enemy
    
    def update(self):
        StaticTileBG.update(self)
        if len(self.enemies) == 0:
            self.spawn()

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
    
    def update(self):
        self.move(0, -1)
        Character.update(self)

class Enemy1(ShmupEnemy):
    art_src = 'enemy1'
    # TODO: sine wave motion in X

class Enemy2(ShmupEnemy):
    art_src = 'enemy2'
    animating = True
    # TODO: move to random X, fire salvo

class Asteroid(ShmupEnemy):
    # TODO: totally inert, just move slowly down the screen
    pass

class ShmupPlayerProjectile(Projectile):
    animating = True
    art_src = 'player_proj'
    use_art_instance = True
    def started_colliding(self, other):
        if isinstance(other, ShmupEnemy) and not other.invincible:
            boom = Boom(self.world)
            boom.set_loc(self.x, self.y)
            # spawn burst, destroy enemy
            other.destroy()
        self.destroy()

class ShmupEnemyProjectile(Projectile):
    def started_colliding(self, other):
        if isinstance(other, ShmupPlayer):
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
    art_src = 'stars'
    use_art_instance = True
    alpha = 0.5
    
    def update(self):
        self.art.shift_all_frames(0, 1)
        GameObject.update(self)
