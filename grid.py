import numpy as np

from renderable_line import LineRenderable

# grid that displays as guide for Cursor

AXIS_COLOR = (0.8, 0.8, 0.8, 0.5)
BASE_COLOR = (0.5, 0.5, 0.5, 0.25)
EXTENTS_COLOR = (0, 0, 0, 1)

class Grid(LineRenderable):
    
    visible = True
    draw_axes = False
    
    def get_tile_size(self):
        "Returns (width, height) grid size in tiles."
        return 1, 1
    
    def build_geo(self):
        "build vert, element, and color arrays"
        w, h = self.get_tile_size()
        # frame
        v = [(0, 0), (w, 0), (0, -h), (w, -h)]
        e = [0, 1, 1, 3, 3, 2, 2, 0]
        color = EXTENTS_COLOR
        c = color * 4
        index = 4
        # axes - Y and X
        if self.draw_axes:
            v += [(w/2, -h), (w/2, 0), (0, -h/2), (w, -h/2)]
            e += [4, 5, 6, 7]
            color = AXIS_COLOR
            c += color * 4
            index = 8
        # vertical lines
        color = BASE_COLOR
        for x in range(1, w):
            # skip middle line
            if not self.draw_axes or x != w/2:
                v += [(x, -h), (x, 0)]
                e += [index, index+1]
                c += color * 2
                index += 2
        for y in range(1, h):
            if not self.draw_axes or y != h/2:
                v += [(0, -y), (w, -y)]
                e += [index, index+1]
                c += color * 2
                index += 2
        self.vert_array = np.array(v, dtype=np.float32)
        self.elem_array = np.array(e, dtype=np.uint32)
        self.color_array = np.array(c, dtype=np.float32)
    
    def reset_loc(self):
        self.x = 0
        self.y = 0
        self.z = 0
    
    def reset(self):
        "macro for convenience - rescale, reposition, update renderable"
        self.build_geo()
        self.reset_loc()
        self.rebind_buffers()
    
    def update(self):
        pass
    
    def get_projection_matrix(self):
        return self.app.camera.projection_matrix
    
    def get_view_matrix(self):
        return self.app.camera.view_matrix


class ArtGrid(Grid):
    
    def reset_loc(self):
        self.x, self.y = 0, 0
        self.z = self.app.ui.active_art.layers_z[self.app.ui.active_art.active_layer]
    
    def reset(self):
        self.quad_size_ref = self.app.ui.active_art
        Grid.reset(self)
    
    def get_tile_size(self):
        return self.app.ui.active_art.width, self.app.ui.active_art.height


class GameGrid(Grid):
    
    draw_axes = True
    base_size = 800
    
    def get_tile_size(self):
        # TODO: dynamically adjust bounds based on furthest away objects?
        return self.base_size, self.base_size
    
    def set_base_size(self, new_size):
        self.base_size = new_size
        self.reset()
    
    def reset_loc(self):
        # center of grid at world zero
        qw, qh = self.get_quad_size()
        self.x = qw * -(self.base_size / 2)
        self.y = qh * (self.base_size / 2)
        self.z = 0
