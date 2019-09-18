
import math

from game_util_objects import Player, BlobShadow
from games.maze.scripts.rooms import OutsideRoom

class PlayerBlobShadow(BlobShadow):
    z = 0
    fixed_z = True
    scale_x = scale_y = 0.5
    offset_y = -0.5
    def pre_first_update(self):
        BlobShadow.pre_first_update(self)
        # TODO: figure out why class default scale isn't taking?
        self.set_scale(0.5, 0.5, 1)


class MazePlayer(Player):
    art_src = 'player'
    move_state = 'stand'
    col_radius = 0.5
    # TODO: setting this to 2 fixes tunneling, but shouldn't slow down the player!
    fast_move_steps = 2
    attachment_classes = { 'shadow': 'PlayerBlobShadow' }
    
    def __init__(self, world, obj_data=None):
        Player.__init__(self, world, obj_data)
        self.held_object = None
    
    def pick_up(self, pickup):
        # drop any other held item first
        if self.held_object:
            self.drop(self.held_object, pickup)
        self.held_object = pickup
        pickup.picked_up(self)
    
    def drop(self, pickup, new_pickup=None):
        # drop pickup in place of one we're swapping with, else drop at feet
        if new_pickup:
            pickup.x, pickup.y = new_pickup.x, new_pickup.y
        else:
            pickup.x, pickup.y = self.x, self.y
        pickup.holder = None
    
    def use_item(self):
        self.world.hud.post_msg(self.held_object.used_message)
        self.held_object.used(self)
    
    def update(self):
        Player.update(self)
        if type(self.world.current_room) is OutsideRoom:
            self.z = 5 + math.sin(self.world.get_elapsed_time() / 300) * 2
        else:
            # slightly above blob shadow
            self.z = 0.01
