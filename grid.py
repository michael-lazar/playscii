import numpy as np

from renderable_line import LineRenderable

# grid that displays as guide for Cursor

AXIS_COLOR = (0.8, 0.8, 0.8, 0.5)
BASE_COLOR = (0.5, 0.5, 0.5, 0.25)
EXTENTS_COLOR = (0, 0, 0, 1)

class Grid(LineRenderable):
    
    # squares to show past extents of active Art
    art_margin = 2
    visible = True
    draw_axes = False
    
    def build_geo(self):
        "build vert, element, and color arrays for"
        w, h = self.app.ui.active_art.width, self.app.ui.active_art.height
        ew, eh = w + (self.art_margin * 2), h + (self.art_margin * 2)
        # frame
        v = [(0, 0), (ew, 0), (0, -eh), (ew, -eh)]
        e = [0, 1, 1, 3, 3, 2, 2, 0]
        color = EXTENTS_COLOR
        c = color * 4
        index = 4
        # axes - Y and X
        if self.draw_axes:
            v += [(ew/2, -eh), (ew/2, 0), (0, -eh/2), (ew, -eh/2)]
            e += [4, 5, 6, 7]
            color = AXIS_COLOR
            c += color * 4
            index = 8
        # vertical lines
        color = BASE_COLOR
        for x in range(1, ew):
            # skip middle line
            if not self.draw_axes or x != ew/2:
                v += [(x, -eh), (x, 0)]
                e += [index, index+1]
                c += color * 2
                index += 2
        for y in range(1, eh):
            if not self.draw_axes or y != eh/2:
                v += [(0, -y), (ew, -y)]
                e += [index, index+1]
                c += color * 2
                index += 2
        self.vert_array = np.array(v, dtype=np.float32)
        self.elem_array = np.array(e, dtype=np.uint32)
        self.color_array = np.array(c, dtype=np.float32)
    
    def reset_loc(self):
        self.x = -self.art_margin
        self.y = self.art_margin
    
    def update(self):
        # TODO: if active_art has changed, adjust position and size accordingly,
        # then self.rebind_buffers()
        pass
    
    def get_projection_matrix(self):
        return self.app.camera.projection_matrix
    
    def get_view_matrix(self):
        return self.app.camera.view_matrix
