import os, sys, time, json, importlib
import pymunk

import collision
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
import game_object

class RenderItem:
    "quickie class to debug render order"
    def __init__(self, obj, layer, sort_value):
        self.obj, self.layer, self.sort_value = obj, layer, sort_value
    def __str__(self):
        return '%s layer %s sort %s' % (self.obj.art.filename, self.layer, self.sort_value)

class GameWorld:
    
    "holds global state for game mode"
    gravity_x, gravity_y = 0, 0
    
    def __init__(self, app):
        self.app = app
        self.game_dir = None
        self.selected_objects = []
        self.camera = Camera(self.app)
        self.player = None
        self.modules = {'game_object': game_object}
        self.objects = []
        self.space = pymunk.Space()
        self.space.gravity = self.gravity_x, self.gravity_y
        self.space.add_collision_handler(CT_PLAYER, CT_GENERIC_DYNAMIC,
                                         begin=collision.player_vs_dynamic_begin,
                                         pre_solve=collision.player_vs_dynamic_pre_solve)
        self.space.add_collision_handler(CT_PLAYER, CT_GENERIC_STATIC,
                                         begin=collision.player_vs_static_begin,
                                         pre_solve=collision.player_vs_static_pre_solve)
        self.art_loaded, self.renderables = [], []
        # player is edit-dragging an object
        self.dragging_object = False
        self.last_state_loaded = None
    
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
        if self.app.ui.active_dialog:
            return
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
        if self.app.ui.active_dialog:
            return
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
    
    def deselect_object(self, obj):
        if obj in self.selected_objects:
            self.selected_objects.remove(obj)
    
    def deselect_all(self):
        self.selected_objects = []
    
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
    
    def move_selected(self, move_x, move_y, move_z):
        for obj in self.selected_objects:
            #obj.move(move_x, move_y)
            obj.x += move_x
            obj.y += move_y
            obj.z += move_z
    
    def reset_game(self):
        if self.game_dir:
            self.set_game_dir(self.game_dir, True)
    
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
            # import all submodules to get them in namespace from the get-go
            self.import_all()
            # load in a default state, eg start.gs
            if reset:
                self.load_game_state(DEFAULT_STATE_FILENAME)
        else:
            self.app.log("Couldn't find game directory %s" % dir_name)
    
    def import_all(self):
        module_suffix = TOP_GAME_DIR[:-1] + '.'
        module_suffix += self.game_dir[:-1] + '.'
        module_suffix += GAME_SCRIPTS_DIR[:-1] + '.'
        module_path = TOP_GAME_DIR + self.game_dir + GAME_SCRIPTS_DIR
        for filename in os.listdir(module_path):
            if filename.endswith('.py'):
                module_name = module_suffix + filename[:-3]
                if not module_name in self.modules:
                    self.modules[module_name] = importlib.import_module(module_name)
    
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
        y_objects = []
        for obj in self.objects:
            if obj.y_sort:
                y_objects.append(obj)
                continue
            for i,z in enumerate(obj.art.layers_z):
                # only draw collision layer if show collision is set
                if obj.collision_shape_type == game_object.CST_TILE and obj.col_layer_name == obj.art.layer_names[i]:
                    if obj.show_collision:
                        item = RenderItem(obj, i, 0)
                        collision_items.append(item)
                    continue
                item = RenderItem(obj, i, z + obj.z)
                draw_order.append(item)
        draw_order.sort(key=lambda item: item.sort_value, reverse=False)
        #
        # process "Y sort" objects
        #
        y_objects.sort(key=lambda obj: obj.y, reverse=True)
        # draw layers of each Y-sorted object in Z order
        for obj in y_objects:
            items = []
            for i,z in enumerate(obj.art.layers_z):
                if obj.collision_shape_type == game_object.CST_TILE and obj.col_layer_name == obj.art.layer_names[i]:
                    if obj.show_collision:
                        item = RenderItem(obj, i, 0)
                        collision_items.append(item)
                    continue
                item = RenderItem(obj, i, z)
                items.append(item)
            items.sort(key=lambda item: item.sort_value, reverse=False)
            for item in items:
                draw_order.append(item)
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
                # log exception info
                #self.app.log(sys.exc_info())
                return None
        else:
            return importlib.import_module(module_name)
    
    def get_module_name_for_class(self, class_name):
        if '.' in class_name:
            return class_name[:class_name.rfind('.')]
        for module_name,module in self.modules.items():
            if class_name in module.__dict__:
                return module_name
        return None
    
    def reset_object_in_place(self, obj):
        x, y = obj.x, obj.y
        obj_class = obj.__class__.__name__
        spawned = self.spawn_object_of_class(obj_class, x, y)
        if spawned:
            self.app.log('%s reset to class defaults' % obj.name)
            if obj is self.player:
                self.player = spawned
            obj.destroy()
    
    def spawn_object_of_class(self, class_name, x=None, y=None):
        module_name = self.get_module_name_for_class(class_name)
        if not module_name:
            self.app.log("Couldn't find module for class %s" % class_name)
            return
        d = {'class_name': class_name, 'module_name': module_name}
        if x is not None and y is not None:
            d['x'], d['y'] = x, y
        return self.spawn_object_from_data(d)
    
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
        # special handling if object is player
        if object_data.get('is_player', False):
            self.player = new_object
            self.camera.focus_object = self.player
        return new_object
    
    def load_game_state(self, filename):
        filename = '%s%s%s.%s' % (TOP_GAME_DIR, self.game_dir, filename, STATE_FILE_EXTENSION)
        self.app.enter_game_mode()
        self.unload_game()
        try:
            d = json.load(open(filename))
            #self.app.log('Loading game state file %s...' % filename)
        except:
            self.app.log("Couldn't load game state from file %s" % filename)
            #self.app.log(sys.exc_info())
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
        self.last_state_loaded = filename
        self.set_for_all_objects('show_collision', self.app.show_collision_all)
        self.set_for_all_objects('show_bounds', self.app.show_bounds_all)
        self.set_for_all_objects('show_origin', self.app.show_origin_all)
        self.app.update_window_title()
    
    def toggle_all_origin_viz(self):
        self.app.show_origin_all = not self.app.show_origin_all
        self.set_for_all_objects('show_origin', self.app.show_origin_all)
    
    def toggle_all_bounds_viz(self):
        self.app.show_bounds_all = not self.app.show_bounds_all
        self.set_for_all_objects('show_bounds', self.app.show_bounds_all)
    
    def toggle_all_collision_viz(self):
        self.app.show_collision_all = not self.app.show_collision_all
        self.set_for_all_objects('show_collision', self.app.show_collision_all)
