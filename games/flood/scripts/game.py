
from random import choice

from art import TileIter
from game_object import GameObject


TILE_COLORS = [3, 4, 5, 6, 7]
STARTING_TURNS = 15
BOARD_WIDTH, BOARD_HEIGHT = 10, 10


class Board(GameObject):
    generate_art = True
    art_width, art_height = BOARD_WIDTH, BOARD_HEIGHT
    art_charset = 'jpetscii'
    art_palette = 'c64_original'
    handle_input_events = True
    
    def __init__(self, world, obj_data):
        GameObject.__init__(self, world, obj_data)
        self.reset()
    
    def reset(self):
        for frame, layer, x, y in TileIter(self.art):
            color = choice(TILE_COLORS)
            self.art.set_color_at(frame, layer, x, y, color, False)
        self.captured_tiles = [(0, 0)]
        self.turns = 20
    
    def get_adjacent_tiles(self, x, y):
        tiles = []
        if x > 0:
            tiles.append((x-1, y))
        if x < BOARD_WIDTH:
            tiles.append((x+1, y))
        if y > 0:
            tiles.append((x, y-1))
        if y < BOARD_HEIGHT:
            tiles.append((x, y+1))
        return tiles
    
    def flood_with_color(self, flood_color):
        # set captured tiles to new color
        for tile_x,tile_y in self.captured_tiles:
            self.art.set_color_at(0, 0, tile_x, tile_y, flood_color, False)
        # capture like-colored tiles adjacent to captured tiles
        for frame, layer, x, y in TileIter(self.art):
            if not (x, y) in self.captured_tiles:
                continue
            adjacents = self.get_adjacent_tiles(x, y)
            for adj_x,adj_y in adjacents:
                adj_color = self.art.get_bg_color_index_at(frame, layer, adj_x, adj_y)
                if adj_color == flood_color:
                    self.captured_tiles.append((adj_x, adj_y))
    
    def color_picked(self, color):
        self.flood_with_color(TILE_COLORS[color])
        self.turns -= 1
        if len(self.captured_tiles) == BOARD_WIDTH * BOARD_HEIGHT:
            print('win!')
        elif self.turns == 0:
            print('lose')
            # TODO: reset after delay / feedback
    
    def handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        # get list of valid keys from length of tile_colors
        valid_keys = ['%s' % str(i + 1) for i in range(len(TILE_COLORS))]
        if not key in valid_keys:
            return
        key = int(key) - 1
        self.color_picked(key)


class ColorBar(GameObject):
    generate_art = True
    art_width, art_height = len(TILE_COLORS), 1
    art_charset = 'jpetscii'
    art_palette = 'c64_original'
    
    def __init__(self, world, obj_data):
        GameObject.__init__(self, world, obj_data)
        i = 0
        for frame, layer, x, y in TileIter(self.art):
            print('%s, %s' % (x, y))
            self.art.set_color_at(frame, layer, x, y, TILE_COLORS[i], False)
            self.art.write_string(frame, layer, x, y, str(i + 1), 1)
            i += 1


class TurnsBar(GameObject):
    text = 'turns: %s'
    generate_art = True
    art_width, art_height = len(text) + 3, 1
    art_charset = 'jpetscii'
    art_palette = 'c64_original'
    
    def __init__(self, world, obj_data):
        GameObject.__init__(self, world, obj_data)
        self.board = None
    
    def pre_first_update(self):
        self.board = self.world.get_all_objects_of_type('Board')[0]
    
    def draw_text(self):
        if not self.board:
            return
        self.art.write_string(0, 0, 0, 0, self.text % self.board.turns, -1)
    
    def update(self):
        GameObject.update(self)
        self.draw_text()
