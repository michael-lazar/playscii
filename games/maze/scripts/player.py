
from game_util_objects import Player

class MazePlayer(Player):
    art_src = 'player'
    move_state = 'stand'
    col_radius = 0.5
    move_accel_x = move_accel_y = 25.
