import math

from renderable import TileRenderable
from renderable_line import CircleCollisionRenderable, TileCircleCollisionRenderable

# collision shape types
CST_NONE = 0
CST_CIRCLE = 1
CST_AABB = 2
CST_TILE = 3

# collision types
CT_NONE = 0
CT_PLAYER = 1
CT_GENERIC_STATIC = 2
CT_GENERIC_DYNAMIC = 3

# collision type groups, eg static and dynamic
CTG_STATIC = [CT_GENERIC_STATIC]
CTG_DYNAMIC = [CT_GENERIC_DYNAMIC, CT_PLAYER]


class CircleCollisionShape:
    def __init__(self, loc_x, loc_y, radius, gobj):
        self.x, self.y = loc_x, loc_y
        self.radius = radius
        self.game_object = gobj
        self.inv_mass = self.game_object.inv_mass

class AxisAlignedRoundedRectangle:
    # AAAARRRR matey
    # TODO: AARR-on-AARR collision detection and resolution!
    def __init__(self, loc_x, loc_y, radius, halfwidth_x, halfwidth_y, gobj):
        self.x, self.y = loc_x, loc_y
        self.radius = radius
        self.halfwidth_x, self.halfwidth_y = halfwidth_x, halfwidth_y
        self.game_object = gobj
        self.inv_mass = self.game_object.inv_mass

class Collideable:
    
    # use game object's art_off_pct values
    use_art_offset = False
    
    def __init__(self, obj):
        self.game_object = obj
        self.cl = self.game_object.world.cl
        self.renderables, self.shapes = [], []
        # contacts with other objects
        self.contacts = {}
        # list of objects processed for collision this frame
        self.collisions_this_frame = []
        self.create_shapes()
    
    def create_shapes(self):
        self.clear_shapes()
        if self.game_object.collision_shape_type == CST_NONE:
            return
        elif self.game_object.collision_shape_type == CST_CIRCLE:
            self.create_circle()
        elif self.game_object.collision_shape_type == CST_TILE:
            self.create_tiles()
        # TODO: AARR creation
        # update renderables once if static
        if not self.game_object.is_dynamic():
            self.update_renderables()
    
    def clear_shapes(self):
        for r in self.renderables:
            r.destroy()
        self.renderables = []
        for shape in self.shapes:
            self.cl.remove_shape(shape)
        self.shapes = []
    
    def create_circle(self):
        x = self.game_object.x + self.game_object.col_offset_x
        y = self.game_object.y + self.game_object.col_offset_y
        shape = self.cl.add_circle_shape(x, y, self.game_object.col_radius,
                                         self.game_object)
        self.shapes = [shape]
        self.renderables = [CircleCollisionRenderable(shape)]
    
    def create_tiles(self):
        # fill shapes list with one circle for each solid tile
        obj = self.game_object
        frame = obj.renderable.frame
        if not obj.col_layer_name in obj.art.layer_names:
            obj.app.dev_log("%s: Couldn't find collision layer with name '%s'" % (obj.name, obj.col_layer_name))
            return
        layer = obj.art.layer_names.index(obj.col_layer_name)
        # for this circle version, no support for non-square tiles - largest
        # dimension will be used; better to have padding than gaps
        radius = max(obj.art.quad_width, obj.art.quad_height) / 2
        for y in range(obj.art.height):
            for x in range(obj.art.width):
                if obj.art.get_char_index_at(frame, layer, x, y) == 0:
                    continue
                # get world space coordinates of this tile's center
                wx = (x * obj.art.quad_width) + (0.5 * obj.art.quad_width)
                wx += obj.x - (obj.renderable.width * obj.art_off_pct_x)
                wy = (y * -obj.art.quad_height) - (0.5 * obj.art.quad_height)
                wy -= -obj.y - (obj.renderable.height * obj.art_off_pct_y)
                shape = self.cl.add_circle_shape(wx, wy, radius, obj)
                self.shapes.append(shape)
                r = TileCircleCollisionRenderable(shape)
                # update renderable once to set location correctly
                r.update()
                self.renderables.append(r)
    
    def update(self):
        if self.game_object and self.game_object.is_dynamic():
            self.update_transform_from_object()
    
    def update_transform_from_object(self, obj=None):
        obj = obj or self.game_object
        # CST_TILE shouldn't run here, it's static-only
        if obj.collision_shape_type == CST_CIRCLE:
            for shape in self.shapes:
                shape.x = obj.x + obj.col_offset_x
                shape.y = obj.y + obj.col_offset_y
    
    def update_renderables(self):
        for r in self.renderables:
            r.update()
    
    def render(self):
        for r in self.renderables:
            r.render()
    
    def destroy(self):
        for r in self.renderables:
            r.destroy()
        # remove our shapes from CollisionLord's shape list
        for shape in self.shapes:
            self.cl.remove_shape(shape)


class CollisionLord:
    
    def __init__(self, world):
        self.world = world
        self.ticks = 0
        self.reset()
    
    def report(self):
        print('%s: %s dynamic shapes, %s static shapes' % (self,
                                                           len(self.dynamic_shapes),
                                                           len(self.static_shapes)))
    
    def reset(self):
        self.dynamic_shapes, self.static_shapes = [], []
    
    def add_circle_shape(self, x, y, radius, gobj):
        shape = CircleCollisionShape(x, y, radius, gobj)
        if gobj.is_dynamic():
            self.dynamic_shapes.append(shape)
        else:
            self.static_shapes.append(shape)
        return shape
    
    def remove_shape(self, shape):
        if shape in self.dynamic_shapes:
            self.dynamic_shapes.remove(shape)
        elif shape in self.static_shapes:
            self.static_shapes.remove(shape)
    
    def resolve_overlaps(self):
        iterations = 5
        for i in range(iterations):
            # push all dynamic circles out of each other
            for a in self.dynamic_shapes:
                if a.game_object.collision_type == CT_NONE:
                    continue
                for b in self.dynamic_shapes:
                    if b.game_object.collision_type == CT_NONE:
                        continue
                    if a is b:
                        continue
                    # TODO: handle different shape type combinations
                    collide_circles(a, b)
            # now push all dynamic circles out of all static circles
            for a in self.dynamic_shapes:
                if a.game_object.collision_type == CT_NONE:
                    continue
                for b in self.static_shapes:
                    if b.game_object.collision_type == CT_NONE:
                        continue
                    collide_circles(a, b)
        # check which objects stopped colliding
        for obj in self.world.objects.values():
            obj.check_finished_contacts()
        self.ticks += 1
        self.collisions_this_frame = []
    
    def resolve_momentum(self, obj_a, obj_b):
        # don't resolve a pair twice
        if obj_a in self.collisions_this_frame:
            return
        # determine new direction and velocity
        total_vel = obj_a.vel_x + obj_a.vel_y + obj_b.vel_x + obj_b.vel_y
        total_mass = obj_a.inv_mass + obj_b.inv_mass
        if obj_b.name not in obj_a.collision.contacts or \
           obj_a.name not in obj_b.collision.contacts:
            return
        # redistribute velocity based on mass we're colliding with
        if obj_a.is_dynamic():
            ax, ay = obj_a.collision.contacts[obj_b.name][:2]
            a_vel = total_vel * (obj_a.inv_mass / total_mass)
            a_vel *= obj_a.bounciness
            obj_a.vel_x, obj_a.vel_y = -ax * a_vel, -ay * a_vel
        if obj_b.is_dynamic():
            bx, by = obj_b.collision.contacts[obj_a.name][:2]
            b_vel = total_vel * (obj_b.inv_mass / total_mass)
            b_vel *= obj_b.bounciness
            obj_b.vel_x, obj_b.vel_y = -bx * b_vel, -by * b_vel
        # mark objects as resolved
        self.collisions_this_frame.append(obj_a)
        self.collisions_this_frame.append(obj_b)


def point_circle_penetration(point_x, point_y, circle_x, circle_y, radius):
    "returns normalized penetration x, y, and distance"
    dx, dy = circle_x - point_x, circle_y - point_y
    pdist = math.sqrt(dx ** 2 + dy ** 2)
    # point is center of circle, arbitrarily project out in +X
    if pdist == 0:
        return 1, 0, -radius
    return dx / pdist, dy / pdist, pdist - radius

def collide_circles(a, b):
    "resolves collision between two CircleCollisionShapes"
    dx, dy, pdist = point_circle_penetration(a.x, a.y, b.x, b.y,
                                             a.radius + b.radius)
    if pdist < 0:
        obj_a, obj_b = a.game_object, b.game_object
        # tell objects they're overlapping, pass penetration vector
        a_coll_b = obj_a.overlapped(obj_b, dx, dy)
        shoulds = ["shouldn't", 'should']
        #print('%s %s collide with %s' % (obj_a.name, shoulds[a_coll_b], obj_b.name))
        b_coll_a = obj_b.overlapped(obj_a, dx, dy)
        #print('%s %s collide with %s' % (obj_b.name, shoulds[b_coll_a], obj_a.name))
        # if either object says it shouldn't collide with other, don't
        if not a_coll_b or not b_coll_a:
            return
        total_mass = obj_a.inv_mass + obj_b.inv_mass
        if obj_a.is_dynamic():
            if not obj_b.is_dynamic():
                a_push = pdist
            else:
                a_push = (a.inv_mass / total_mass) * pdist
            # move parent object, not shape
            obj_a.x += a_push * dx
            obj_a.y += a_push * dy
            # update all shapes based on object's new position
            obj_a.collision.update_transform_from_object()
        if obj_b.is_dynamic():
            if not obj_a.is_dynamic():
                b_push = pdist
            else:
                b_push = (b.inv_mass / total_mass) * pdist
            obj_b.x -= b_push * dx
            obj_b.y -= b_push * dy
            obj_b.collision.update_transform_from_object()
