import os, sys, time, json, importlib

import collision
from camera import Camera
from art import ART_DIR

TOP_GAME_DIR = 'games/'
DEFAULT_STATE_FILENAME = 'start'
STATE_FILE_EXTENSION = 'gs'
GAME_SCRIPTS_DIR = 'scripts/'

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
    gravity_x, gravity_y, gravity_z = 0, 0, 0
    last_click_on_ui = False
    player_camera_lock = True
    object_grid_snap = True
    
    def __init__(self, app):
        self.app = app
        self.game_dir = None
        self.top_game_dir = TOP_GAME_DIR
        self.selected_objects = []
        self.camera = Camera(self.app)
        self.player = None
        self.paused = False
        self.modules = {'game_object': game_object}
        self.classname_to_spawn = None
        # table of objects by name:object
        self.objects = {}
        self.cl = collision.CollisionLord(self)
        self.art_loaded = []
        # player is edit-dragging an object
        self.dragging_object = False
        self.last_state_loaded = DEFAULT_STATE_FILENAME
    
    def pick_next_object_at(self, x, y):
        # TODO: cycle through objects at point til an unselected one is found
        for obj in self.get_objects_at(x, y):
            if obj.selectable and not obj in self.selected_objects:
                return obj
        return None
    
    def get_objects_at(self, x, y):
        "returns list of all objects whose bounds fall within given point"
        objects = []
        for obj in self.objects.values():
            # only allow selecting of visible objects
            # (can still be selected via edit panel)
            if obj.visible and not obj.locked and obj.is_point_inside(x, y):
                objects.append(obj)
        return objects
    
    def clicked(self, button):
        if self.classname_to_spawn:
            x, y, z = self.app.cursor.screen_to_world(self.app.mouse_x,
                                                      self.app.mouse_y)
            self.spawn_object_of_class(self.classname_to_spawn, x, y)
    
    def unclicked(self, button):
        # clicks on UI are consumed and flag world to not accept unclicks
        # (keeps unclicks after dialog dismiss from deselecting objects)
        if self.last_click_on_ui:
            self.last_click_on_ui = False
            return
        # if we're clicking to spawn something, don't drag/select
        if self.classname_to_spawn:
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
        # if last onclick was a UI element, don't drag
        if self.last_click_on_ui:
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
                # check "locked" flag
                if not obj.locked:
                    # note: grid snap is set in object.stopped_dragging()
                    obj.x += world_dx
                    obj.y += world_dy
            self.dragging_object = True
    
    def select_object(self, obj):
        if obj and obj.selectable and not obj in self.selected_objects:
            self.selected_objects.append(obj)
    
    def deselect_object(self, obj):
        if obj in self.selected_objects:
            self.selected_objects.remove(obj)
    
    def deselect_all(self):
        self.selected_objects = []
    
    def unload_game(self):
        for obj in self.objects.values():
            obj.destroy()
        self.cl.reset()
        self.objects = {}
        self.renderables = []
        self.art_loaded = []
        self.selected_objects = []
    
    def set_for_all_objects(self, name, value):
        for obj in self.objects.values():
            setattr(obj, name, value)
    
    def move_selected(self, move_x, move_y, move_z):
        for obj in self.selected_objects:
            #obj.move(move_x, move_y)
            obj.x += move_x
            obj.y += move_y
            obj.z += move_z
    
    def reset_game(self):
        if self.game_dir:
            self.load_game_state(self.last_state_loaded)
    
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
            if reset:
                # load in a default state, eg start.gs
                self.load_game_state(DEFAULT_STATE_FILENAME)
            else:
                # if no reset load submodules into namespace from the get-go
                self.import_all()
                self.classes = self.get_all_loaded_classes()
        else:
            self.app.log("Couldn't find game directory %s" % dir_name)
        if self.app.ui:
            self.app.ui.edit_game_panel.draw_titlebar()
    
    def import_all(self):
        module_suffix = TOP_GAME_DIR[:-1] + '.'
        module_suffix += self.game_dir[:-1] + '.'
        module_suffix += GAME_SCRIPTS_DIR[:-1] + '.'
        module_path = TOP_GAME_DIR + self.game_dir + GAME_SCRIPTS_DIR
        # build list of module files
        modules_list = ['game_object']
        for filename in os.listdir(module_path):
            # exclude emacs temp files :/
            if filename.endswith('.py') and not filename.startswith('.#'):
                modules_list.append(module_suffix + filename[:-3])
        # make copy of old modules table for import vs reload check
        old_modules = self.modules.copy()
        self.modules = {}
        for module_name in modules_list:
            if module_name in old_modules:
                self.modules[module_name] = importlib.reload(old_modules[module_name])
            else:
                self.modules[module_name] = importlib.import_module(module_name)
    
    def toggle_pause(self):
        self.paused = not self.paused
        s = 'Game %spaused.' % ['un', ''][self.paused]
        self.app.ui.message_line.post_line(s)
    
    def toggle_player_camera_lock(self):
        self.player_camera_lock = not self.player_camera_lock
        if self.player_camera_lock:
            if self.player:
                self.camera.focus_object = self.player
        else:
            self.camera.focus_object = None
    
    def toggle_grid_snap(self):
        self.object_grid_snap = not self.object_grid_snap
    
    def pre_update(self):
        "runs at start of game loop iteration, before input/update/render"
        for obj in self.objects.values():
            obj.art.updated_this_tick = False
    
    def update(self, dt):
        self.mouse_moved(self.app.mouse_dx, self.app.mouse_dy)
        if not self.paused:
            # update objects based on movement, then resolve collisions
            for obj in self.objects.values():
                obj.update(dt)
            self.cl.resolve_overlaps()
        # display debug text for selected object(s)
        for obj in self.selected_objects:
            s = obj.get_debug_text()
            if s:
                self.app.ui.debug_text.post_lines(s)
        # remove objects marked for destruction
        to_destroy = []
        for obj in self.objects.values():
            if obj.should_destroy:
                to_destroy.append(obj.name)
        for obj in to_destroy:
            self.objects.pop(obj)
    
    def render(self):
        for obj in self.objects.values():
            obj.update_renderables()
        #
        # process non "Y sort" objects first
        #
        draw_order = []
        collision_items = []
        y_objects = []
        for obj in self.objects.values():
            if obj.y_sort:
                y_objects.append(obj)
                continue
            for i,z in enumerate(obj.art.layers_z):
                # ignore invisible layers
                if not obj.art.layers_visibility[i]:
                    continue
                # only draw collision layer if show collision is set
                if obj.collision_shape_type == collision.CST_TILE and \
                   obj.col_layer_name == obj.art.layer_names[i]:
                    if obj.show_collision:
                        item = RenderItem(obj, i, 0)
                        collision_items.append(item)
                    continue
                # respect object's "should render at all" flag
                if obj.visible:
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
                if not obj.art.layers_visibility[i]:
                    continue
                if obj.collision_shape_type == collision.CST_TILE and \
                   obj.col_layer_name == obj.art.layer_names[i]:
                    if obj.show_collision:
                        item = RenderItem(obj, i, 0)
                        collision_items.append(item)
                    continue
                if obj.visible:
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
        for obj in self.objects.values():
            obj.render_debug()
    
    def save_to_file(self, filename=None):
        d = {
            'gravity_x': self.gravity_x,
            'gravity_y': self.gravity_y,
            'gravity_z': self.gravity_z,
            'camera_x': self.camera.x,
            'camera_y': self.camera.y,
            'camera_z': self.camera.z
        }
        objects = []
        for obj in self.objects.values():
            if obj.should_save:
                objects.append(obj.get_dict())
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
        json.dump(d, open(TOP_GAME_DIR + filename, 'w'),
                  sort_keys=True, indent=1)
        self.app.log('Saved game state file %s to disk.' % filename)
    
    def get_all_loaded_classes(self):
        """
        returns classname,class dict of all GameObject classes in loaded modules
        """
        classes = {}
        for module in self.modules.values():
            for k,v in module.__dict__.items():
                # skip anything that's not a class
                if not type(v) is type:
                    continue
                if issubclass(v, game_object.GameObject):
                    classes[k] = v
        return classes
    
    def get_class_by_name(self, class_name):
        return self.classes.get(class_name, None)
    
    def reset_object_in_place(self, obj):
        x, y = obj.x, obj.y
        obj_class = obj.__class__.__name__
        spawned = self.spawn_object_of_class(obj_class, x, y)
        if spawned:
            self.app.log('%s reset to class defaults' % obj.name)
            if obj is self.player:
                self.player = spawned
            obj.destroy()
    
    def duplicate_selected_objects(self):
        new_objects = []
        for obj in self.selected_objects:
            new_objects.append(self.duplicate_object(obj))
        # report on objects created
        if len(new_objects) == 1:
            self.app.log('%s created from %s' % (obj.name, new_objects[0].name))
        elif len(new_objects) > 1:
            self.app.log('%s new objects created' % len(new_objects))
    
    def duplicate_object(self, obj):
        d = obj.get_dict()
        # offset new object's location
        x, y = d['x'], d['y']
        x += obj.renderable.width
        y -= obj.renderable.height
        d['x'], d['y'] = x, y
        return self.spawn_object_from_data(d)
    
    def spawn_object_of_class(self, class_name, x=None, y=None):
        if not class_name in self.classes:
            self.app.log("Couldn't find class %s" % class_name)
            return
        d = {'class_name': class_name}
        if x is not None and y is not None:
            d['x'], d['y'] = x, y
        return self.spawn_object_from_data(d)
    
    def spawn_object_from_data(self, object_data):
        # load module and class
        class_name = object_data.get('class_name', None)
        if not class_name or not class_name in self.classes:
            self.app.log("Couldn't parse class %s" % class_name)
            return
        obj_class = self.classes[class_name]
        # pass in object data
        new_object = obj_class(self, object_data)
        # special handling if object is player
        if object_data.get('is_player', False):
            self.player = new_object
            self.camera.focus_object = self.player
        return new_object
    
    def load_game_state(self, filename):
        if not os.path.exists(filename):
            filename = '%s%s%s' % (TOP_GAME_DIR, self.game_dir, filename)
        if not filename.endswith(STATE_FILE_EXTENSION):
            filename += '.%s' % STATE_FILE_EXTENSION
        self.app.enter_game_mode()
        self.unload_game()
        # import all submodules and catalog classes
        self.import_all()
        self.classes = self.get_all_loaded_classes()
        try:
            d = json.load(open(filename))
            #self.app.log('Loading game state file %s...' % filename)
        except:
            self.app.log("Couldn't load game state from file %s" % filename)
            #self.app.log(sys.exc_info())
            return
        self.gravity_x = d['gravity_x']
        self.gravity_y = d['gravity_y']
        self.gravity_z = d.get('gravity_z', self.gravity_z)
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
