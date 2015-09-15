import os, sys, time, importlib, json

import collision
from camera import Camera
from art import ART_DIR

TOP_GAME_DIR = 'games/'
DEFAULT_STATE_FILENAME = 'start'
STATE_FILE_EXTENSION = 'gs'
GAME_SCRIPTS_DIR = 'scripts/'
START_SCRIPT_FILENAME = 'start.py'
SOUNDS_DIR = 'sounds/'

# import after game_object has done its imports from us
import game_object
import game_hud

class RenderItem:
    "quickie class to debug render order"
    def __init__(self, obj, layer, sort_value):
        self.obj, self.layer, self.sort_value = obj, layer, sort_value
    def __str__(self):
        return '%s layer %s sort %s' % (self.obj.art.filename, self.layer, self.sort_value)


class GameWorld:
    
    "holds global state for game mode"
    # properties serialized via WorldPropertiesObject (make sure type is right)
    gravity_x, gravity_y, gravity_z = 0., 0., 0.
    bg_color = [0., 0., 0., 1.]
    hud_class_name = 'GameHUD'
    properties_object_class_name = 'WorldPropertiesObject'
    globals_object_class_name = 'WorldGlobalsObject'
    player_camera_lock = True
    object_grid_snap = True
    # editable properties
    draw_hud = True
    collision_enabled = True
    # toggles for "show all" debug viz modes
    show_collision_all = False
    show_bounds_all = False
    show_origin_all = False
    
    def __init__(self, app):
        self.app = app
        self.game_dir = None
        self.sounds_dir = None
        self.game_name = None
        self.selected_objects = []
        self.last_click_on_ui = False
        self.properties = None
        self.globals = None
        self.camera = Camera(self.app)
        self.player = None
        self.paused = False
        self.modules = {'game_object': game_object, 'game_hud': game_hud}
        self.classname_to_spawn = None
        # table of objects by name:object
        self.objects = {}
        # table of just-spawned objects, added to above on update() after spawn
        self.new_objects = {}
        self.cl = collision.CollisionLord(self)
        self.hud = None
        self.art_loaded = []
        # player is edit-dragging an object
        self.dragging_object = False
        self.last_state_loaded = DEFAULT_STATE_FILENAME
    
    def play_music(self, music_filename, fade_in_time=0):
        music_filename = self.game_dir + SOUNDS_DIR + music_filename
        self.app.al.set_music(music_filename)
        self.app.al.start_music(music_filename)
    
    def stop_music(self):
        self.app.al.stop_all_music()
    
    def is_music_playing(self):
        return self.app.al.is_music_playing()
    
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
        # not dragging anything?
        if len(self.selected_objects) == 0:
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
    
    def select_object(self, obj, force=False):
        if not self.app.can_edit:
            return
        if obj and (obj.selectable or force) and not obj in self.selected_objects:
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
        self.camera.focus_object = None
        self.player = None
        self.objects = {}
        # art_loaded is cleared when game dir is set
        self.selected_objects = []
        self.app.al.stop_all_music()
    
    def get_all_objects_of_type(self, class_name):
        # TODO: "allow subclasses" optional flag
        objects = []
        for obj in self.objects.values():
            if type(obj).__name__ == class_name:
                objects.append(obj)
        return objects
    
    def set_for_all_objects(self, name, value):
        for obj in self.objects.values():
            setattr(obj, name, value)
    
    def edit_art_for_selected(self):
        if len(self.selected_objects) == 0:
            return
        self.app.exit_game_mode()
        for obj in self.selected_objects:
            for art_filename in obj.get_all_art():
                self.app.load_art_for_edit(art_filename)
    
    def move_selected(self, move_x, move_y, move_z):
        for obj in self.selected_objects:
            #obj.move(move_x, move_y)
            obj.x += move_x
            obj.y += move_y
            obj.z += move_z
    
    def reset_game(self):
        if self.game_dir:
            self.load_game_state(self.last_state_loaded)
    
    def set_game_dir(self, dir_name, reset=False):
        if dir_name == self.game_dir:
            self.load_game_state(DEFAULT_STATE_FILENAME)
            return
        # loading a new game, wipe art list
        self.art_loaded = []
        # check in user documents dir first
        game_dir = TOP_GAME_DIR + dir_name
        doc_game_dir = self.app.documents_dir + game_dir
        for d in [doc_game_dir, game_dir]:
            if not os.path.exists(d):
                continue
            self.game_dir = d
            self.game_name = dir_name
            if not d.endswith('/'):
                self.game_dir += '/'
            self.app.log('Game data directory is now %s' % self.game_dir)
            if reset:
                # load in a default state, eg start.gs
                self.load_game_state(DEFAULT_STATE_FILENAME)
            else:
                # if no reset load submodules into namespace from the get-go
                self.import_all()
                self.classes = self.get_all_loaded_classes()
            break
        else:
            self.app.log("Couldn't find game directory %s" % dir_name)
        if self.app.ui:
            self.app.ui.edit_game_panel.draw_titlebar()
        if self.game_dir:
            self.sounds_dir = self.game_dir + SOUNDS_DIR
    
    def import_all(self):
        module_path = self.game_dir + GAME_SCRIPTS_DIR
        # build list of module files
        modules_list = ['game_object', 'game_hud']
        for filename in os.listdir(module_path):
            # exclude emacs temp files and special world start script
            if not filename.endswith('.py'):
                continue
            if filename.startswith('.#'):
                continue
            if filename == START_SCRIPT_FILENAME:
                continue
            modules_list.append(filename[:-3])
        # make copy of old modules table for import vs reload check
        old_modules = self.modules.copy()
        self.modules = {}
        # add game dir to import path if it isn't there already
        if not module_path in sys.path:
            sys.path += [module_path]
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
    
    def pre_frame_update(self):
        "runs at start of game loop iteration, before input/update/render"
        for obj in self.objects.values():
            obj.art.updated_this_tick = False
    
    def frame_update(self):
        for obj in self.objects.values():
            obj.frame_update()
    
    def pre_update(self):
        # add newly spawned objects to table
        self.objects.update(self.new_objects)
        self.new_objects = {}
        for obj in self.objects.values():
            obj.pre_update()
    
    def update(self):
        self.mouse_moved(self.app.mouse_dx, self.app.mouse_dy)
        if self.properties:
            self.properties.update_from_world()
        # run "first update" on all appropriate objects
        for obj in self.objects.values():
            if not obj.pre_first_update_run:
                obj.pre_first_update()
                obj.pre_first_update_run = True
        if not self.paused:
            # update objects based on movement, then resolve collisions
            for obj in self.objects.values():
                obj.update()
            if self.collision_enabled:
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
        for obj_name in to_destroy:
            self.objects.pop(obj_name)
        if self.hud:
            self.hud.update()
    
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
        if self.hud and self.draw_hud:
            self.hud.render()
    
    def save_to_file(self, filename=None):
        objects = []
        for obj in self.objects.values():
            if obj.should_save:
                objects.append(obj.get_dict())
        d = {'objects': objects}
        if filename and filename != '':
            if not filename.endswith(STATE_FILE_EXTENSION):
                filename += '.' + STATE_FILE_EXTENSION
            filename = '%s%s' % (self.game_dir, filename)
        else:
            # state filename example:
            # games/mytestgame2/1431116386.gs
            timestamp = int(time.time())
            filename = '%s%s.%s' % (self.game_dir, timestamp,
                                     STATE_FILE_EXTENSION)
        json.dump(d, open(filename, 'w'),
                  sort_keys=True, indent=1)
        self.app.log('Saved game state %s to disk.' % filename)
    
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
                if issubclass(v, game_object.GameObject) or \
                   issubclass(v, game_hud.GameHUD):
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
        new_obj = self.spawn_object_from_data(d)
        return new_obj
    
    def spawn_object_of_class(self, class_name, x=None, y=None):
        if not class_name in self.classes:
            self.app.log("Couldn't find class %s" % class_name)
            return
        d = {'class_name': class_name}
        if x is not None and y is not None:
            d['x'], d['y'] = x, y
        new_obj = self.spawn_object_from_data(d)
        return new_obj
    
    def spawn_object_from_data(self, object_data):
        # load module and class
        class_name = object_data.get('class_name', None)
        if not class_name or not class_name in self.classes:
            self.app.log("Couldn't parse class %s" % class_name)
            return
        obj_class = self.classes[class_name]
        # pass in object data
        new_object = obj_class(self, object_data)
        return new_object
    
    def load_game_state(self, filename=DEFAULT_STATE_FILENAME):
        if not os.path.exists(filename):
            filename = self.game_dir + filename
        if not filename.endswith(STATE_FILE_EXTENSION):
            filename += '.' + STATE_FILE_EXTENSION
        self.app.enter_game_mode()
        self.unload_game()
        # tell list panel to reset, its contents might get jostled
        self.app.ui.edit_list_panel.game_reset()
        # import all submodules and catalog classes
        self.import_all()
        self.classes = self.get_all_loaded_classes()
        try:
            d = json.load(open(filename))
            #self.app.log('Loading game state %s...' % filename)
        except:
            self.app.log("Couldn't load game state from %s" % filename)
            #self.app.log(sys.exc_info())
            return
        # spawn objects
        for obj_data in d['objects']:
            self.spawn_object_from_data(obj_data)
        # spawn a WorldPropertiesObject if one doesn't exist
        for obj in self.new_objects.values():
            if type(obj).__name__ == self.properties_object_class_name:
                self.properties = obj
                break
        if not self.properties:
            self.properties = self.spawn_object_of_class(self.properties_object_class_name, 0, 0)
        # spawn a WorldGlobalStateObject
        self.globals = self.spawn_object_of_class(self.properties.globals_object_class_name, 0, 0)
        # spawn hud
        hud_class = self.classes[d.get('hud_class', self.hud_class_name)]
        self.hud = hud_class(self)
        self.hud_class_name = hud_class.__name__
        
        self.app.log('Loaded game state from %s' % filename)
        self.last_state_loaded = filename
        self.set_for_all_objects('show_collision', self.show_collision_all)
        self.set_for_all_objects('show_bounds', self.show_bounds_all)
        self.set_for_all_objects('show_origin', self.show_origin_all)
        self.app.update_window_title()
        self.app.ui.edit_list_panel.refresh_items()
        # run "world start" script if present
        start_script = self.game_dir + GAME_SCRIPTS_DIR + START_SCRIPT_FILENAME
        if os.path.exists(start_script):
            world = self
            exec(open(start_script).read())
        #self.report()
    
    def report(self):
        print('--------------\n%s report:' % self)
        obj_arts, obj_rends, obj_dbg_rends, obj_cols, obj_col_rends = 0, 0, 0, 0, 0
        attachments = 0
        # create merged dict of existing and just-spawned objects
        all_objects = self.objects.copy()
        all_objects.update(self.new_objects)
        print('%s objects:' % len(all_objects))
        for obj in all_objects.values():
            obj_arts += len(obj.arts)
            if obj.renderable is not None:
                obj_rends += 1
            if obj.origin_renderable is not None:
                obj_dbg_rends += 1
            if obj.bounds_renderable is not None:
                obj_dbg_rends += 1
            if obj.collision:
                obj_cols += 1
                obj_col_rends += len(obj.collision.renderables)
            attachments += len(obj.attachments)
        print("""
        %s arts in objects, %s arts loaded,
        %s HUD arts, %s HUD renderables,
        %s renderables, %s debug renderables,
        %s collideables, %s collideable viz renderables,
        %s attachments""" % (obj_arts, len(self.art_loaded), len(self.hud.arts),
                             len(self.hud.renderables),
                             obj_rends, obj_dbg_rends,
                             obj_cols, obj_col_rends, attachments))
        self.cl.report()
        print('%s charsets loaded, %s palettes' % (len(self.app.charsets),
                                                   len(self.app.palettes)))
        print('%s arts loaded for edit' % len(self.app.art_loaded_for_edit))
    
    def toggle_all_origin_viz(self):
        self.show_origin_all = not self.show_origin_all
        self.set_for_all_objects('show_origin', self.show_origin_all)
    
    def toggle_all_bounds_viz(self):
        self.show_bounds_all = not self.show_bounds_all
        self.set_for_all_objects('show_bounds', self.show_bounds_all)
    
    def toggle_all_collision_viz(self):
        self.show_collision_all = not self.show_collision_all
        self.set_for_all_objects('show_collision', self.show_collision_all)
    
    def destroy(self):
        self.unload_game()
        self.art_loaded = []
