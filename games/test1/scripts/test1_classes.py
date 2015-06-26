import math
from random import randint

from art import Art
from game_object import GameObject, Player

class TestPlayer(Player):
    state_changes_art = False
    facing_changes_art = False

class WobblyThing(GameObject):
    
    serialized = GameObject.serialized + ['origin_x', 'origin_y', 'origin_z']
    
    def __init__(self, world, obj_data):
        GameObject.__init__(self, world, obj_data)
        self.origin_x = randint(0, 30)
        self.origin_y = randint(-30, 0)
        self.origin_z = randint(-5, 5)
        self.start_animating()
    
    def update(self):
        x_off = math.sin(self.app.elapsed_time / 1000) * self.origin_x
        y_off = math.sin(self.app.elapsed_time / 500) * self.origin_y
        z_off = math.sin(self.app.elapsed_time / 750) * self.origin_z
        self.x = self.origin_x + x_off
        self.y = self.origin_y + y_off
        self.z = self.origin_z + z_off
        scale_x = 0.5 + math.sin(self.app.elapsed_time / 10000) / 100
        scale_y = 0.5 + math.sin(self.app.elapsed_time / 5000) / 100
        self.set_scale(scale_x, scale_y, 1)
        GameObject.update(self)

class ParticleThing(GameObject):
    
    generate_art = True
    art_width, art_height = 8, 8
    art_charset = 'dos'
    art_palette = 'ega'
    
    def __init__(self, world, obj_data):
        GameObject.__init__(self, world, obj_data)
        self.art.run_script_every('mutate')
