import math

from art import Art
from renderable import TileRenderable
from renderable_line import OriginIndicatorRenderable

class GameObject:
    
    move_accel_rate = 0.01
    # normal movement will accelerate up to this, final velocity is uncapped
    max_move_speed = 0.4
    friction = 0.1
    log_move = False
    show_origin = False
    # 0,0 = top left; 1,1 = bottom right; 0.5,0.5 = center
    origin_pct_x, origin_pct_y = 0.5, 0.5
    show_bounds = False
    
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
        self.origin_renderable = OriginIndicatorRenderable(app)
        # TODO: 1px LineRenderable showing object's bounding box
        #self.bounds_renderable = BoundsIndicatorRenderable(app)
        if not self.art in self.app.art_loaded_for_game:
            self.app.art_loaded_for_game.append(self.art)
        self.app.game_renderables.append(self.renderable)
        self.app.game_objects.append(self)
    
    def get_all_art(self):
        "returns a list of all Art used by this object"
        return [self.art]
    
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
        self.origin_renderable.set_transform_from_object(self)
        self.renderable.set_transform_from_object(self)
    
    def render(self, layer):
        #print('GameObject %s layer %s has Z %s' % (self.art.filename, layer, self.art.layers_z[layer]))
        self.renderable.render(layer)
        if self.show_origin:
            self.origin_renderable.render()


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
    camera_pan_scaler = 0
    
    def update(self):
        GameObject.update(self)
        # camera follow player
        if self.camera_pan_scaler != 0:
            self.app.camera.pan(self.vel_x * self.camera_pan_scaler,
                                self.vel_y * self.camera_pan_scaler)


class NSEWPlayer(Player):
    
    "top-down player character that can face & travel in 4 directions"
    
    camera_pan_scaler = 0.1
    anim_stand_base = 'stand'
    anim_walk_base = 'walk'
    anim_forward_base = 'fwd'
    anim_back_base = 'back'
    anim_right_base = 'right'
    
    def __init__(self, app, anim_prefix, loc=(0, 0, 0)):
        # load animations
        stand_fwd_anim_name = '%s_%s_%s' % (anim_prefix, self.anim_stand_base,
                                            self.anim_forward_base)
        stand_back_anim_name = '%s_%s_%s' % (anim_prefix, self.anim_stand_base,
                                             self.anim_back_base)
        stand_right_anim_name = '%s_%s_%s' % (anim_prefix, self.anim_stand_base,
                                              self.anim_right_base)
        walk_fwd_anim_name = '%s_%s_%s' % (anim_prefix, self.anim_walk_base,
                                           self.anim_forward_base)
        walk_back_anim_name = '%s_%s_%s' % (anim_prefix, self.anim_walk_base,
                                            self.anim_back_base)
        walk_right_anim_name = '%s_%s_%s' % (anim_prefix, self.anim_walk_base,
                                             self.anim_right_base)
        self.anim_stand_fwd = app.load_art(stand_fwd_anim_name)
        self.anim_stand_back = app.load_art(stand_back_anim_name)
        self.anim_stand_right = app.load_art(stand_right_anim_name)
        self.anim_walk_fwd = app.load_art(walk_fwd_anim_name)
        self.anim_walk_back = app.load_art(walk_back_anim_name)
        self.anim_walk_right = app.load_art(walk_right_anim_name)
        self.last_move_dir = (0, 0)
        # set initial pose
        Player.__init__(self, app, self.anim_stand_fwd, loc)
    
    def get_all_art(self):
        return [self.anim_stand_fwd, self.anim_stand_back, self.anim_stand_right,
                self.anim_walk_fwd, self.anim_walk_back, self.anim_walk_right]
    
    def move(self, dx, dy):
        Player.move(self, dx, dy)
        self.last_move_dir = (dx, dy)
    
    def face_left(self):
        if self.scale_x != -1:
            self.scale_x = -1
            #self.x += self.art.quad_width * self.art.width
    
    def face_right(self):
        if self.scale_x != 1:
            self.scale_x = 1
            #self.x -= self.art.quad_width * self.art.width
    
    def set_anim(self, new_anim):
        if self.art is not new_anim:
            self.art = new_anim
            self.renderable.set_art(self.art)
            self.renderable.start_animating()
    
    def update(self):
        Player.update(self)
        # set art and frame based on move direction/velocity
        if -0.01 < self.vel_x < 0.01 and -0.01 < self.vel_y < 0.01:
            self.renderable.stop_animating()
            # stand fwd/left/right/back based on last travel dir
            if self.last_move_dir[0] > 0:
                self.art = self.anim_stand_right
                self.face_right()
            elif self.last_move_dir[0] < 0:
                self.art = self.anim_stand_right
                self.face_left()
            elif self.last_move_dir[1] > 0:
                self.art = self.anim_stand_back
            else:
                self.art = self.anim_stand_fwd
            self.renderable.set_art(self.art)
        elif self.last_move_dir[0] > 0:
            self.set_anim(self.anim_walk_right)
            self.face_right()
        elif self.last_move_dir[0] < 0:
            self.set_anim(self.anim_walk_right)
            self.face_left()
        elif self.last_move_dir[1] > 0:
            self.set_anim(self.anim_walk_back)
            self.face_right()
        elif self.last_move_dir[1] < 0:
            self.set_anim(self.anim_walk_fwd)
            self.face_right()
        #self.renderable.set_transform_from_object(self)
