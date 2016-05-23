
from game_object import GameObject
from game_util_objects import Player, Character, Projectile

class ShmupPlayer(Player):
    state_changes_art = False
    art_src = 'player'
    handle_input_events = True
    
    def handle_key(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        if key.lower() == 'x':
            self.fire_proj()
    
    def fire_proj(self):
        proj = ShmupPlayerProjectile(self.world)
        proj.fire(self, 0, 1)
    
    def started_colliding(self, other):
        if isinstance(other, ShmupEnemy):
            print('die')
            boom = Boom(self.world)
            boom.set_loc(self.x, self.y)
            self.destroy()

class ShmupEnemy(Character):
    state_changes_art = False
    move_state = 'stand'
    invincible = False
    serialized = Character.serialized + ['invincible']

class Enemy1(ShmupEnemy):
    art_src = 'enemy1'

class Enemy2(ShmupEnemy):
    art_src = 'enemy2'
    animating = True

class ShmupPlayerProjectile(Projectile):
    animating = True
    art_src = 'player_proj'
    use_art_instance = True
    def started_colliding(self, other):
        boom = Boom(self.world)
        boom.set_loc(self.x, self.y)
        if isinstance(other, ShmupEnemy) and not other.invincible:
            # spawn burst, destroy enemy
            other.destroy()
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
    
    def update(self):
        GameObject.update(self)
        self.art.shift_all_frames(0, 1)
