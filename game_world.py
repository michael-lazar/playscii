import os, sys, time, importlib, json

import sdl2

import game_object, game_util_objects, game_hud, game_room
import collision, vector
from camera import Camera
from art import ART_DIR
from charset import CHARSET_DIR
from palette import PALETTE_DIR

TOP_GAME_DIR = 'games/'
DEFAULT_STATE_FILENAME = 'start'
STATE_FILE_EXTENSION = 'gs'
GAME_SCRIPTS_DIR = 'scripts/'
SOUNDS_DIR = 'sounds/'


class RenderItem:
    "quickie class to debug render order"
    def __init__(self, obj, layer, sort_value):
        self.obj, self.layer, self.sort_value = obj, layer, sort_value
    def __str__(self):
        return '%s layer %s sort %s' % (self.obj.art.filename, self.layer, self.sort_value)

class GameCamera(Camera):
    pan_friction = 0.2

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
    # if True, show all rooms not just current one
    show_all_rooms = False
    # if False, objects with is_debug=True won't be drawn
    draw_debug_objects = True
    # if True, snap camera to new room's associated camera marker
    room_camera_changes_enabled = True
    # if True, list UI will only show objects in current room
    list_only_current_room_objects = False
    builtin_module_names = ['game_object', 'game_util_objects', 'game_hud',
                            'game_room']
    builtin_base_classes = (game_object.GameObject, game_hud.GameHUD,
                            game_room.GameRoom)
    
    def __init__(self, app):
        self.app = app
        self.game_dir = None
        self.sounds_dir = None
        self.game_name = None
        self.selected_objects = []
        self.last_click_on_ui = False
        self.properties = None
        self.globals = None
        self.camera = GameCamera(self.app)
        self.player = None
        self.paused = False
        self.modules = {'game_object': game_object,
                        'game_util_objects': game_util_objects,
                        'game_hud': game_hud, 'game_room': game_room}
        self.classname_to_spawn = None
        # dict of objects by name:object
        self.objects = {}
        # dict of just-spawned objects, added to above on update() after spawn
        self.new_objects = {}
        # dict of rooms by name:room
        self.rooms = {}
        self.current_room = None
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
        # cycle through objects at point til an unselected one is found
        use_next = False
        for obj in self.get_objects_at(x, y):
            if not obj.selectable:
                continue
            if len(self.selected_objects) == 0:
                return obj
            elif use_next:
                return obj
            elif obj in self.selected_objects:
                use_next = True
        return None
    
    def get_objects_at(self, x, y):
        "returns list of all objects whose bounds fall within given point"
        objects = []
        for obj in self.objects.values():
            # only allow selecting of visible objects
            # (can still be selected via list panel)
            if obj.visible and not obj.locked and obj.is_point_inside(x, y):
                objects.append(obj)
        return objects
    
    def clicked(self, button):
        if self.classname_to_spawn:
            x, y, z = vector.screen_to_world(self.app, self.app.mouse_x,
                                             self.app.mouse_y)
            new_obj = self.spawn_object_of_class(self.classname_to_spawn, x, y)
            if self.current_room:
                self.current_room.add_object(new_obj)
            self.app.ui.message_line.post_line('Spawned %s' % new_obj.name)
    
    def unclicked(self, button):
        # clicks on UI are consumed and flag world to not accept unclicks
        # (keeps unclicks after dialog dismiss from deselecting objects)
        if self.last_click_on_ui:
            self.last_click_on_ui = False
            return
        # if we're clicking to spawn something, don't drag/select
        if self.classname_to_spawn:
            return
        x, y, z = vector.screen_to_world(self.app, self.app.mouse_x,
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
        mx1, my1, mz1 = vector.screen_to_world(self.app, self.app.mouse_x,
                                               self.app.mouse_y)
        mx2, my2, mz2 = vector.screen_to_world(self.app, self.app.mouse_x + dx,
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
        self.app.ui.object_selection_changed()
    
    def deselect_object(self, obj):
        if obj in self.selected_objects:
            self.selected_objects.remove(obj)
        self.app.ui.object_selection_changed()
    
    def deselect_all(self):
        self.selected_objects = []
        self.app.ui.object_selection_changed()
    
    def create_new_game(self, game_name):
        "creates appropriate dirs and files for a new game, returns success"
        new_dir = self.app.documents_dir + TOP_GAME_DIR + game_name + '/'
        if os.path.exists(new_dir):
            self.app.log('Game dir %s already exists!' % game_name)
            return False
        os.mkdir(new_dir)
        os.mkdir(new_dir + ART_DIR)
        os.mkdir(new_dir + GAME_SCRIPTS_DIR)
        os.mkdir(new_dir + SOUNDS_DIR)
        os.mkdir(new_dir + CHARSET_DIR)
        os.mkdir(new_dir + PALETTE_DIR)
        self.set_game_dir(game_name)
        self.save_to_file(DEFAULT_STATE_FILENAME)
        return True
    
    def unload_game(self):
        for obj in self.objects.values():
            obj.destroy()
        self.cl.reset()
        self.camera.reset()
        self.player = None
        self.globals = None
        self.properties = None
        if self.hud:
            self.hud.destroy()
            self.hud = None
        self.objects, self.new_objects = {}, {}
        self.rooms = {}
        # art_loaded is cleared when game dir is set
        self.selected_objects = []
        self.app.al.stop_all_music()
    
    def get_first_object_of_type(self, class_name):
        for obj in self.objects.values():
            if type(obj).__name__ == class_name:
                return obj
    
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
        if self.game_dir and dir_name == self.game_dir:
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
            # set sounds dir before loading state; some obj inits depend on it
            self.sounds_dir = self.game_dir + SOUNDS_DIR
            if reset:
                # load in a default state, eg start.gs
                self.load_game_state(DEFAULT_STATE_FILENAME)
            else:
                # if no reset load submodules into namespace from the get-go
                self.import_all()
                self.classes = self.get_all_loaded_classes()
            break
        if not self.game_dir:
            self.app.log("Couldn't find game directory %s" % dir_name)
    
    def remove_non_current_game_modules(self):
        """
        removes modules from previously-loaded games from both sys and
        GameWorld's dicts
        """
        modules_to_remove = []
        games_dir_prefix = TOP_GAME_DIR.replace('/', '')
        this_game_dir_prefix = '%s.%s' % (games_dir_prefix, self.game_name)
        for module_name in sys.modules:
            # remove any module that isn't for this game or part of its path
            if module_name != games_dir_prefix and \
               module_name != this_game_dir_prefix and \
               module_name.startswith(games_dir_prefix) and \
               not module_name.startswith(this_game_dir_prefix + '.'):
                modules_to_remove.append(module_name)
        for module_name in modules_to_remove:
            sys.modules.pop(module_name)
            if module_name in self.modules:
                self.modules.pop(module_name)
    
    def get_game_modules_list(self):
        "gets list of current game's modules from its scripts/ dir"
        # build list of module files
        modules_list = self.builtin_module_names[:]
        # create appropriately-formatted python import path
        module_path_prefix = '%s.%s.%s.' % (TOP_GAME_DIR.replace('/', ''),
                                            self.game_name,
                                            GAME_SCRIPTS_DIR.replace('/', ''))
        for filename in os.listdir(self.game_dir + GAME_SCRIPTS_DIR):
            # exclude emacs temp files and special world start script
            if not filename.endswith('.py'):
                continue
            if filename.startswith('.#'):
                continue
            new_module_name = module_path_prefix + filename.replace('.py', '')
            modules_list.append(new_module_name)
        return modules_list
    
    def import_all(self):
        """
        populates GameWorld.modules with the modules GW.get_all_loaded_classes
        refers to when finding classes to spawn
        """
        # on first load, documents dir may not be in import path
        if not self.app.documents_dir in sys.path:
            sys.path += [self.app.documents_dir]
        # clean modules dict before (re)loading anything
        self.remove_non_current_game_modules()
        # make copy of old modules table for import vs reload check
        old_modules = self.modules.copy()
        self.modules = {}
        # load/reload new modules
        for module_name in self.get_game_modules_list():
            # always reload built in modules
            if module_name in self.builtin_module_names or module_name in old_modules:
                self.modules[module_name] = importlib.reload(old_modules[module_name])
            else:
                self.modules[module_name] = importlib.import_module(module_name)
    
    def toggle_pause(self):
        self.paused = not self.paused
        s = 'Game %spaused.' % ['un', ''][self.paused]
        self.app.ui.message_line.post_line(s)
    
    def enable_player_camera_lock(self):
        if self.player:
            self.camera.focus_object = self.player
    
    def disable_player_camera_lock(self):
        # change only if player has focus
        if self.player and self.camera.focus_object is self.player:
            self.camera.focus_object = None
    
    def toggle_player_camera_lock(self):
        if self.player and self.camera.focus_object is self.player:
            self.disable_player_camera_lock()
        else:
            self.enable_player_camera_lock()
    
    def toggle_grid_snap(self):
        self.object_grid_snap = not self.object_grid_snap
    
    def handle_input(self, event, shift_pressed, alt_pressed, ctrl_pressed):
        # pass event's key to any objects that want to handle it
        if event.type != sdl2.SDL_KEYDOWN:
            return
        key = sdl2.SDL_GetKeyName(event.key.keysym.sym).decode()
        for obj in self.objects.values():
            if obj.handle_input_events:
                obj.handle_input(key, shift_pressed, alt_pressed, ctrl_pressed)
    
    def frame_begin(self):
        "runs at start of game loop iteration, before input/update/render"
        for obj in self.objects.values():
            obj.art.updated_this_tick = False
            obj.frame_begin()
    
    def frame_update(self):
        for obj in self.objects.values():
            obj.frame_update()
    
    def pre_update(self):
        # add newly spawned objects to table
        self.objects.update(self.new_objects)
        self.new_objects = {}
        # run object pre-updates
        for obj in self.objects.values():
            obj.pre_update()
        # run "first update" on all appropriate objects
        for obj in self.objects.values():
            if not obj.pre_first_update_run:
                obj.pre_first_update()
                obj.pre_first_update_run = True
        for room in self.rooms.values():
            if not room.pre_first_update_run:
                room.pre_first_update()
                room.pre_first_update_run = True
    
    def update(self):
        self.mouse_moved(self.app.mouse_dx, self.app.mouse_dy)
        if self.properties:
            self.properties.update_from_world()
        if not self.paused:
            # update objects based on movement, then resolve collisions
            for obj in self.objects.values():
                if obj.is_in_current_room() or obj.update_if_outside_room:
                    obj.update()
            if self.collision_enabled:
                self.cl.resolve_overlaps()
            for room in self.rooms.values():
                room.update()
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
        if len(to_destroy) > 0:
            self.app.ui.edit_list_panel.items_changed()
        if self.hud:
            self.hud.update()
    
    def render(self):
        visible_objects = []
        for obj in self.objects.values():
            obj.update_renderables()
            # filter out objects outside current room here
            # (if no current room or object is in no rooms, render it always)
            in_room = self.current_room is None or obj.is_in_current_room()
            hide_debug = obj.is_debug and not self.draw_debug_objects
            # respect object's "should render at all" flag
            if obj.visible and not hide_debug and \
               (self.show_all_rooms or in_room):
                visible_objects.append(obj)
        #
        # process non "Y sort" objects first
        #
        draw_order = []
        collision_items = []
        y_objects = []
        for obj in visible_objects:
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
    
    def save_last_state(self):
        "save over last loaded state"
        # strip down to base filename w/o extension :/
        last_state = self.last_state_loaded
        last_state = os.path.basename(last_state)
        last_state = os.path.splitext(last_state)[0]
        self.save_to_file(last_state)
    
    def save_to_file(self, filename=None):
        objects = []
        for obj in self.objects.values():
            if obj.should_save:
                objects.append(obj.get_dict())
        d = {'objects': objects}
        # save rooms if any exist
        if len(self.rooms) > 0:
            rooms = [room.get_dict() for room in self.rooms.values()]
            d['rooms'] = rooms
            if self.current_room:
                d['current_room'] = self.current_room.name
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
                # skip anything that's not a game class
                if not type(v) is type:
                    continue
                base_classes = (game_object.GameObject, game_hud.GameHUD, game_room.GameRoom)
                # TODO: find out why above works but below doesn't!!  O___O
                #base_classes = self.builtin_base_classes
                if issubclass(v, base_classes):
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
            self.app.log('%s created from %s' % (new_objects[0].name, obj.name))
        elif len(new_objects) > 1:
            self.app.log('%s new objects created' % len(new_objects))
    
    def duplicate_object(self, obj):
        d = obj.get_dict()
        # offset new object's location
        x, y = d['x'], d['y']
        x += obj.renderable.width
        y -= obj.renderable.height
        d['x'], d['y'] = x, y
        # new object needs a unique name, use a temp one until object exists
        # for real and we can give it a proper, more-likely-to-be-unique one
        d['name'] = obj.name + ' TEMP COPY NAME'
        new_obj = self.spawn_object_from_data(d)
        # give object a non-duplicate name
        self.rename_object(new_obj, new_obj.get_unique_name())
        # tell object's rooms about it
        for room_name in new_obj.rooms:
            self.world.rooms[room_name].add_object(new_obj)
        # update list after changes have been applied to object
        self.app.ui.edit_list_panel.items_changed()
        return new_obj
    
    def rename_object(self, obj, new_name):
        "gives specified object a new name. doesn't accept already-in-use names"
        self.objects.update(self.new_objects)
        for other_obj in self.objects.values():
            if not other_obj is self and other_obj.name == new_name:
                print("Can't rename %s to %s, name already in use" % (obj.name, new_name))
                return
        self.objects.pop(obj.name)
        old_name = obj.name
        obj.name = new_name
        self.objects[obj.name] = obj
        for room in self.rooms.values():
            if obj in room.objects.values():
                room.objects.pop(old_name)
                room.objects[obj.name] = self
    
    def spawn_object_of_class(self, class_name, x=None, y=None):
        if not class_name in self.classes:
            self.app.log("Couldn't find class %s" % class_name)
            return
        d = {'class_name': class_name}
        if x is not None and y is not None:
            d['x'], d['y'] = x, y
        new_obj = self.spawn_object_from_data(d)
        self.app.ui.edit_list_panel.items_changed()
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
    
    def add_room(self, new_room_name, new_room_classname='GameRoom'):
        if new_room_name in self.rooms:
            self.log('Room called %s already exists!' % new_room_name)
            return
        new_room_class = self.classes[new_room_classname]
        new_room = new_room_class(self, new_room_name)
        self.rooms[new_room.name] = new_room
    
    def remove_room(self, room_name):
        if not room_name in self.rooms:
            return
        room = self.rooms.pop(room_name)
        if room is self.current_room:
            self.current_room = None
        room.destroy()
    
    def change_room(self, new_room_name):
        if not new_room_name in self.rooms:
            self.app.log("Couldn't change to missing room %s" % new_room_name)
            return
        old_room = self.current_room
        self.current_room = self.rooms[new_room_name]
        # tell old and new rooms they've been exited and entered, respectively
        if old_room:
            old_room.exited(self.current_room)
        self.current_room.entered(old_room)
    
    def rename_room(self, room, new_room_name):
        old_name = room.name
        room.name = new_room_name
        self.rooms.pop(old_name)
        self.rooms[new_room_name] = room
        # update all objects in this room
        for obj in self.objects.values():
            if old_name in obj.rooms:
                obj.rooms.pop(old_name)
                obj.rooms[new_room_name] = room
    
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
        self.globals = self.spawn_object_of_class(self.globals_object_class_name, 0, 0)
        # just for first update, merge new objects list into objects list
        self.objects.update(self.new_objects)
        # create rooms
        for room_data in d.get('rooms', []):
            # get room class
            room_class_name = room_data.get('class_name', None)
            room_class = self.classes.get(room_class_name, game_room.GameRoom)
            room = room_class(self, room_data['name'], room_data)
            self.rooms[room.name] = room
        start_room = self.rooms.get(d.get('current_room', None), None)
        if start_room:
            self.change_room(start_room.name)
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
        self.app.ui.edit_list_panel.items_changed()
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
