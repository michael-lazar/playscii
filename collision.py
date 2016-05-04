import math

from renderable import TileRenderable
from renderable_line import CircleCollisionRenderable, BoxCollisionRenderable, TileBoxCollisionRenderable

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
        self.mass = self.game_object.mass
    
    def get_box(self):
        "returns coords of our bounds (left, top, right, bottom)"
        return self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius


class AABBCollisionShape:
    
    "Axis-Aligned Bounding Box"
    
    def __init__(self, loc_x, loc_y, halfwidth, halfheight, gobj):
        self.x, self.y = loc_x, loc_y
        self.halfwidth, self.halfheight = halfwidth, halfheight
        self.game_object = gobj
        self.mass = self.game_object.mass
    
    def get_box(self):
        return self.x - self.halfwidth, self.y - self.halfheight, self.x + self.halfwidth, self.y + self.halfheight


class Collideable:
    
    # use game object's art_off_pct values
    use_art_offset = False
    
    def __init__(self, obj):
        self.game_object = obj
        self.cl = self.game_object.world.cl
        self.renderables, self.shapes = [], []
        # dict of shapes accessible by (x,y) tile coordinates
        self.tile_shapes = {}
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
        elif self.game_object.collision_shape_type == CST_AABB:
            self.create_box()
        elif self.game_object.collision_shape_type == CST_TILE:
            self.create_merged_tile_boxes()
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
    
    def create_box(self):
        x = self.game_object.x# + self.game_object.col_offset_x
        y = self.game_object.y# + self.game_object.col_offset_y
        shape = self.cl.add_box_shape(x, y,
                                      self.game_object.col_width / 2,
                                      self.game_object.col_height / 2,
                                      self.game_object)
        self.shapes = [shape]
        self.renderables = [BoxCollisionRenderable(shape)]
    
    def create_merged_tile_boxes(self):
        "create AABB shapes for a CST_TILE object"
        # generate fewer, larger boxes!
        obj = self.game_object
        frame = obj.renderable.frame
        if not obj.col_layer_name in obj.art.layer_names:
            obj.app.dev_log("%s: Couldn't find collision layer with name '%s'" % (obj.name, obj.col_layer_name))
            return
        layer = obj.art.layer_names.index(obj.col_layer_name)
        # tile is available if it's not empty and not already covered by a shape
        def tile_available(tile_x, tile_y):
            return obj.art.get_char_index_at(frame, layer, tile_x, tile_y) != 0 and not (tile_x, tile_y) in self.tile_shapes
        def tile_range_available(start_x, end_x, start_y, end_y):
            for y in range(start_y, end_y + 1):
                for x in range(start_x, end_x + 1):
                    if not tile_available(x, y):
                        return False
            return True
        for y in range(obj.art.height):
            for x in range(obj.art.width):
                if not tile_available(x, y):
                    continue
                # determine how big we can make this box
                # first fill left to right
                end_x = x
                while end_x < obj.art.width - 1 and tile_available(end_x + 1, y):
                    end_x += 1
                # then fill top to bottom
                end_y = y
                while end_y < obj.art.height - 1 and tile_range_available(x, end_x, y, end_y + 1):
                    end_y += 1
                # compute origin and halfsizes of box covering tile range
                wx1, wy1 = obj.get_tile_loc(x, y, tile_center=True)
                wx2, wy2 = obj.get_tile_loc(end_x, end_y, tile_center=True)
                wx = (wx1 + wx2) / 2
                halfwidth = (end_x - x) * obj.art.quad_width
                halfwidth /= 2
                halfwidth += obj.art.quad_width / 2
                wy = (wy1 + wy2) / 2
                halfheight = (end_y - y) * obj.art.quad_height
                halfheight /= 2
                halfheight += obj.art.quad_height / 2
                shape = self.cl.add_box_shape(wx, wy, halfwidth, halfheight, obj)
                self.shapes.append(shape)
                # fill in cell(s) in tile collision dict
                for tile_y in range(y, end_y + 1):
                    for tile_x in range(x, end_x + 1):
                        self.tile_shapes[(tile_x, tile_y)] = shape
                r = TileBoxCollisionRenderable(shape)
                # update renderable once to set location correctly
                r.update()
                self.renderables.append(r)
    
    def create_tile_boxes(self):
        "create AABB shapes for each solid tile in a CST_TILE object"
        # fill shapes list with one box for each solid tile
        obj = self.game_object
        frame = obj.renderable.frame
        if not obj.col_layer_name in obj.art.layer_names:
            obj.app.dev_log("%s: Couldn't find collision layer with name '%s'" % (obj.name, obj.col_layer_name))
            return
        layer = obj.art.layer_names.index(obj.col_layer_name)
        for y in range(obj.art.height):
            for x in range(obj.art.width):
                if obj.art.get_char_index_at(frame, layer, x, y) == 0:
                    continue
                # get world space coordinates of this tile's center
                wx, wy = obj.get_tile_loc(x, y, tile_center=True)
                shape = self.cl.add_box_shape(wx, wy, obj.art.quad_width / 2,
                                              obj.art.quad_height / 2, obj)
                self.shapes.append(shape)
                self.tile_shapes[(x, y)] = shape
                r = TileBoxCollisionRenderable(shape)
                # update renderable once to set location correctly
                r.update()
                self.renderables.append(r)
    
    def get_shapes_overlapping_box(self, left, top, right, bottom):
        "returns a list of our shapes that overlap given box"
        shapes = []
        tiles = self.game_object.get_tiles_overlapping_box(left, top, right, bottom)
        for (x, y) in tiles:
            shape = self.tile_shapes.get((x, y), None)
            if shape:
                shapes.append(shape)
        return shapes
    
    def update(self):
        if self.game_object and self.game_object.is_dynamic():
            self.update_transform_from_object()
    
    def update_transform_from_object(self, obj=None):
        obj = obj or self.game_object
        # CST_TILE shouldn't run here, it's static-only
        if obj.collision_shape_type != CST_TILE:
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
    
    def add_box_shape(self, x, y, halfwidth, halfheight, gobj):
        shape = AABBCollisionShape(x, y, halfwidth, halfheight, gobj)
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
    
    def get_overlapping_static_shapes(self, shape):
        "returns a list of static shapes that overlap with given shape"
        overlapping_shapes = []
        shape_left, shape_top, shape_right, shape_bottom = shape.get_box()
        # add padding to overlapping tiles check
        if False:
            padding = 0.01
            shape_left -= padding
            shape_top -= padding
            shape_right += padding
            shape_bottom += padding
        for obj in self.world.objects.values():
            if obj is shape.game_object or not obj.should_collide() or obj.is_dynamic():
                continue
            # always check non-tile-based static shapes
            if obj.collision_shape_type != CST_TILE:
                overlapping_shapes += obj.collision.shapes
            else:
                # skip if even bounds don't overlap
                obj_left, obj_top, obj_right, obj_bottom = obj.get_edges()
                if not boxes_overlap(shape_left, shape_top, shape_right, shape_bottom,
                                     obj_left, obj_top, obj_right, obj_bottom):
                    continue
                overlapping_shapes += obj.collision.get_shapes_overlapping_box(shape_left, shape_top, shape_right, shape_bottom)
        return overlapping_shapes
    
    def resolve_overlaps(self):
        iterations = 5
        # filter shape lists for anything out of room etc
        valid_dynamic_shapes = []
        for shape in self.dynamic_shapes:
            if shape.game_object.should_collide():
                valid_dynamic_shapes.append(shape)
        for i in range(iterations):
            # track test pairs so we don't do B->A if we've already done A->B
            tests = {}
            # push all dynamic circles out of each other
            for a in valid_dynamic_shapes:
                # create list for objects this object has tested against
                if not a in tests:
                    tests[a] = []
                for b in valid_dynamic_shapes:
                    if a is b:
                        continue
                    if not b in tests:
                        tests[b] = []
                    # have these two objects already tested this iteration?
                    if a in tests[b] or b in tests[a]:
                        continue
                    # mark A->B as tested
                    tests[a].append(b)
                    # collide_shapes handles different shape type combinations
                    collide_shapes(a, b)
            # now push all dynamic circles out of all static circles
            for a in valid_dynamic_shapes:
                # check against list of static shapes pared down by broadphase
                for b in self.get_overlapping_static_shapes(a):
                    if not b in tests:
                        tests[b] = []
                    if a in tests[b] or b in tests[a]:
                        continue
                    tests[a].append(b)
                    collide_shapes(a, b)
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
        # negative mass = infinite
        total_mass = max(0, obj_a.mass) + max(0, obj_b.mass)
        if obj_b.name not in obj_a.collision.contacts or \
           obj_a.name not in obj_b.collision.contacts:
            return
        # redistribute velocity based on mass we're colliding with
        if obj_a.is_dynamic() and obj_a.mass >= 0:
            ax, ay = obj_a.collision.contacts[obj_b.name][:2]
            a_vel = total_vel * (obj_a.mass / total_mass)
            a_vel *= obj_a.bounciness
            obj_a.vel_x, obj_a.vel_y = -ax * a_vel, -ay * a_vel
        if obj_b.is_dynamic() and obj_b.mass >= 0:
            bx, by = obj_b.collision.contacts[obj_a.name][:2]
            b_vel = total_vel * (obj_b.mass / total_mass)
            b_vel *= obj_b.bounciness
            obj_b.vel_x, obj_b.vel_y = -bx * b_vel, -by * b_vel
        # mark objects as resolved
        self.collisions_this_frame.append(obj_a)
        self.collisions_this_frame.append(obj_b)

# collision handling

def point_in_box(x, y, box_left, box_top, box_right, box_bottom):
    return box_left <= x <= box_right and box_bottom <= y <= box_top

def boxes_overlap(left_a, top_a, right_a, bottom_a, left_b, top_b, right_b, bottom_b):
    for (x, y) in ((left_a, top_a), (right_a, top_a), (right_a, bottom_a), (left_a, bottom_a)):
        if left_b <= x <= right_b and bottom_b <= y <= top_b:
            return True
    return False

def point_circle_penetration(point_x, point_y, circle_x, circle_y, radius):
    "returns normalized penetration x, y, and distance"
    dx, dy = circle_x - point_x, circle_y - point_y
    pdist = math.sqrt(dx ** 2 + dy ** 2)
    # point is center of circle, arbitrarily project out in +X
    if pdist == 0:
        return 1, 0, -radius
    return dx / pdist, dy / pdist, pdist - radius

def box_penetration(ax, ay, bx, by, ahw, ahh, bhw, bhh):
    "returns penetration vector and magnitude for two boxes"
    left_a, right_a = ax - ahw, ax + ahw
    top_a, bottom_a = ay + ahh, ay - ahh
    left_b, right_b = bx - bhw, bx + bhw
    top_b, bottom_b = by + bhh, by - bhh
    # A to left or right of B?
    px = right_a - left_b if ax <= bx else right_b - left_a
    # A above or below B?
    py = top_b - bottom_a if ay >= by else top_a - bottom_b
    dx, dy = bx - ax, by - ay
    widths, heights = ahw + bhw, ahh + bhh
    # return separating axis + penetration depth
    if widths + px - abs(dx) < heights + py - abs(dy):
        if dx >= 0:
            return 1, 0, -px
        elif dx < 0:
            return -1, 0, -px
    else:
        if dy >= 0:
            return 0, 1, -py
        elif dy < 0:
            return 0, -1, -py
    return 1, 0, -px

def circle_box_penetration(circle_x, circle_y, box_x, box_y, circle_radius,
                           box_hw, box_hh):
    box_left, box_right = box_x - box_hw, box_x + box_hw
    box_top, box_bottom = box_y + box_hh, box_y - box_hh
    # if circle center inside box, use box-on-box penetration vector + distance
    if point_in_box(circle_x, circle_y, box_left, box_top, box_right, box_bottom):
        return box_penetration(circle_x, circle_y, box_x, box_y,
                               circle_radius, circle_radius, box_hw, box_hh)
    # find point on AABB edges closest to center of circle
    # clamp = min(highest, max(lowest, val))
    px = min(box_right, max(box_left, circle_x))
    py = min(box_top, max(box_bottom, circle_y))
    closest_x = circle_x - px
    closest_y = circle_y - py
    d = math.sqrt(closest_x ** 2 + closest_y ** 2)
    pdist = circle_radius - d
    if d == 0:
        return 1, 0, pdist
    return -closest_x / d, -closest_y / d, -pdist

def collide_shapes(a, b):
    "detect and resolve collision between two collision shapes"
    # handle all combinations of shape types
    if type(a) is CircleCollisionShape and type(b) is CircleCollisionShape:
        px, py, pdist = point_circle_penetration(a.x, a.y, b.x, b.y,
                                                 a.radius + b.radius)
    elif type(a) is AABBCollisionShape and type(b) is AABBCollisionShape:
        px, py, pdist = box_penetration(a.x, a.y, b.x, b.y,
                                        a.halfwidth, a.halfheight,
                                        b.halfwidth, b.halfheight)
    elif type(a) is CircleCollisionShape and type(b) is AABBCollisionShape:
        px, py, pdist = circle_box_penetration(a.x, a.y, b.x, b.y, a.radius,
                                               b.halfwidth, b.halfheight)
    elif type(a) is AABBCollisionShape and type(b) is CircleCollisionShape:
        px, py, pdist = circle_box_penetration(b.x, b.y, a.x, a.y, b.radius,
                                               a.halfwidth, a.halfheight)
        # reverse penetration result
        px, py = -px, -py
    else:
        a.game_object.app.log('Unhandled collision: %s on %s' % (a.game_object.name, b.game_object.name))
    if pdist >= 0:
        return
    obj_a, obj_b = a.game_object, b.game_object
    # tell objects they're overlapping, pass penetration vector
    a_coll_b = obj_a.overlapped(obj_b, px, py)
    b_coll_a = obj_b.overlapped(obj_a, px, py)
    # if either object says it shouldn't collide with other, don't
    if not a_coll_b or not b_coll_a:
        return
    total_mass = max(0, obj_a.mass) + max(0, obj_b.mass)
    if obj_a.is_dynamic():
        if not obj_b.is_dynamic() or obj_b.mass < 0:
            a_push = pdist
        else:
            a_push = (a.mass / total_mass) * pdist
        # move parent object, not shape
        obj_a.x += a_push * px
        obj_a.y += a_push * py
        # update all shapes based on object's new position
        obj_a.collision.update_transform_from_object()
    if obj_b.is_dynamic():
        if not obj_a.is_dynamic() or obj_a.mass < 0:
            b_push = pdist
        else:
            b_push = (b.mass / total_mass) * pdist
        obj_b.x -= b_push * px
        obj_b.y -= b_push * py
        obj_b.collision.update_transform_from_object()
