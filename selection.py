import numpy as np

from renderable_line import LineRenderable

class SelectionRenderable(LineRenderable):
    
    color = (0.8, 0.8, 0.8, 1)
    line_width = 3
    x, y, z = 0, 0, 0
    # verts include Z for different layers - set 2 for a cool glitch :]
    vert_items = 3
    
    def build_geo(self):
        self.vert_array = np.array([], dtype=np.float32)
        self.elem_array = np.array([], dtype=np.uint32)
        self.color_array = np.array([], dtype=np.float32)
    
    def get_adjacent_tile(self, tiles, x, y, dir_x, dir_y):
        # TODO: this search is crummy, make tiles a dict instead!
        for tile in tiles:
            if (tile[2] == x + dir_x) and (-tile[3] == y + dir_y):
                return tile
        return None
    
    def get_lines_for_tile(self, tiles, x, y):
        """
        use rules to detect if a tile is above, below,
        to left or right of this one, draw lines accordingly
        """
        above = self.get_adjacent_tile(tiles, x, y, 0, -1)
        below = self.get_adjacent_tile(tiles, x, y, 0, 1)
        left = self.get_adjacent_tile(tiles, x, y, -1, 0)
        right = self.get_adjacent_tile(tiles, x, y, 1, 0)
        if not above:
            # top line
            pass
        if not below:
            # bottom line
            pass
        if not left:
            # left line
            pass
        if not right:
            # right line
            pass
    
    def rebuild_geo(self, tiles):
        v, e, c = [], [], []
        w, h = self.app.ui.active_art.width, self.app.ui.active_art.height
        index = 0
        for tile in tiles:
            frame, layer, x, y = tile[0], tile[1], tile[2], -tile[3]
            z = self.app.ui.active_art.layers_z[layer]
            # verts = corners
            # top left
            v += [(  x,   y, z)]
            # top right
            v += [(x+1,   y, z)]
            # bottom right
            v += [(x+1, y-1, z)]
            # bottom left
            v += [(  x, y-1, z)]
            # elements = edges
            # top
            e += [index, index+1]
            # right
            e += [index+1, index+2]
            # bottom
            e += [index+2, index+3]
            # left
            e += [index+3, index]
            c += self.color * 4
            index += 4
        self.vert_array = np.array(v, dtype=np.float32)
        self.elem_array = np.array(e, dtype=np.uint32)
        self.color_array = np.array(c, dtype=np.float32)
    
    def reset_loc(self):
        pass
    
    def get_projection_matrix(self):
        return self.app.camera.projection_matrix
    
    def get_view_matrix(self):
        return self.app.camera.view_matrix
    
    def render(self, elapsed_time):
        LineRenderable.render(self, elapsed_time)
        #print('hi')
