import math

from art import Art
from renderable import TileRenderable

class GameObject:
    
    def __init__(self, app, art):
        self.x, self.y, self.z = 0, 0, 0
        self.scale_x, self.scale_y, self.scale_z = 1, 1, 1
        self.app = app
        # support a filename OR an existing Art object
        self.art = self.app.load_art(art) if type(art) is str else art
        if not self.art:
            self.app.log("Couldn't spawn GameObject with art %s" % art.filename)
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
        self.renderable.x, self.renderable.y = self.x, self.y
        self.renderable.z = self.z
        self.renderable.scale_x = self.scale_x
        self.renderable.scale_y = self.scale_y
        self.renderable.scale_z = self.scale_z
    
    def start_animating(self):
        self.renderable.animating = True
    
    def set_loc(self, x, y, z=None):
        self.x, self.y = x, y
        self.z = z or 0
    
    def render(self, layer):
        #print('GameObject %s layer %s has Z %s' % (self.art.filename, layer, self.art.layers_z[layer]))
        self.renderable.render(layer)


class WobblyThing(GameObject):
    
    def __init__(self, app, art):
        GameObject.__init__(self, app, art)
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
        self.scale_x = 0.5 + math.sin(self.app.elapsed_time / 10000)
        self.scale_y = 0.5 + math.sin(self.app.elapsed_time / 5000)
        GameObject.update(self)


class ParticleThing(GameObject):
    
    width, height = 8, 8
    
    def __init__(self, app):
        charset = app.load_charset('dos')
        palette = app.load_palette('ega')
        art = Art('smoke1', app, charset, palette, self.width, self.height)
        art.clear_frame_layer(0, 0, 0)
        GameObject.__init__(self, app, art)
        self.art.run_script_every('mutate')
