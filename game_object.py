import os
import pymunk

from art import Art
from renderable import TileRenderable
from renderable_line import OriginIndicatorRenderable, BoundsIndicatorRenderable, CircleCollisionRenderable, BoxCollisionRenderable, TileCollisionRenderable

from game_world import CT_NONE, CT_GENERIC_STATIC, CT_GENERIC_DYNAMIC, CT_PLAYER, CTG_STATIC, CTG_DYNAMIC

# collision shape types
CST_NONE = 0
CST_CIRCLE = 1
CST_AABB = 2
CST_TILE = 3

class GameObject:
    
    # if specified, this art will be loaded from disk
    art_src = None
    # if art_src not specified, blank art will be created with these dimensions
    art_width, art_height = 8, 8
    # Y-sort: if true, object will sort according to its Y position
    y_sort = False
    move_accel_rate = 0.01
    # normal movement will accelerate up to this, final velocity is uncapped
    max_move_speed = 0.4
    friction = 0.1
    # mass - only used by pymunk
    mass = 1
    log_move = False
    log_load = False
    log_spawn = False
    show_origin = False
    show_bounds = False
    show_collision = False
    # collision shape (tile, circle, AABB) and type (channel)
    collision_shape_type = CST_NONE
    collision_type = CT_NONE
    # segment thickness for AABB / tile based collision
    seg_thickness = 0.1
    # collision layer name for CST_TILE objects
    col_layer_name = 'collision'
    # collision circle/box offset from origin
    col_offset_x, col_offset_y = 0, 0
    col_radius = 1
    # AABB top left / bottom right coordinates
    col_box_left_x, col_box_right_x = -1, 1
    col_box_top_y, col_box_bottom_y = -1, 1
    # art offset from pivot: renderable's origin_pct set to this if !None
    # 0,0 = top left; 1,1 = bottom right; 0.5,0.5 = center
    art_off_pct_x, art_off_pct_y = 0.5, 0.5
    # list of members to serialize (no weak refs!)
    serialized = ['x', 'y', 'z', 'art_src', 'y_sort', 'art_off_pct_x', 'art_off_pct_y']
    
    def __init__(self, world, obj_data=None):
        self.x, self.y, self.z = 0, 0, 0
        # apply serialized data before most of init happens
        # properties that need non-None defaults should be declared above
        for v in self.serialized:
            if not hasattr(self, v):
                if log_load:
                    self.app.dev_log("Unknown serialized property '%s' for %s" % (v, self.name))
                continue
            elif not v in obj_data:
                if self.log_load:
                    self.app.dev_log("Serialized property '%s' not found for %s" % (v, self.name))
                continue
            setattr(self, v, obj_data[v])
        self.vel_x, self.vel_y, self.vel_z = 0, 0, 0
        self.scale_x, self.scale_y, self.scale_z = 1, 1, 1
        self.flip_x = False
        # generate unique name for object
        name = str(self)
        self.name = '%s_%s' % (type(self).__name__, name[name.rfind('x')+1:-1])
        self.world = world
        self.app = self.world.app
        # if art_src not specified, create a new art according to dimensions
        if not self.art_src:
            self.art_src = '%s_art' % self.name
            self.art = self.app.new_art(self.art_src, self.art_width,
                                        self.art_height)
        else:
            self.art = self.app.load_art(self.art_src)
        if not self.art:
            self.app.log("Couldn't spawn GameObject with art %s" % self.art_src)
            return
        self.renderable = TileRenderable(self.app, self.art, self)
        self.origin_renderable = OriginIndicatorRenderable(self.app, self)
        # 1px LineRenderable showing object's bounding box
        self.bounds_renderable = BoundsIndicatorRenderable(self.app, self)
        if not self.art in self.world.art_loaded:
            self.world.art_loaded.append(self.art)
        self.world.renderables.append(self.renderable)
        # remember previous collision type for enable/disable
        self.orig_collision_type = None
        self.collision_renderable = None
        self.col_shapes, self.col_body = [], []
        if self.collision_shape_type != CST_NONE:
            self.create_collision()
        self.world.objects.append(self)
        if self.log_spawn:
            self.app.log('Spawned %s with Art %s' % (self.name, os.path.basename(self.art.filename)))
    
    def create_collision(self):
        if self.is_dynamic():# and self.collision_type != CT_PLAYER:
            # TODO: calculate moment depending on type of shape
            self.col_body = pymunk.Body(self.mass, 1)
        else:
            if self.collision_shape_type == CT_GENERIC_STATIC:
                self.col_body = self.world.space.static_body
            else:
                self.col_body = pymunk.Body()
        self.col_body.position.x, self.col_body.position.y = self.x, self.y
        # give our body a link back to us
        self.col_body.gobj = self
        # create shapes in a separate method so shapes can be regen'd independently
        self.create_collision_shapes()
        # static bodies should always be "rogue" ie not added to world space
        if self.is_dynamic():# and self.collision_type != CT_PLAYER:
            self.world.space.add(self.col_body)
            pass
        if self.collision_shape_type == CST_CIRCLE:
            self.collision_renderable = CircleCollisionRenderable(self.app, self)
        elif self.collision_shape_type == CST_AABB:
            self.collision_renderable = BoxCollisionRenderable(self.app, self)
        elif self.collision_shape_type == CST_TILE:
            self.collision_renderable = TileCollisionRenderable(self.app, self)
    
    def create_collision_shapes(self):
        # create different shapes based on collision type
        if self.collision_shape_type == CST_NONE:
            return
        elif self.collision_shape_type == CST_CIRCLE:
            self.col_shapes = [pymunk.Circle(self.col_body, self.col_radius, (self.col_offset_x, self.col_offset_y))]
        elif self.collision_shape_type == CST_AABB:
            self.col_shapes = self.get_box_segs()
        elif self.collision_shape_type == CST_TILE:
            self.col_shapes = self.get_tile_segs()
        # always add shapes to world space, even if they're part of rogue bodies
        for shape in self.col_shapes:
            shape.gobj = self
            shape.collision_type = self.collision_type
            self.world.space.add(shape)
    
    def destroy_collision_shapes(self):
        # it would be simpler to check for CST_NONE here, but that would miss
        # objects with collision that's temporarily disabled!
        if len(self.col_shapes) > 0:
            for shape in self.col_shapes:
                self.world.space.remove(shape)
        self.col_shapes = []
    
    def get_box_segs(self):
        left = self.col_box_left_x + self.col_offset_x
        right = self.col_box_right_x + self.col_offset_x
        top = self.col_box_top_y + self.col_offset_y
        bottom = self.col_box_bottom_y + self.col_offset_y
        left_shape = self.get_seg(left, top, left, bottom)
        right_shape = self.get_seg(right, top, right, bottom)
        top_shape = self.get_seg(left, top, right, top)
        bottom_shape = self.get_seg(left, bottom, right, bottom)
        return [left_shape, right_shape, top_shape, bottom_shape]
    
    def get_seg(self, x1, y1, x2, y2):
        return pymunk.Segment(self.col_body, (x1, y1), (x2, y2), self.seg_thickness)
    
    def get_tile_segs(self):
        segs = []
        frame = self.renderable.frame
        if not self.col_layer_name in self.art.layer_names:
            self.app.log("%s: Couldn't find collision layer with name '%s'" % (self.name, self.col_layer_name))
            return []
        layer = self.art.layer_names.index(self.col_layer_name)
        def is_dir_empty(x, y):
            return self.art.get_char_index_at(frame, layer, x, y) == 0
        for y in range(self.art.height):
            for x in range(self.art.width):
                if is_dir_empty(x, y):
                    continue
                left = (x * self.art.quad_width) - (self.renderable.width * self.art_off_pct_x)
                right = left + self.art.quad_width
                # TODO: railing in cronotest is offset, fix!
                top = (self.renderable.height * self.art_off_pct_y) - (y * self.art.quad_height)
                bottom = top - self.art.quad_height
                # only create segs for 0/>0 tile boundaries
                # empty space to left = left seg
                if x == 0 or is_dir_empty(x-1, y):
                    segs += [self.get_seg(left, top, left, bottom)]
                if x == self.art.width - 1 or is_dir_empty(x+1, y):
                    segs += [self.get_seg(right, top, right, bottom)]
                if y == 0 or is_dir_empty(x, y-1):
                    segs += [self.get_seg(left, top, right, top)]
                if y == self.art.height - 1 or is_dir_empty(x, y+1):
                    segs += [self.get_seg(left, bottom, right, bottom)]
        return segs
    
    def is_dynamic(self):
        return self.collision_type in CTG_DYNAMIC
    
    def is_point_inside(self, x, y):
        "returns True if given point is inside our bounds"
        min_x = self.x - (self.renderable.width * self.art_off_pct_x)
        max_x = self.x + (self.renderable.width * self.art_off_pct_x)
        min_y = self.y - (self.renderable.height * self.art_off_pct_y)
        max_y = self.y + (self.renderable.height * self.art_off_pct_y)
        return min_x <= x <= max_x and min_y <= y <= max_y
    
    def set_collision_type(self, new_type):
        self.collision_type = new_type
        for shape in self.col_shapes:
            shape.collision_type = self.collision_type
    
    def start_dragging(self):
        if self.collision_type != CT_NONE:
            self.disable_collision()
    
    def stop_dragging(self):
        if self.orig_collision_type is not None:
            self.enable_collision()
        # recreate shapes if stopping dragging a tile collision object
        if self.collision_shape_type == CST_TILE:
            self.destroy_collision_shapes()
            self.create_collision_shapes()
    
    def enable_collision(self):
        self.set_collision_type(self.orig_collision_type)
        self.orig_collision_type = None
    
    def disable_collision(self):
        self.orig_collision_type = self.collision_type
        self.set_collision_type(CT_NONE)
    
    def get_all_art(self):
        "returns a list of all Art used by this object"
        return [self.art]
    
    def start_animating(self):
        self.renderable.start_animating()
    
    def stop_animating(self):
        self.renderable.stop_animating()
    
    def set_art(self, new_art_filename):
        if self.art:
            old_art = self.art
        self.art = self.app.load_art(new_art_filename)
        if not self.art:
            self.art = old_art
            return
        self.renderable.set_art(self.art)
        self.bounds_renderable.art = self.art
    
    def set_loc(self, x, y, z=None):
        self.x, self.y = x, y
        self.z = z or 0
        if self.col_body and self.col_body is not self.world.space.static_body:
            self.col_body.position.x = self.x + self.col_offset_x
            self.col_body.position.y = self.y + self.col_offset_y
        if self.collision_shape_type == CST_TILE:
            self.destroy_collision_shapes()
            self.create_collision_shapes()
    
    def set_scale(self, x, y, z):
        self.scale_x, self.scale_y, self.scale_z = x, y, z
    
    def move(self, dx, dy):
        m = 1 + self.friction
        vel_dx = dx * self.move_accel_rate * m
        vel_dy = dy * self.move_accel_rate * m
        # TODO: account for friction so max rate is actually max rate
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
        # update physics: shape's surface velocity, body's position
        if self.collision_shape_type != CST_NONE and self.col_shapes and self.col_body:
            self.update_physics()
    
    def update_physics(self):
        # default behavior: object's location shadows that of its phy body
        #self.x, self.y = self.col_body.position.x, self.col_body.position.y
        self.col_body.position.x, self.col_body.position.y = self.x, self.y
    
    def update_renderables(self):
        # even if debug viz are off, update once on init to set correct state
        if self.show_origin or self in self.world.selected_objects:
            self.origin_renderable.update()
        if self.show_bounds or self in self.world.selected_objects:
            self.bounds_renderable.update()
        if self.collision_renderable and self.show_collision:
            self.collision_renderable.update()
        self.renderable.update()
    
    def render_debug(self):
        if self.show_origin or self in self.world.selected_objects:
            self.origin_renderable.render()
        if self.show_bounds or self in self.world.selected_objects:
            self.bounds_renderable.render()
        if self.show_collision and self.collision_renderable:
            self.collision_renderable.render()
    
    def render(self, layer, z_override=None):
        #print('GameObject %s layer %s has Z %s' % (self.art.filename, layer, self.art.layers_z[layer]))
        self.renderable.render(layer, z_override)
    
    def get_state_dict(self):
        "return a dict that GameWorld.save_state_to_file can save as JSON"
        d = {
            'class_name': type(self).__name__,
            'module_name': type(self).__module__,
        }
        if self is self.world.player:
            d['is_player'] = True
        # serialize whatever other vars are declared in self.serialized
        for prop_name in self.serialized:
            if hasattr(self, prop_name):
                d[prop_name] = getattr(self, prop_name)
        return d
    
    def reset_in_place(self):
        self.world.reset_object_in_place(self)
    
    def destroy(self):
        self.world.objects.remove(self)
        if self in self.world.selected_objects:
            self.world.selected_objects.remove(self)
        self.world.renderables.remove(self.renderable)
        self.origin_renderable.destroy()
        self.bounds_renderable.destroy()
        if self.collision_renderable:
            self.collision_renderable.destroy()
        if len(self.col_shapes) > 0:
            for shape in self.col_shapes:
                self.world.space.remove(shape)
        if self.col_body:
            #self.world.space.remove(self.col_body)
            pass
        self.renderable.destroy()


class StaticTileBG(GameObject):
    collision_shape_type = CST_TILE
    collision_type = CT_GENERIC_STATIC

class StaticTileObject(GameObject):
    collision_shape_type = CST_TILE
    collision_type = CT_GENERIC_STATIC
    y_sort = True

class StaticBoxObject(GameObject):
    collision_shape_type = CST_AABB
    collision_type = CT_GENERIC_STATIC

class DynamicBoxObject(GameObject):
    collision_shape_type = CST_AABB
    collision_type = CT_GENERIC_DYNAMIC
    y_sort = True

class Pickup(GameObject):
    collision_shape_type = CST_CIRCLE
    collision_type = CT_GENERIC_DYNAMIC
    y_sort = True

class Player(GameObject):
    
    y_sort = True
    move_accel_rate = 0.1
    max_move_speed = 0.8
    friction = 0.25
    log_move = True
    collision_shape_type = CST_CIRCLE
    collision_type = CT_PLAYER
    
    def update_physics(self):
        for shape in self.col_shapes:
            #shape.surface_velocity = self.vel_x, self.vel_y
            #print(shape.surface_velocity)
            #shape.position.x = self.x + self.col_offset_x
            #shape.position.y = self.y + self.col_offset_y
            pass
        #self.col_body.velocity = self.vel_x * 50, self.vel_y * 50
        self.col_body.position.x, self.col_body.position.y = self.x, self.y
        #self.x, self.y = self.col_body.position.x, self.col_body.position.y


class NSEWPlayer(Player):
    
    "top-down player character that can face & travel in 4 directions"
    
    anim_stand_base = 'stand'
    anim_walk_base = 'walk'
    anim_forward_base = 'fwd'
    anim_back_base = 'back'
    anim_right_base = 'right'
    
    def __init__(self, world, obj_data=None):
        # load animations
        stand_fwd_anim_name = '%s_%s_%s' % (self.art_src, self.anim_stand_base,
                                            self.anim_forward_base)
        stand_back_anim_name = '%s_%s_%s' % (self.art_src, self.anim_stand_base,
                                             self.anim_back_base)
        stand_right_anim_name = '%s_%s_%s' % (self.art_src, self.anim_stand_base,
                                              self.anim_right_base)
        walk_fwd_anim_name = '%s_%s_%s' % (self.art_src, self.anim_walk_base,
                                           self.anim_forward_base)
        walk_back_anim_name = '%s_%s_%s' % (self.art_src, self.anim_walk_base,
                                            self.anim_back_base)
        walk_right_anim_name = '%s_%s_%s' % (self.art_src, self.anim_walk_base,
                                             self.anim_right_base)
        self.anim_stand_fwd = world.app.load_art(stand_fwd_anim_name)
        self.anim_stand_back = world.app.load_art(stand_back_anim_name)
        self.anim_stand_right = world.app.load_art(stand_right_anim_name)
        self.anim_walk_fwd = world.app.load_art(walk_fwd_anim_name)
        self.anim_walk_back = world.app.load_art(walk_back_anim_name)
        self.anim_walk_right = world.app.load_art(walk_right_anim_name)
        self.last_move_dir = (0, 0)
        # provide valid art_src so rest of init doesn't get confused
        self.art_src = stand_fwd_anim_name
        Player.__init__(self, world, obj_data)
    
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
        Player.update(self)
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
