import os, sys, time, json, importlib
import pymunk

from camera import Camera
from art import ART_DIR

TOP_GAME_DIR = 'games/'
DEFAULT_STATE_FILENAME = 'start'
STATE_FILE_EXTENSION = 'gs'
GAME_SCRIPTS_DIR = 'scripts/'

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
    def __init__(self, obj, layer, sort_value):
        self.obj, self.layer, self.sort_value = obj, layer, sort_value
    def __str__(self):
        return '%s layer %s sort %s' % (self.obj.art.filename, self.layer, self.sort_value)

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

class GameWorld:
    
    "holds global state for game mode"
    gravity_x, gravity_y = 0, 0
    log_load = False
    
    def __init__(self, app):
        self.app = app
        self.game_dir = None
        self.selected_objects = []
        self.camera = Camera(self.app)
        self.player = None
        self.modules = {}
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
        # player is edit-dragging an object
        self.dragging_object = False
    
    def pick_next_object_at(self, x, y):
        # TODO: cycle through objects at point til an unselected one is found
        for obj in self.get_objects_at(x, y):
            if not obj in self.selected_objects:
                return obj
        return None
    
    def get_objects_at(self, x, y):
        "returns all objects whose bounds fall within given point"
        objects = []
        # reverse object list, helps in (common) case where BG spawns first
        objects_reversed = self.objects[:]
        objects_reversed.reverse()
        for obj in objects_reversed:
            if obj.is_point_inside(x, y):
                objects.append(obj)
        return objects
    
    def clicked(self, button):
        pass
    
    def unclicked(self, button):
        x, y, z = self.app.cursor.screen_to_world(self.app.mouse_x,
                                                  self.app.mouse_y)
        was_dragging = self.dragging_object
        self.dragging_object = False
        if not self.app.il.ctrl_pressed and not self.app.il.shift_pressed:
            objects = self.get_objects_at(x, y)
            if len(objects) == 0:
                self.deselect_all()
                return
        if self.app.il.ctrl_pressed:
            # unselect first object found under mouse
            objects = self.get_objects_at(x, y)
            if len(objects) > 0:
                self.deselect_object(objects[0])
            return
        if was_dragging:
            # tell objects they're no longer being dragged
            for obj in self.selected_objects:
                obj.stop_dragging()
        next_obj = self.pick_next_object_at(x, y)
        # don't select stuff if ending a drag
        if not next_obj and was_dragging:
            return
        if not self.app.il.shift_pressed:
            self.deselect_all()
        self.select_object(next_obj)
    
    def mouse_moved(self, dx, dy):
        # get mouse delta in world space
        mx1, my1, mz1 = self.app.cursor.screen_to_world(self.app.mouse_x,
                                                        self.app.mouse_y)
        mx2, my2, mz2 = self.app.cursor.screen_to_world(self.app.mouse_x + dx,
                                                        self.app.mouse_y + dy)
        world_dx, world_dy = mx2 - mx1, my2 - my1
        if self.app.left_mouse and world_dx != 0 and world_dy != 0:
            for obj in self.selected_objects:
                if not self.dragging_object:
                    obj.start_dragging()
                obj.x += world_dx
                obj.y += world_dy
            self.dragging_object = True
    
    def select_object(self, obj):
        if not obj in self.selected_objects:
            self.selected_objects.append(obj)
            self.app.ui.selection_panel.set_object(obj)
    
    def deselect_object(self, obj):
        if obj in self.selected_objects:
            self.selected_objects.remove(obj)
        if len(self.selected_objects) > 0:
            self.app.ui.selection_panel.set_object(self.selected_objects[0])
        else:
            self.app.ui.selection_panel.set_object(None)
    
    def deselect_all(self):
        self.selected_objects = []
        self.app.ui.selection_panel.set_object(None)
    
    def unload_game(self):
        for obj in self.objects:
            obj.destroy()
        self.objects = []
        self.renderables = []
        self.art_loaded = []
        self.selected_objects = []
    
    def set_for_all_objects(self, name, value):
        for obj in self.objects:
            setattr(obj, name, value)
    
    def reset_game(self):
        if self.game_dir:
            self.set_game_dir(self.game_dir)
    
    def get_game_dir(self):
        return TOP_GAME_DIR + self.game_dir
    
    def set_game_dir(self, dir_name, reset=False):
        if dir_name == self.game_dir:
            self.load_game_state(DEFAULT_STATE_FILENAME)
            return
        if os.path.exists(TOP_GAME_DIR + dir_name):
            self.game_dir = dir_name
            if not dir_name.endswith('/'):
                self.game_dir += '/'
            self.app.log('Game data directory is now %s' % dir_name)
            # load in a default state, eg start.gs
            if reset:
                self.load_game_state(DEFAULT_STATE_FILENAME)
        else:
            self.app.log("Couldn't find game directory %s" % dir_name)
    
    def update(self):
        self.mouse_moved(self.app.mouse_dx, self.app.mouse_dy)
        # update objects based on movement, then resolve collisions
        for obj in self.objects:
            obj.update()
        self.space.step(1 / self.app.framerate)
    
    def render(self):
        for obj in self.objects:
            obj.update_renderables()
        #
        # process non "Y sort" objects first
        #
        draw_order = []
        collision_items = []
        for obj in self.objects:
            for i,z in enumerate(obj.art.layers_z):
                # only draw collision layer if show collision is set
                if obj.collision_shape_type == CST_TILE and obj.col_layer_name == obj.art.layer_names[i]:
                    if obj.show_collision:
                        item = RenderItem(obj, i, 0)
                        collision_items.append(item)
                    continue
                elif obj.y_sort:
                    continue
                item = RenderItem(obj, i, z + obj.z)
                draw_order.append(item)
        draw_order.sort(key=lambda item: item.sort_value, reverse=False)
        for item in draw_order:
            item.obj.render(item.layer)
        #
        # process "Y sort" objects
        #
        y_objects = []
        for obj in self.objects:
            if obj.y_sort:
                y_objects.append(obj)
        y_objects.sort(key=lambda obj: obj.y, reverse=True)
        # draw layers of each Y-sorted object in Z order
        draw_order = []
        for obj in y_objects:
            items = []
            for i,z in enumerate(obj.art.layers_z):
                if obj.collision_shape_type == CST_TILE and obj.col_layer_name == obj.art.layer_names[i]:
                    continue
                item = RenderItem(obj, i, z)
                items.append(item)
            items.sort(key=lambda item: item.sort_value, reverse=False)
            for item in items:
                draw_order.append(item)
        draw_order.sort(key=lambda item: item.sort_value, reverse=False)
        for item in draw_order:
            item.obj.render(item.layer)
        #
        # draw debug stuff: collision layers and origins/boxes
        #
        for item in collision_items:
            # draw all tile collision at z 0
            item.obj.render(item.layer, 0)
        for obj in self.objects:
            obj.render_debug()
    
    def save_state_to_file(self, filename=None):
        d = {}
        d['gravity_x'] = self.gravity_x
        d['gravity_y'] = self.gravity_y
        d['camera_x'] = self.camera.x
        d['camera_y'] = self.camera.y
        d['camera_z'] = self.camera.z
        objects = []
        for obj in self.objects:
            objects.append(obj.get_state_dict())
        d['objects'] = objects
        if filename:
            if not filename.endswith(STATE_FILE_EXTENSION):
                filename += '.' + STATE_FILE_EXTENSION
            filename = '%s%s' % (self.game_dir, filename)
        else:
            # state filename example:
            # games/mytestgame2/1431116386.gs
            timestamp = int(time.time())
            filename = '%s/%s_%s.%s' % (self.game_dir, timestamp,
                                        STATE_FILE_EXTENSION)
        json.dump(d, open(TOP_GAME_DIR + filename, 'w'), sort_keys=True, indent=1)
        self.app.log('Saved game state file %s to disk.' % filename)
    
    def find_module(self, module_name):
        if module_name in self.modules:
            return importlib.reload(self.modules[module_name])
        try:
            return importlib.import_module(module_name)
        except:
            # not found in global namespace, check in scripts dir
            module_name = '%s.%s.%s.%s' % (TOP_GAME_DIR[:-1],
                                           self.game_dir[:-1],
                                           GAME_SCRIPTS_DIR[:-1], module_name)
        if module_name in self.modules:
            try:
                return importlib.reload(self.modules[module_name])
            except:
                # TODO: return exceptions
                return None
        else:
            return importlib.import_module(module_name)
    
    def get_module_name_for_class(self, class_name):
        for module_name,module in self.modules.items():
            if class_name in module.__dict__:
                return module_name
        return None
    
    def spawn_object_of_class(self, class_name, x=None, y=None):
        module_name = self.get_module_name_for_class(class_name)
        if not module_name:
            self.app.log("Couldn't find module for class %s" % class_name)
            return
        d = {'class_name': class_name, 'module_name': module_name}
        if x and y:
            d['x'], d['y'] = x, y
        self.spawn_object_from_data(d)
    
    def spawn_object_from_data(self, object_data):
        # load module and class
        class_name = object_data.get('class_name', None)
        module_name = object_data.get('module_name', None)
        if not class_name or not module_name:
            self.app.log("Couldn't parse class %s in module %s" % (class_name,
                                                                   module_name))
            return
        module = self.find_module(module_name)
        if not module:
            self.app.log("Couldn't import module %s" % module_name)
            return
        self.modules[module.__name__] = module
        # spawn classes
        obj_class = module.__dict__[class_name]
        # pass in object data
        new_object = obj_class(self, object_data)
        # apply properties from JSON
        for prop in new_object.serialized:
            if not hasattr(new_object, prop):
                if self.log_load:
                    self.app.dev_log("Unknown serialized property '%s' for %s" % (prop, new_object.name))
                continue
            elif not prop in object_data:
                if self.log_load:
                    self.app.dev_log("Serialized property '%s' not found for %s" % (prop, new_object.name))
                continue
            setattr(new_object, prop, object_data.get(prop, None))
        # special handling if object is player
        if object_data.get('is_player', False):
            self.player = new_object
            self.camera.focus_object = self.player
    
    def load_game_state(self, filename):
        filename = '%s%s%s.%s' % (TOP_GAME_DIR, self.game_dir, filename, STATE_FILE_EXTENSION)
        self.app.enter_game_mode()
        self.unload_game()
        try:
            d = json.load(open(filename))
            #self.app.log('Loading game state file %s...' % filename)
        except:
            self.app.log("Couldn't load game state from file %s" % filename)
            print(sys.exc_info()[0])
            return
        self.gravity_x = d['gravity_x']
        self.gravity_y = d['gravity_y']
        # spawn objects
        for obj_data in d['objects']:
            self.spawn_object_from_data(obj_data)
        # restore camera settings
        if 'camera_x' in d and 'camera_y' in d and 'camera_z' in d:
            self.camera.set_loc(d['camera_x'], d['camera_y'], d['camera_z'])
        self.app.log('Loaded game state from file %s' % filename)
