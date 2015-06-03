import os

from art import Art
from renderable import TileRenderable
from renderable_line import OriginIndicatorRenderable, BoundsIndicatorRenderable

from collision import Collideable, CST_NONE, CST_CIRCLE, CST_AABB, CST_TILE, CT_NONE, CT_GENERIC_STATIC, CT_GENERIC_DYNAMIC, CT_PLAYER, CTG_STATIC, CTG_DYNAMIC

class GameObject:
    
    # if specified, this art will be loaded from disk
    art_src = None
    # if generate_art is True, blank art will be created with these
    # dimensions, charset, and palette
    generate_art = False
    art_width, art_height = 8, 8
    art_charset, art_palette = None, None
    # Y-sort: if true, object will sort according to its Y position
    y_sort = False
    move_accel_rate = 0.01
    # normal movement will accelerate up to this, final velocity is uncapped
    max_move_speed = 0.4
    friction = 0.1
    # inverse mass: 0 = infinitely dense
    inv_mass = 1
    log_move = False
    log_load = False
    log_spawn = False
    visible = True
    # location is protected from edit mode drags
    location_locked = False
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
    col_offset_x, col_offset_y = 0., 0.
    col_radius = 1
    # AABB top left / bottom right coordinates
    col_box_left_x, col_box_right_x = -1, 1
    col_box_top_y, col_box_bottom_y = -1, 1
    # art offset from pivot: renderable's origin_pct set to this if !None
    # 0,0 = top left; 1,1 = bottom right; 0.5,0.5 = center
    art_off_pct_x, art_off_pct_y = 0.5, 0.5
    # list of members to serialize (no weak refs!)
    serialized = ['x', 'y', 'z', 'art_src', 'visible', 'location_locked',
                  'y_sort', 'art_off_pct_x', 'art_off_pct_y']
    # if setting a given property should run some logic, specify method here
    set_methods = {'art_src': 'set_art'}
    
    def __init__(self, world, obj_data=None):
        self.x, self.y, self.z = 0., 0., 0.
        # apply serialized data before most of init happens
        # properties that need non-None defaults should be declared above
        for v in self.serialized:
            if not hasattr(self, v):
                if self.log_load:
                    self.app.dev_log("Unknown serialized property '%s' for %s" % (v, self.name))
                continue
            elif not v in obj_data:
                if self.log_load:
                    self.app.dev_log("Serialized property '%s' not found for %s" % (v, self.name))
                continue
            # match type of variable as declared, eg loc might be written as
            # an int in the JSON so preserve its floatness
            if getattr(self, v) is not None:
                src_type = type(getattr(self, v))
                setattr(self, v, src_type(obj_data[v]))
            else:
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
        if self.generate_art:
            self.art_src = '%s_art' % self.name
            self.art = self.app.new_art(self.art_src, self.art_width,
                                        self.art_height, self.art_charset,
                                        self.art_palette)
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
        self.collision = Collideable(self)
        self.world.objects.append(self)
        if self.log_spawn:
            self.app.log('Spawned %s with Art %s' % (self.name, os.path.basename(self.art.filename)))
    
    def is_point_inside(self, x, y):
        "returns True if given point is inside our bounds"
        min_x = self.x - (self.renderable.width * self.art_off_pct_x)
        max_x = self.x + (self.renderable.width * self.art_off_pct_x)
        min_y = self.y - (self.renderable.height * self.art_off_pct_y)
        max_y = self.y + (self.renderable.height * self.art_off_pct_y)
        return min_x <= x <= max_x and min_y <= y <= max_y
    
    def is_dynamic(self):
        return self.collision_type in CTG_DYNAMIC
    
    def start_dragging(self):
        # TODO: disable collision, remember prior collision type
        pass
    
    def stop_dragging(self):
        # TODO: re-enable collision
        pass
    
    def enable_collision(self):
        # TODO
        pass
    
    def disable_collision(self):
        # TODO
        pass
    
    def get_all_art(self):
        "returns a list of all Art used by this object"
        return [self.art]
    
    def start_animating(self):
        self.renderable.start_animating()
    
    def stop_animating(self):
        self.renderable.stop_animating()
    
    def set_object_property(self, prop_name, new_value):
        if not hasattr(self, prop_name):
            return
        if prop_name in self.set_methods:
            method = getattr(self, self.set_methods[prop_name])
            method(new_value)
        else:
            setattr(self, prop_name, new_value)
    
    def set_art(self, new_art_filename):
        if self.art:
            old_art = self.art
        self.art = self.app.load_art(new_art_filename)
        if not self.art:
            self.art = old_art
            return
        self.art_src = new_art_filename
        self.renderable.set_art(self.art)
        self.bounds_renderable.art = self.art
    
    def set_loc(self, x, y, z=None):
        self.x, self.y = x, y
        self.z = z or 0
        # TODO: tell collision to update its loc
        # TODO: if collision is tile-based, rebuild shapes based on tiles
        # (assuming it doesn't move dynamically)
    
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
    
    def update_move(self):
        # apply friction and move
        if self.vel_x == 0 and self.vel_y == 0 and self.vel_z == 0:
            return
        self.vel_x *= 1 - self.friction
        self.vel_y *= 1 - self.friction
        self.vel_z *= 1 - self.friction
        self.x += self.vel_x
        self.y += self.vel_y
        self.z += self.vel_z
        if self.log_move:
            debug = ['%s velocity: %.4f, %.4f' % (self.name, self.vel_x, self.vel_y)]
            self.app.ui.debug_text.post_lines(debug)
    
    def update(self):
        if not self.art.updated_this_tick:
            self.art.update()
        self.last_x, self.last_y, self.last_z = self.x, self.y, self.z
        self.update_move()
        # update collision shape before CollisionLord resolves any collisions
        self.collision.update()
    
    def update_renderables(self):
        # even if debug viz are off, update once on init to set correct state
        if self.show_origin or self in self.world.selected_objects:
            self.origin_renderable.update()
        if self.show_bounds or self in self.world.selected_objects:
            self.bounds_renderable.update()
        if self.show_collision and self.is_dynamic():
            self.collision.update_renderables()
        self.renderable.update()
    
    def render_debug(self):
        if self.show_origin or self in self.world.selected_objects:
            self.origin_renderable.render()
        if self.show_bounds or self in self.world.selected_objects:
            self.bounds_renderable.render()
        if self.show_collision:
            self.collision.render()
    
    def render(self, layer, z_override=None):
        #print('GameObject %s layer %s has Z %s' % (self.art.filename, layer, self.art.layers_z[layer]))
        self.renderable.render(layer, z_override)
    
    def get_state_dict(self):
        "return a dict that GameWorld.save_state_to_file can dump to JSON"
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
        self.collision.destroy()
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
    inv_mass = 0
    log_move = True
    collision_shape_type = CST_CIRCLE
    collision_type = CT_PLAYER


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
