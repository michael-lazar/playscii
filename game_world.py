import os

from art import ART_DIR
from game_object import GameObject
from camera import Camera
from collision import CollisionLord, CT_NONE, CT_TILE, CT_CIRCLE, CT_AABB

GAME_DIR = 'games/'
GAME_FILE_EXTENSION = 'game'


class RenderItem:
    "quickie class to debug render order"
    def __init__(self, obj, layer, layer_z):
        self.obj, self.layer, self.layer_z = obj, layer, layer_z
    def __str__(self):
        return '%s layer %s z %s' % (self.obj.art.filename, self.layer, self.layer_z)


class GameWorld:
    "holds global state for game mode"
    def __init__(self, app):
        self.app = app
        # "tuner": set an object to this for quick console tuning access
        self.camera = Camera(self.app)
        self.player, self.tuner = None, None
        self.objects = []
        self.cl = CollisionLord(self)
        self.art_loaded, self.renderables = [], []
    
    def unload_game(self):
        self.objects = []
        self.renderables = []
        self.art_loaded = []
    
    def set_for_all_objects(self, name, value):
        for obj in self.objects:
            setattr(obj, name, value)
    
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
        self.app.log('loaded game %s' % game_name)
    
    def update(self):
        # update objects based on movement, then resolve collisions
        for obj in self.objects:
            obj.update()
        self.cl.update()
    
    def render(self):
        # sort objects for drawing by each layer Z order
        draw_order = []
        collision_items = []
        for obj in self.objects:
            for i,z in enumerate(obj.art.layers_z):
                # only draw collision layer if show collision is set
                if obj.collision_type == CT_TILE and obj.col_layer_name == obj.art.layer_names[i]:
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
    
