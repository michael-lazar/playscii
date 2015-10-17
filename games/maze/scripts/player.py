
from game_util_objects import Player

class MazePlayer(Player):
    art_src = 'player'
    move_state = 'stand'
    col_radius = 0.5
    
    def __init__(self, world, obj_data=None):
        Player.__init__(self, world, obj_data)
        self.held_object = None
