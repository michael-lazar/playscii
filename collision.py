
from renderable import TileRenderable
from renderable_line import CircleCollisionRenderable, BoxCollisionRenderable, TileCollisionRenderable

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


class Collideable:
    
    def __init__(self, obj):
        self.game_object = obj
        self.shape_type = self.game_object.collision_shape_type
        self.renderable = TileRenderable(obj.app, obj.art, obj)
        if self.game_object.collision_shape_type != CST_NONE:
            pass
        #self.create_collision()
    
    def set_type(self, new_type):
        self.collision_type = new_type
        for shape in self.col_shapes:
            shape.collision_type = self.collision_type
    
    def update(self):
        # TODO: update transform based on our object
        pass
    
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
    
    def destroy(self):
        self.renderable.destroy()


def a_push_b(a, b, contact):
    x = b.x + contact.normal.x * contact.distance
    y = b.y + contact.normal.y * contact.distance
    b.set_loc(x, y)
    #b.vel_x = 0
    #b.vel_y = 0

def player_vs_dynamic_begin(space, arbiter):
    obj1 = arbiter.shapes[0].gobj
    obj2 = arbiter.shapes[1].gobj
    #print('pymunk: %s collided with %s' % (obj1.name, obj2.name))
    a_push_b(obj1, obj2, arbiter.contacts[0])
    return True

def player_vs_dynamic_pre_solve(space, arbiter):
    player_vs_dynamic_begin(space, arbiter)
    return False

def player_vs_static_begin(space, arbiter):
    obj1 = arbiter.shapes[0].gobj
    obj2 = arbiter.shapes[1].gobj
    #print('pymunk: %s collided with %s' % (obj1.name, obj2.name))
    a_push_b(obj2, obj1, arbiter.contacts[0])
    return True

def player_vs_static_pre_solve(space, arbiter):
    player_vs_static_begin(space, arbiter)
    return False

def always_collide(space, arbiter):
    return True
