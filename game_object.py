import math

from art import Art
from renderable import TileRenderable
from renderable_line import AxisIndicatorRenderable

class GameObject:
    
    move_accel_rate = 0.01
    # normal movement will accelerate up to this, final velocity is uncapped
    max_move_speed = 0.4
    friction = 0.1
    log_move = False
    
    def __init__(self, app, art, loc=(0, 0, 0)):
        (self.x, self.y, self.z) = loc
        self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
        self.scale_x, self.scale_y, self.scale_z = 1, 1, 1
        self.app = app
        # support a filename OR an existing Art object
        self.art = self.app.load_art(art) if type(art) is str else art
        if not self.art:
            self.app.log("Couldn't spawn GameObject with art %s" % art.filename)
            return
        self.renderable = TileRenderable(self.app, self.art)
        self.axis_renderable = AxisIndicatorRenderable(app)
        if not self.art in self.app.art_loaded_for_game:
            self.app.art_loaded_for_game.append(self.art)
        self.app.game_renderables.append(self.renderable)
        self.app.game_objects.append(self)
    
    def start_animating(self):
        self.renderable.start_animating()
    
    def stop_animating(self):
        self.renderable.stop_animating()
    
    def set_loc(self, x, y, z=None):
        self.x, self.y = x, y
        self.z = z or 0
    
    def move(self, dx, dy):
        m = 1 + self.friction
        vel_dx = dx * self.move_accel_rate * m
        vel_dy = dy * self.move_accel_rate * m
        # TODO: account for friction so max rate
        # (below doesn't work properly, figure it out)
        max_speed = self.max_move_speed# * (1 + self.friction)
        if vel_dx < 0:
            self.vel_x += max(vel_dx, -max_speed)
        elif vel_dx > 0:
            self.vel_x += min(vel_dx, max_speed)
        if vel_dy < 0:
            self.vel_y += max(vel_dy, -max_speed)
        elif vel_dy > 0:
            self.vel_y += min(vel_dy, max_speed)
    
    def update(self):
        if not self.art.updated_this_tick:
            self.art.update()
        # apply friction and move
        self.vel_x *= 1 - self.friction
        self.vel_y *= 1 - self.friction
        self.vel_z *= 1 - self.friction
        self.x += self.vel_x
        self.y += self.vel_y
        self.z += self.vel_z
        if self.log_move:
            debug = ['%s velocity: %.4f, %.4f' % (self, self.vel_x, self.vel_y)]
            self.app.ui.debug_text.post_lines(debug)
        # update renderables
        self.renderable.update()
        self.renderable.set_loc_from_object(self)
        self.renderable.set_scale_from_object(self)
        self.axis_renderable.set_loc_from_object(self)
    
    def render(self, layer):
        #print('GameObject %s layer %s has Z %s' % (self.art.filename, layer, self.art.layers_z[layer]))
        self.renderable.render(layer)
        self.axis_renderable.render()


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
        self.scale_x = 0.5 + math.sin(self.app.elapsed_time / 10000) / 100
        self.scale_y = 0.5 + math.sin(self.app.elapsed_time / 5000) / 100
        GameObject.update(self)


class ParticleThing(GameObject):
    
    width, height = 8, 8
    
    def __init__(self, app, loc=(0, 0, 0)):
        charset = app.load_charset('dos')
        palette = app.load_palette('ega')
        art = Art('smoke1', app, charset, palette, self.width, self.height)
        art.clear_frame_layer(0, 0, 0)
        GameObject.__init__(self, app, art, loc)
        self.art.run_script_every('mutate')


class Player(GameObject):
    move_accel_rate = 0.1
    max_move_speed = 0.8
    friction = 0.25
    log_move = True
