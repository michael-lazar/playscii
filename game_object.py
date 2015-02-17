import math

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
    
    def render(self, layer):
        #print('GameObject %s layer %s has Z %s' % (self.art.filename, layer, self.art.layers_z[layer]))
        self.renderable.render(layer)


class WobblyThing(GameObject):
    
    def __init__(self, app, art_filename):
        GameObject.__init__(self, app, art_filename)
        self.origin_x, self.origin_y, self.origin_z = self.x, self.y, self.z
    
    def set_origin(self, x, y, z=None):
        self.origin_x, self.origin_y, self.origin_z = x, y, z or self.z
    
    def update(self):
        x_off = math.sin(self.app.elapsed_time / 1000) * self.origin_x
        y_off = math.sin(self.app.elapsed_time / 500) * self.origin_y
        z_off = math.sin(self.app.elapsed_time / 750) * self.origin_z
        self.x = self.origin_x + x_off
        self.y = self.origin_y + y_off
        self.z = self.origin_z + z_off
        GameObject.update(self)
