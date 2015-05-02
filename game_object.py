import math, os

from art import Art
from renderable import TileRenderable
from renderable_line import OriginIndicatorRenderable, BoundsIndicatorRenderable, CircleCollisionRenderable, BoxCollisionRenderable
from collision import CT_NONE, CT_TILE, CT_CIRCLE, CT_AABB

class GameObject:
    
    # if specified, this art will be loaded instead of what's passed into init
    art_src = None
    move_accel_rate = 0.01
    # normal movement will accelerate up to this, final velocity is uncapped
    max_move_speed = 0.4
    friction = 0.1
    log_move = False
    show_origin = False
    show_bounds = False
    show_collision = False
    # static/dynamic: only relevant if collision type != CT_NONE
    # if false, object will only be checked by other, dynamic objects
    dynamic = False
    collision_type = CT_NONE
    # collision layer name for CT_TILE objects
    col_layer_name = 'collision'
    # collision circle/box offset from origin
    col_offset_x, col_offset_y = 0, 0
    col_radius = 1
    # AABB top left / bottom right coordinates
    col_box_left_x, col_box_right_x = -1, 1
    col_box_top_y, col_box_bottom_y = -1, 1
    # lists of classes to call back on overlap / collide with
    overlap_classes = []
    collide_classes = []
    
    def __init__(self, app, art, loc=(0, 0, 0)):
        self.initializing = True
        (self.x, self.y, self.z) = loc
        self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
        self.scale_x, self.scale_y, self.scale_z = 1, 1, 1
        self.flip_x = False
        # update_renderables should behave as if we transformed on first frame
        self.transformed_this_frame = True
        self.overlapping_objects = []
        self.colliding_objects = []
        # generate unique name for object 
        name = str(self)
        self.name = '%s_%s' % (type(self).__name__, name[name.rfind('x')+1:-1])
        self.app = app
        # specify art in art_src else use what's passed in
        if self.art_src:
            art = self.app.game_art_dir + self.art_src
        # support a filename OR an existing Art object
        self.art = self.app.load_art(art) if type(art) is str else art
        if not self.art:
            self.app.log("Couldn't spawn GameObject with art %s" % art.filename)
            return
        self.renderable = TileRenderable(self.app, self.art, self)
        self.origin_renderable = OriginIndicatorRenderable(app, self)
        self.collision_renderable = None
        if self.collision_type == CT_CIRCLE:
            self.collision_renderable = CircleCollisionRenderable(app, self)
        elif self.collision_type == CT_AABB:
            self.collision_renderable = BoxCollisionRenderable(app, self)
        # 1px LineRenderable showing object's bounding box
        self.bounds_renderable = BoundsIndicatorRenderable(app, self)
        if not self.art in self.app.art_loaded_for_game:
            self.app.art_loaded_for_game.append(self.art)
        self.app.game_renderables.append(self.renderable)
        self.app.game_objects.append(self)
        # whether we're static or dynamic, run these once to set proper state
        self.update_renderables()
        # CT_TILE objects base their box edges off renderable loc + size
        self.update_collision_box_edges()
        self.initializing = False
        self.app.log('Spawned %s with Art %s' % (self.name, os.path.basename(self.art.filename)))
    
    def get_all_art(self):
        "returns a list of all Art used by this object"
        return [self.art]
    
    def start_animating(self):
        self.renderable.start_animating()
    
    def stop_animating(self):
        self.renderable.stop_animating()
    
    def set_loc(self, x, y, z=None):
        if self.x != x or self.y != y:
            self.transformed_this_frame = True
        self.x, self.y = x, y
        if (not z and self.z != 0) or self.z != z:
            self.transformed_this_frame = True
        self.z = z or 0
    
    def set_scale(self, x, y, z):
        if self.scale_x != x or self.scale_y != y or self.scale_z != z:
            self.transformed_this_frame = True
        self.scale_x, self.scale_y, self.scale_z = x, y, z
    
    def started_overlap(self, other):
        #print('%s started overlapping with %s' % (self.name, other.name))
        self.overlapping_objects.append(other)
    
    def ended_overlap(self, other):
        #print('%s stopped overlapping with %s' % (self.name, other.name))
        self.overlapping_objects.remove(other)
    
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
    
    def update(self, should_update_renderables=True):
        if not self.art.updated_this_tick:
            self.art.update()
        self.last_x, self.last_y, self.last_z = self.x, self.y, self.z
        # apply friction and move
        if self.vel_x != 0 or self.vel_y != 0 or self.vel_z != 0:
            self.vel_x *= 1 - self.friction
            self.vel_y *= 1 - self.friction
            self.vel_z *= 1 - self.friction
            self.x += self.vel_x
            self.y += self.vel_y
            self.z += self.vel_z
            if self.log_move:
                debug = ['%s velocity: %.4f, %.4f' % (self.name, self.vel_x, self.vel_y)]
                self.app.ui.debug_text.post_lines(debug)
        if self.last_x != self.x or self.last_y != self.y or self.last_z != self.z:
            self.transformed_this_frame = True
            self.update_collision_box_edges()
        if should_update_renderables:
            self.update_renderables()
    
    def update_collision_box_edges(self):
        if self.collision_type == CT_NONE:
            self.left_x, self.right_x = 0, 0
            self.top_y, self.bottom_y = 0, 0
        elif self.collision_type == CT_TILE:
            self.left_x = self.renderable.x
            self.right_x = self.left_x + self.renderable.width
            self.top_y = self.renderable.y
            self.bottom_y = self.top_y - self.renderable.height
        elif self.collision_type == CT_CIRCLE:
            self.left_x = (self.x + self.col_offset_x) - self.col_radius
            self.right_x = self.x + self.col_radius
            self.top_y = (self.y + self.col_offset_y) + self.col_radius
            self.bottom_y = self.top_y - (self.col_radius * 2)
        elif self.collision_type == CT_AABB:
            self.left_x = (self.x + self.col_offset_x) + self.col_box_left_x
            self.right_x = self.x + self.col_box_right_x
            self.top_y = (self.y + self.col_offset_y) - self.col_box_top_y
            self.bottom_y = self.top_y + (self.col_box_top_y - self.col_box_bottom_y)
    
    def update_renderables(self):
        # even if debug viz are off, update once on init to set correct state
        if self.show_origin or self.initializing:
            self.origin_renderable.update()
        if self.show_bounds or self.initializing:
            self.bounds_renderable.update()
        if self.collision_renderable and (self.show_collision or self.initializing):
            self.collision_renderable.update()
        self.renderable.update()
    
    def render_debug(self):
        if self.show_origin:
            self.origin_renderable.render()
        if self.show_bounds:
            self.bounds_renderable.render()
        if self.show_collision and self.collision_renderable:
            self.collision_renderable.render()
    
    def render(self, layer, z_override=None):
        #print('GameObject %s layer %s has Z %s' % (self.art.filename, layer, self.art.layers_z[layer]))
        self.renderable.render(layer, z_override)


class StaticTileObject(GameObject):
    collision_type = CT_TILE

class StaticBoxObject(GameObject):
    collision_type = CT_AABB

class Pickup(GameObject):
    collision_type = CT_CIRCLE
    dyanmic = True


class WobblyThing(GameObject):
    
    dynamic = True
    
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
        scale_x = 0.5 + math.sin(self.app.elapsed_time / 10000) / 100
        scale_y = 0.5 + math.sin(self.app.elapsed_time / 5000) / 100
        self.set_scale(scale_x, scale_y, 1)
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
    dynamic = True
    collision_type = CT_AABB


class NSEWPlayer(Player):
    
    "top-down player character that can face & travel in 4 directions"
    
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
    
    def set_anim(self, new_anim):
        if self.art is not new_anim:
            self.art = new_anim
            self.renderable.set_art(self.art)
            self.bounds_renderable.art = self.art
            self.renderable.start_animating()
    
    def update(self):
        # tell update not to update renderables yet
        Player.update(self, False)
        # set art and frame based on move direction/velocity
        if -0.01 < self.vel_x < 0.01 and -0.01 < self.vel_y < 0.01:
            self.renderable.stop_animating()
            # stand fwd/left/right/back based on last travel dir
            if self.last_move_dir[0] > 0:
                self.set_anim(self.anim_stand_right)
                self.flip_x = False
            elif self.last_move_dir[0] < 0:
                self.set_anim(self.anim_stand_right)
                self.flip_x = True
            elif self.last_move_dir[1] > 0:
                self.set_anim(self.anim_stand_back)
            else:
                self.set_anim(self.anim_stand_fwd)
            self.renderable.set_art(self.art)
        elif self.last_move_dir[0] > 0:
            self.set_anim(self.anim_walk_right)
            self.flip_x = False
        elif self.last_move_dir[0] < 0:
            self.set_anim(self.anim_walk_right)
            self.flip_x = True
        elif self.last_move_dir[1] > 0:
            self.set_anim(self.anim_walk_back)
        elif self.last_move_dir[1] < 0:
            self.set_anim(self.anim_walk_fwd)
        # transforms all done, ready to update renderables
        self.update_renderables()
