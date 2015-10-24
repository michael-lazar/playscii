
from game_util_objects import Player

class MazePlayer(Player):
    art_src = 'player'
    move_state = 'stand'
    col_radius = 0.5
    
    def __init__(self, world, obj_data=None):
        Player.__init__(self, world, obj_data)
        self.held_object = None
    
    def pick_up(self, pickup):
        # drop any other held item first
        if self.held_object:
            self.drop(self.held_object, pickup)
        self.held_object = pickup
        pickup.holder = self
        self.world.hud.post_msg('got %s!' % pickup.display_name)
        pickup.disable_collision()
    
    def drop(self, pickup, new_pickup=None):
        # drop pickup in place of one we're swapping with, else drop at feet
        if new_pickup:
            pickup.x, pickup.y = new_pickup.x, new_pickup.y
        else:
            pickup.x, pickup.y = self.x, self.y
        pickup.holder = None
    
    def use_item(self):
        if self.held_object.consume_on_use:
            obj, self.held_object = self.held_object, None
            obj.holder = None
            obj.destroy()
