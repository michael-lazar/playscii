
from art import Art
from renderable import TileRenderable


class GameHUDArt(Art):
    #recalc_quad_height = False
    log_creation = False
    quad_width = 0.1


class GameHUDRenderable(TileRenderable):
    def get_projection_matrix(self):
        # much like UIRenderable, use UI's matrices to render in screen space
        return self.app.ui.view_matrix
    def get_view_matrix(self):
        return self.app.ui.view_matrix


class GameHUD:
    
    "stub HUD, subclass and put your own stuff here"
    
    def __init__(self, world):
        self.world = world
        self.arts, self.renderables = [], []
    
    def update(self, dt):
        for art in self.arts:
            art.update()
        for r in self.renderables:
            r.update()
    
    def render(self):
        for r in self.renderables:
            r.render()
