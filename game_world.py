import os
import pymunk

from art import ART_DIR
from camera import Camera

GAME_DIR = 'games/'
GAME_FILE_EXTENSION = 'game'

# collision types
CT_NONE = 0
CT_PLAYER = 1
CT_GENERIC_STATIC = 2
CT_GENERIC_DYNAMIC = 3

# collision type groups, eg static and dynamic
CTG_STATIC = [CT_GENERIC_STATIC]
CTG_DYNAMIC = [CT_GENERIC_DYNAMIC, CT_PLAYER]

# import after game_object has done its imports from us
from game_object import CST_TILE

class RenderItem:
    "quickie class to debug render order"
    def __init__(self, obj, layer, layer_z):
        self.obj, self.layer, self.layer_z = obj, layer, layer_z
    def __str__(self):
        return '%s layer %s z %s' % (self.obj.art.filename, self.layer, self.layer_z)

def a_push_b(a, b, contact):
    x = b.x + contact.normal.x * contact.distance
    y = b.y + contact.normal.y * contact.distance
    b.set_loc(x, y)
    #b.vel_x = 0
    #b.vel_y = 0

def player_vs_dynamic_begin(space, arbiter):
    obj1 = arbiter.shapes[0].gobj
    obj2 = arbiter.shapes[1].gobj
    print('pymunk: %s collided with %s' % (obj1.name, obj2.name))
    a_push_b(obj1, obj2, arbiter.contacts[0])
    return True

def player_vs_dynamic_pre_solve(space, arbiter):
    player_vs_dynamic_begin(space, arbiter)
    return False

def player_vs_static_begin(space, arbiter):
    obj1 = arbiter.shapes[0].gobj
    obj2 = arbiter.shapes[1].gobj
    print('pymunk: %s collided with %s' % (obj1.name, obj2.name))
    a_push_b(obj2, obj1, arbiter.contacts[0])
    return True

def player_vs_static_pre_solve(space, arbiter):
    player_vs_static_begin(space, arbiter)
    return False

def always_collide(space, arbiter):
    return True

class GameWorld:
    
    "holds global state for game mode"
    gravity_x, gravity_y = 0, 0
    
    def __init__(self, app):
        self.app = app
        self.current_game_name = None
        # "tuner": set an object to this for quick console tuning access
        self.camera = Camera(self.app)
        self.player, self.tuner = None, None
        self.objects = []
        self.space = pymunk.Space()
        self.space.gravity = self.gravity_x, self.gravity_y
        self.space.add_collision_handler(CT_PLAYER, CT_GENERIC_DYNAMIC,
                                         begin=player_vs_dynamic_begin,
                                         pre_solve=player_vs_dynamic_pre_solve)
        self.space.add_collision_handler(CT_PLAYER, CT_GENERIC_STATIC,
                                         begin=player_vs_static_begin,
                                         pre_solve=player_vs_static_pre_solve)
        self.art_loaded, self.renderables = [], []
    
    def unload_game(self):
        for obj in self.objects:
            obj.destroy()
        self.objects = []
        self.renderables = []
        self.art_loaded = []
    
    def set_for_all_objects(self, name, value):
        for obj in self.objects:
            setattr(obj, name, value)
    
    def reset_game(self):
        if self.current_game_name:
            self.load_game(self.current_game_name)
    
    def load_game(self, game_name):
        self.app.enter_game_mode()
        # execute game script, which loads game assets etc
        game_file = '%s%s/%s.%s' % (GAME_DIR, game_name, game_name, GAME_FILE_EXTENSION)
        if not os.path.exists(game_file):
            self.app.log("Couldn't find game script: %s" % game_file)
            return
        self.unload_game()
        self.app.log('loading game %s...' % game_name)
        # set game_dir & game_art_dir for quick access within game script
        self.game_dir = '%s%s/' % (GAME_DIR, game_name)
        self.game_art_dir = '%s%s' % (self.game_dir, ART_DIR)
        exec(open(game_file).read())
        self.current_game_name = game_name
        self.app.log('loaded game %s' % game_name)
    
    def update(self):
        # update objects based on movement, then resolve collisions
        for obj in self.objects:
            obj.update()
        self.space.step(1 / self.app.framerate)
    
    def render(self):
        # sort objects for drawing by each layer Z order
        draw_order = []
        collision_items = []
        for obj in self.objects:
            obj.update_renderables()
            for i,z in enumerate(obj.art.layers_z):
                # only draw collision layer if show collision is set
                if obj.collision_shape_type == CST_TILE and obj.col_layer_name == obj.art.layer_names[i]:
                    if obj.show_collision:
                        item = RenderItem(obj, i, 0)
                        collision_items.append(item)
                    continue
                item = RenderItem(obj, i, z + obj.z)
                draw_order.append(item)
        draw_order.sort(key=lambda item: item.layer_z, reverse=False)
        for item in draw_order:
            item.obj.render(item.layer)
        # draw debug stuff: collision layers and origins/boxes
        for item in collision_items:
            # draw all tile collision at z 0
            item.obj.render(item.layer, 0)
        for obj in self.objects:
            obj.render_debug()
