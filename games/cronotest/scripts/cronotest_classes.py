import math

from game_util_objects import TopDownPlayer, StaticTileBG, StaticTileObject, DynamicBoxObject, Pickup
from collision import CST_AABB

class CronoPlayer(TopDownPlayer):
    art_src = 'crono'
    
    col_radius = 1.5
    
    # AABB testing
    #collision_shape_type = CST_AABB
    #col_offset_x, col_offset_y = 0, 1.25
    
    col_width = 3
    col_height = 3
    art_off_pct_y = 0.9

class Chest(DynamicBoxObject):
    art_src = 'chest'
    col_width, col_height = 6, 4
    col_offset_y = -0.5

class Urn(Pickup):
    art_src = 'urn'
    col_radius = 2
    art_off_pct_y = 0.85

class Bed(StaticTileObject):
    art_src = 'bed'
    art_off_pct_x, art_off_pct_y = 0.5, 1
