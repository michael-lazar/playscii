import math
from collections import namedtuple

from renderable import TileRenderable
from renderable_line import CircleCollisionRenderable, BoxCollisionRenderable, TileBoxCollisionRenderable

# collision shape types
CST_NONE = 0
"Don't use a CollisionShape"
CST_CIRCLE = 1
"Use a CircleCollisionShap"
CST_AABB = 2
"Use an AABBCollisionShape"
CST_TILE = 3
"""
Tile-based collision: generate multiple AABBCollisionShapes to approximate all
non-blank (character index 0) tiles of our GameObject's default Art's
"collision layer", whose string name is defined in GO.col_layer_name.
"""

# collision types
CT_NONE = 0
CT_PLAYER = 1
CT_GENERIC_STATIC = 2
CT_GENERIC_DYNAMIC = 3

# collision type groups, eg static and dynamic
CTG_STATIC = [CT_GENERIC_STATIC]
'"Collision type group", collections of CT_* values for more convenient checks.'
CTG_DYNAMIC = [CT_GENERIC_DYNAMIC, CT_PLAYER]
'"Collision type group", collections of CT_* values for more convenient checks.'

__pdoc__ = {}
# named tuples for collision structs that don't merit a class
Contact = namedtuple('Contact', ['overlap', 'timestamp'])
__pdoc__['Contact'] = "Represents a contact between two objects."

ShapeOverlap = namedtuple('ShapeOverlap', ['x', 'y', 'dist', 'area', 'other'])
__pdoc__['ShapeOverlap'] = "Represents a CollisionShape's overlap with another."


class CollisionShape:
    """
    Abstract class for a shape that can overlap and collide with other shapes.
    Shapes are part of a Collideable which in turn is part of a GameObject.
    """
    def resolve_overlaps_with_shapes(self, shapes):
        "Resolve this shape's overlap(s) with given list of shapes."
        overlaps = []
        for other in shapes:
            if other is self:
                continue
            overlap = self.get_overlap(other)
            if overlap.dist < 0:
                overlaps.append(overlap)
        if len(overlaps) == 0:
            return
        # resolve collisions in order of largest -> smallest overlap
        overlaps.sort(key=lambda item: item.area, reverse=True)
        for i,old_overlap in enumerate(overlaps):
            # resolve first overlap without recalculating
            overlap = self.get_overlap(old_overlap.other) if i > 0 else overlaps[0]
            self.resolve_overlap(overlap)
    
    def resolve_overlap(self, overlap):
        "Resolve this shape's given overlap."
        other = overlap.other
        # tell objects they're overlapping, pass penetration vector
        a_coll_b, a_started_b = self.go.overlapped(other.go, overlap)
        b_coll_a, b_started_a = other.go.overlapped(self.go, overlap)
        # if either object says it shouldn't collide with other, don't
        if not a_coll_b or not b_coll_a:
            return
        # push shapes apart according to mass
        total_mass = max(0, self.go.mass) + max(0, other.go.mass)
        if self.go.is_dynamic():
            if not other.go.is_dynamic() or other.go.mass < 0:
                a_push = overlap.dist
            else:
                a_push = (self.go.mass / total_mass) * overlap.dist
            # move parent object, not shape
            self.go.x += a_push * overlap.x
            self.go.y += a_push * overlap.y
            # update all shapes based on object's new position
            self.go.collision.update_transform_from_object()
        if other.go.is_dynamic():
            if not self.go.is_dynamic() or self.go.mass < 0:
                b_push = overlap.dist
            else:
                b_push = (other.go.mass / total_mass) * overlap.dist
            other.go.x -= b_push * overlap.x
            other.go.y -= b_push * overlap.y
            other.go.collision.update_transform_from_object()
        # call objs' started_colliding once collisions have been resolved
        world = self.go.world
        if a_started_b:
            world.try_object_method(self.go, self.go.started_colliding, [other.go])
        if b_started_a:
            world.try_object_method(other.go, other.go.started_colliding, [self.go])
    
    def get_overlapping_static_shapes(self):
        "Return a list of static shapes that overlap with this shape."
        overlapping_shapes = []
        shape_left, shape_top, shape_right, shape_bottom = self.get_box()
        # add padding to overlapping tiles check
        if False:
            padding = 0.01
            shape_left -= padding
            shape_top -= padding
            shape_right += padding
            shape_bottom += padding
        for obj in self.go.world.objects.values():
            if obj is self.go or not obj.should_collide() or obj.is_dynamic():
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


class CircleCollisionShape(CollisionShape):
    "CollisionShape using a circle area."
    def __init__(self, loc_x, loc_y, radius, game_object):
        self.x, self.y = loc_x, loc_y
        self.radius = radius
        self.go = game_object
    
    def get_box(self):
        "Return world coordinates of our bounds (left, top, right, bottom)"
        return self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius
    
    def is_point_inside(self, x, y):
        "Return True if given point is inside this shape."
        return (self.x - x) ** 2 + (self.y - y) ** 2 <= self.radius ** 2
    
    def overlaps_line(self, x1, y1, x2, y2):
        "Return True if this circle overlaps given line segment."
        return circle_overlaps_line(self.x, self.y, self.radius, x1, y1, x2, y2)
    
    def get_overlap(self, other):
        "Return ShapeOverlap data for this shape's overlap with given other."
        if type(other) is CircleCollisionShape:
            px, py, pdist1, pdist2 = point_circle_penetration(self.x, self.y,
                                                     other.x, other.y,
                                                     self.radius + other.radius)
        elif type(other) is AABBCollisionShape:
            px, py, pdist1, pdist2 = circle_box_penetration(self.x, self.y,
                                                   other.x, other.y,
                                                   self.radius, other.halfwidth,
                                                   other.halfheight)
        area = abs(pdist1 * pdist2) if pdist1 < 0 else 0
        return ShapeOverlap(x=px, y=py, dist=pdist1, area=area, other=other)


class AABBCollisionShape(CollisionShape):
    "CollisionShape using an axis-aligned bounding box area."
    def __init__(self, loc_x, loc_y, halfwidth, halfheight, game_object):
        self.x, self.y = loc_x, loc_y
        self.halfwidth, self.halfheight = halfwidth, halfheight
        self.go = game_object
        # for CST_TILE objects, lists of tile(s) we cover
        self.tiles = []
    
    def get_box(self):
        return self.x - self.halfwidth, self.y - self.halfheight, self.x + self.halfwidth, self.y + self.halfheight
    
    def is_point_inside(self, x, y):
        "Return True if given point is inside this shape."
        return point_in_box(x, y, *self.get_box())
    
    def overlaps_line(self, x1, y1, x2, y2):
        "Return True if this box overlaps given line segment."
        left, top, right, bottom = self.get_box()
        return box_overlaps_line(left, top, right, bottom, x1, y1, x2, y2)
    
    def get_overlap(self, other):
        "Return ShapeOverlap data for this shape's overlap with given other."
        if type(other) is AABBCollisionShape:
            px, py, pdist1, pdist2 = box_penetration(self.x, self.y,
                                                     other.x, other.y,
                                            self.halfwidth, self.halfheight,
                                            other.halfwidth, other.halfheight)
        elif type(other) is CircleCollisionShape:
            px, py, pdist1, pdist2 = circle_box_penetration(other.x, other.y,
                                                   self.x, self.y,
                                                   other.radius, self.halfwidth,
                                                   self.halfheight)
            # reverse result if we're shape B
            px, py = -px, -py
        area = abs(pdist1 * pdist2) if pdist1 < 0 else 0
        return ShapeOverlap(x=px, y=py, dist=pdist1, area=area, other=other)


class Collideable:
    "Collision component for GameObjects. Contains a list of shapes."
    use_art_offset = False
    "use game object's art_off_pct values"
    def __init__(self, obj):
        "Create new Collideable for given GameObject."
        self.go = obj
        self.cl = self.go.world.cl
        self.renderables, self.shapes = [], []
        self.tile_shapes = {}
        "Dict of shapes accessible by (x,y) tile coordinates"
        self.contacts = {}
        "Dict of contacts with other objects, by object name"
        self.create_shapes()
    
    def create_shapes(self):
        """
        Create collision shape(s) appropriate to our game object's
        collision_shape_type value.
        """
        self._clear_shapes()
        if self.go.collision_shape_type == CST_NONE:
            return
        elif self.go.collision_shape_type == CST_CIRCLE:
            self._create_circle()
        elif self.go.collision_shape_type == CST_AABB:
            self._create_box()
        elif self.go.collision_shape_type == CST_TILE:
            self.tile_shapes.clear()
            self._create_merged_tile_boxes()
        # update renderables once if static
        if not self.go.is_dynamic():
            self.update_renderables()
    
    def _clear_shapes(self):
        for r in self.renderables:
            r.destroy()
        self.renderables = []
        for shape in self.shapes:
            self.cl._remove_shape(shape)
        self.shapes = []
        "List of CollisionShapes"
    
    def _create_circle(self):
        x = self.go.x + self.go.col_offset_x
        y = self.go.y + self.go.col_offset_y
        shape = self.cl._add_circle_shape(x, y, self.go.col_radius, self.go)
        self.shapes = [shape]
        self.renderables = [CircleCollisionRenderable(shape)]
    
    def _create_box(self):
        x = self.go.x # + self.go.col_offset_x
        y = self.go.y # + self.go.col_offset_y
        shape = self.cl._add_box_shape(x, y,
                                      self.go.col_width / 2,
                                      self.go.col_height / 2,
                                      self.go)
        self.shapes = [shape]
        self.renderables = [BoxCollisionRenderable(shape)]
    
    def _create_merged_tile_boxes(self):
        "Create AABB shapes for a CST_TILE object"
        # generate fewer, larger boxes!
        frame = self.go.renderable.frame
        if not self.go.col_layer_name in self.go.art.layer_names:
            self.go.app.dev_log("%s: Couldn't find collision layer with name '%s'" % (self.go.name, self.go.col_layer_name))
            return
        layer = self.go.art.layer_names.index(self.go.col_layer_name)
        # tile is available if it's not empty and not already covered by a shape
        def tile_available(tile_x, tile_y):
            return self.go.art.get_char_index_at(frame, layer, tile_x, tile_y) != 0 and not (tile_x, tile_y) in self.tile_shapes
        def tile_range_available(start_x, end_x, start_y, end_y):
            for y in range(start_y, end_y + 1):
                for x in range(start_x, end_x + 1):
                    if not tile_available(x, y):
                        return False
            return True
        for y in range(self.go.art.height):
            for x in range(self.go.art.width):
                if not tile_available(x, y):
                    continue
                # determine how big we can make this box
                # first fill left to right
                end_x = x
                while end_x < self.go.art.width - 1 and tile_available(end_x + 1, y):
                    end_x += 1
                # then fill top to bottom
                end_y = y
                while end_y < self.go.art.height - 1 and tile_range_available(x, end_x, y, end_y + 1):
                    end_y += 1
                # compute origin and halfsizes of box covering tile range
                wx1, wy1 = self.go.get_tile_loc(x, y, tile_center=True)
                wx2, wy2 = self.go.get_tile_loc(end_x, end_y, tile_center=True)
                wx = (wx1 + wx2) / 2
                halfwidth = (end_x - x) * self.go.art.quad_width
                halfwidth /= 2
                halfwidth += self.go.art.quad_width / 2
                wy = (wy1 + wy2) / 2
                halfheight = (end_y - y) * self.go.art.quad_height
                halfheight /= 2
                halfheight += self.go.art.quad_height / 2
                shape = self.cl._add_box_shape(wx, wy, halfwidth, halfheight,
                                               self.go)
                # fill in cell(s) in our tile collision dict,
                # write list of tiles shape covers to shape.tiles
                for tile_y in range(y, end_y + 1):
                    for tile_x in range(x, end_x + 1):
                        self.tile_shapes[(tile_x, tile_y)] = shape
                        shape.tiles.append((tile_x, tile_y))
                r = TileBoxCollisionRenderable(shape)
                # update renderable once to set location correctly
                r.update()
                self.shapes.append(shape)
                self.renderables.append(r)
    
    def get_shape_overlapping_point(self, x, y):
        "Return shape if it's overlapping given point, None if no overlap."
        tile_x, tile_y = self.go.get_tile_at_point(x, y)
        return self.tile_shapes.get((tile_x, tile_y), None)
    
    def get_shapes_overlapping_box(self, left, top, right, bottom):
        "Return a list of our shapes that overlap given box."
        shapes = []
        tiles = self.go.get_tiles_overlapping_box(left, top, right, bottom)
        for (x, y) in tiles:
            shape = self.tile_shapes.get((x, y), None)
            if shape and not shape in shapes:
                shapes.append(shape)
        return shapes
    
    def update(self):
        if self.go and self.go.is_dynamic():
            self.update_transform_from_object()
    
    def update_transform_from_object(self, obj=None):
        "Snap our shapes to location of given object (if unspecified, our GO)."
        obj = obj or self.go
        # CST_TILE shouldn't run here, it's static-only
        if obj.collision_shape_type == CST_TILE:
            return
        for shape in self.shapes:
            shape.x = obj.x + obj.col_offset_x
            shape.y = obj.y + obj.col_offset_y
    
    def set_shape_color(self, shape, new_color):
        "Set the color of a given shape's debug LineRenderable."
        try:
            shape_index = self.shapes.index(shape)
        except ValueError:
            return
        self.renderables[shape_index].color = new_color
        self.renderables[shape_index].build_geo()
        self.renderables[shape_index].rebind_buffers()
    
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
            self.cl._remove_shape(shape)


class CollisionLord:
    """
    Collision manager object, tracks Collideables, detects overlaps and
    resolves collisions.
    """
    iterations = 7
    """
    Number of times to resolve collisions per update. Lower at own risk;
    multi-object collisions require multiple iterations to settle correctly.
    """
    def __init__(self, world):
        self.world = world
        self.ticks = 0
        # list of objects processed for collision this frame
        self.collisions_this_frame = []
        self.reset()
    
    def report(self):
        print('%s: %s dynamic shapes, %s static shapes' % (self,
                                                           len(self.dynamic_shapes),
                                                           len(self.static_shapes)))
    
    def reset(self):
        self.dynamic_shapes, self.static_shapes = [], []
    
    def _add_circle_shape(self, x, y, radius, game_object):
        shape = CircleCollisionShape(x, y, radius, game_object)
        if game_object.is_dynamic():
            self.dynamic_shapes.append(shape)
        else:
            self.static_shapes.append(shape)
        return shape
    
    def _add_box_shape(self, x, y, halfwidth, halfheight, game_object):
        shape = AABBCollisionShape(x, y, halfwidth, halfheight, game_object)
        if game_object.is_dynamic():
            self.dynamic_shapes.append(shape)
        else:
            self.static_shapes.append(shape)
        return shape
    
    def _remove_shape(self, shape):
        if shape in self.dynamic_shapes:
            self.dynamic_shapes.remove(shape)
        elif shape in self.static_shapes:
            self.static_shapes.remove(shape)
    
    def update(self):
        "Resolve overlaps between all relevant world objects."
        for i in range(self.iterations):
            # filter shape lists for anything out of room etc
            valid_dynamic_shapes = []
            for shape in self.dynamic_shapes:
                if shape.go.should_collide():
                    valid_dynamic_shapes.append(shape)
            for shape in valid_dynamic_shapes:
                shape.resolve_overlaps_with_shapes(valid_dynamic_shapes)
            for shape in valid_dynamic_shapes:
                static_shapes = shape.get_overlapping_static_shapes()
                shape.resolve_overlaps_with_shapes(static_shapes)
        # check which objects stopped colliding
        for obj in self.world.objects.values():
            obj.check_finished_contacts()
        self.ticks += 1
        self.collisions_this_frame = []


# collision handling

def point_in_box(x, y, box_left, box_top, box_right, box_bottom):
    "Return True if given point lies within box with given corners."
    return box_left <= x <= box_right and box_bottom <= y <= box_top

def boxes_overlap(left_a, top_a, right_a, bottom_a,
                  left_b, top_b, right_b, bottom_b):
    "Return True if given boxes A and B overlap."
    for (x, y) in ((left_a, top_a), (right_a, top_a),
                   (right_a, bottom_a), (left_a, bottom_a)):
        if left_b <= x <= right_b and bottom_b <= y <= top_b:
            return True
    return False

def lines_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    "Return True if given lines intersect."
    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    numer = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
    numer2 = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
    if denom == 0:
        if numer == 0 and numer2 == 0:
            # coincident
            return False
        # parallel
        return False
    ua = numer / denom
    ub = numer2 / denom
    return ua >= 0 and ua <= 1 and ub >= 0 and ub <= 1

def line_point_closest_to_point(point_x, point_y, x1, y1, x2, y2):
    "Return point on given line that's closest to given point."
    wx, wy = point_x - x1, point_y - y1
    dir_x, dir_y = x2 - x1, y2 - y1
    proj = wx * dir_x + wy * dir_y
    if proj <= 0:
        # line point 1 is closest
        return x1, y1
    vsq = dir_x ** 2 + dir_y ** 2
    if proj >= vsq:
        # line point 2 is closest
        return x2, y2
    else:
        # closest point is between 1 and 2
        return x1 + (proj / vsq) * dir_x, y1 + (proj / vsq) * dir_y

def circle_overlaps_line(circle_x, circle_y, radius, x1, y1, x2, y2):
    "Return True if given circle overlaps given line."
    # get closest point on line to circle center
    closest_x, closest_y = line_point_closest_to_point(circle_x, circle_y,
                                                       x1, y1, x2, y2)
    dist_x, dist_y = closest_x - circle_x, closest_y - circle_y
    return dist_x ** 2 + dist_y ** 2 <= radius ** 2

def box_overlaps_line(left, top, right, bottom, x1, y1, x2, y2):
    "Return True if given box overlaps given line."
    # TODO: determine if this is less efficient than slab method below
    if point_in_box(x1, y1, left, top, right, bottom) and \
       point_in_box(x2, y2, left, top, right, bottom):
        return True
    # check left/top/right/bottoms edges
    return lines_intersect(left, top, left, bottom, x1, y1, x2, y2) or \
        lines_intersect(left, top, right, top, x1, y1, x2, y2) or \
        lines_intersect(right, top, right, bottom, x1, y1, x2, y2) or \
        lines_intersect(left, bottom, right, bottom, x1, y1, x2, y2)

def box_overlaps_ray(left, top, right, bottom, x1, y1, x2, y2):
    "Return True if given box overlaps given ray."
    # TODO: determine if this can be adapted for line segments
    # (just a matter of setting tmin/tmax properly?)
    tmin, tmax = -math.inf, math.inf
    dir_x, dir_y = x2 - x1, y2 - y1
    if abs(dir_x) > 0:
        tx1 = (left - x1) / dir_x
        tx2 = (right - x1) / dir_x
        tmin = max(tmin, min(tx1, tx2))
        tmax = min(tmax, max(tx1, tx2))
    if abs(dir_y) > 0:
        ty1 = (top - y1) / dir_y
        ty2 = (bottom - y1) / dir_y
        tmin = max(tmin, min(ty1, ty2))
        tmax = min(tmax, max(ty1, ty2))
    return tmax >= tmin

def point_circle_penetration(point_x, point_y, circle_x, circle_y, radius):
    "Return normalized penetration x, y, and distance for given circles."
    dx, dy = circle_x - point_x, circle_y - point_y
    pdist = math.sqrt(dx ** 2 + dy ** 2)
    # point is center of circle, arbitrarily project out in +X
    if pdist == 0:
        return 1, 0, -radius, -radius
    # TODO: calculate other axis of intersection for area?
    return dx / pdist, dy / pdist, pdist - radius, pdist - radius

def box_penetration(ax, ay, bx, by, ahw, ahh, bhw, bhh):
    "Return penetration vector and magnitude for given boxes."
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
    # return separating axis + penetration depth (+ other axis for area calc)
    if widths + px - abs(dx) < heights + py - abs(dy):
        if dx >= 0:
            return 1, 0, -px, -py
        elif dx < 0:
            return -1, 0, -px, -py
    else:
        if dy >= 0:
            return 0, 1, -py, -px
        elif dy < 0:
            return 0, -1, -py, -px

def circle_box_penetration(circle_x, circle_y, box_x, box_y, circle_radius,
                           box_hw, box_hh):
    "Return penetration vector and magnitude for given circle and box."
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
        return
    1, 0, -pdist, -pdist
    # TODO: calculate other axis of intersection for area?
    return -closest_x / d, -closest_y / d, -pdist, -pdist
