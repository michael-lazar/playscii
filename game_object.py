
from renderable import TileRenderable

class GameObject:
    
    def __init__(self, app, art_filename):
        self.x, self.y, self.z = 0, 0, 0
        self.app = app
        self.art = self.app.load_art(art_filename)
        if not self.art:
            self.app.log("Couldn't spawn GameObject with art %s" % art_filename)
            return
        self.renderable = TileRenderable(self.app, self.art)
        if not self.art in self.app.art_loaded_for_game:
            self.app.art_loaded_for_game.append(self.art)
        self.app.game_renderables.append(self.renderable)
        self.app.game_objects.append(self)
    
    def update(self):
        # TODO: if self.art has already updated this frame, don't bother
        self.art.update()
        self.renderable.update()
        self.renderable.x = self.x
        self.renderable.y = self.y
        self.renderable.z = self.z
    
    def start_animating(self):
        self.renderable.animating = True
    
    def set_loc(self, x, y, z=None):
        self.x, self.y = x, y
        self.z = z or 0
    
    def render(self):
        self.renderable.render()
