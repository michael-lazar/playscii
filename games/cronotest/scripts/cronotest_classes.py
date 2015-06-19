import math

from game_object import NSEWPlayer, StaticTileBG, StaticTileObject, DynamicBoxObject, Pickup

class CronoPlayer(NSEWPlayer):
    art_src = 'crono'
    col_offset_x, col_offset_y = 0, 1.25
    col_radius = 1.5
    art_off_pct_y = 0.9

class Chest(DynamicBoxObject):
    art_src = 'chest'
    col_box_left_x, col_box_right_x = -3, 3
    col_box_top_y, col_box_bottom_y = -2, 2
    col_offset_y = -0.5

class Urn(Pickup):
    art_src = 'urn'
    col_radius = 2
    art_off_pct_y = 0.85

class Bed(StaticTileObject):
    art_src = 'bed'
    art_off_pct_x, art_off_pct_y = 0.5, 1
