import os

from ui_element import UIElement
from ui_button import UIButton
from ui_game_dialog import LoadGameStateDialog, SaveGameStateDialog
from ui_chooser_dialog import ScrollArrowButton
from ui_colors import UIColors

from game_world import TOP_GAME_DIR, STATE_FILE_EXTENSION
from ui_list_operations import LO_NONE, LO_SELECT_OBJECTS, LO_SET_SPAWN_CLASS, LO_LOAD_STATE, LO_SET_ROOM, LO_SET_ROOM_OBJECTS, LO_SET_OBJECT_ROOMS, LO_OPEN_GAME_DIR, LO_SET_ROOM_EDGE_WARP, LO_SET_ROOM_EDGE_OBJ, LO_SET_ROOM_CAMERA


class GamePanel(UIElement):
    "base class of game edit UI panels"
    tile_y = 5
    game_mode_visible = True
    fg_color = UIColors.black
    bg_color = UIColors.lightgrey
    titlebar_fg = UIColors.white
    titlebar_bg = UIColors.darkgrey
    text_left = True
    support_keyboard_navigation = True
    support_scrolling = True
    keyboard_nav_offset = -2
    
    def __init__(self, ui):
        self.ui = ui
        self.world = self.ui.app.gw
        UIElement.__init__(self, ui)
        self.buttons = []
        self.create_buttons()
        self.keyboard_nav_index = 0
    
    def create_buttons(self): pass
    # label and main item draw functions - overridden in subclasses
    def get_label(self): pass
    def refresh_items(self): pass
    
    # reset all buttons to default state
    def clear_buttons(self, button_list=None):
        buttons = button_list or self.buttons
        for button in buttons:
            self.reset_button(button)
    
    def reset_button(self, button):
        button.normal_fg_color = UIButton.normal_fg_color
        button.normal_bg_color = UIButton.normal_bg_color
        button.hovered_fg_color = UIButton.hovered_fg_color
        button.hovered_bg_color = UIButton.hovered_bg_color
        button.can_hover = True
    
    def highlight_button(self, button):
        button.normal_fg_color = UIButton.clicked_fg_color
        button.normal_bg_color = UIButton.clicked_bg_color
        button.hovered_fg_color = UIButton.clicked_fg_color
        button.hovered_bg_color = UIButton.clicked_bg_color
        button.can_hover = True
    
    def draw_titlebar(self):
        # only shade titlebar if panel has keyboard focus
        fg = self.titlebar_fg if self is self.ui.keyboard_focus_element else self.fg_color
        bg = self.titlebar_bg if self is self.ui.keyboard_focus_element else self.bg_color
        self.art.clear_line(0, 0, 0, fg, bg)
        label = self.get_label()
        if len(label) > self.tile_width:
            label = label[:self.tile_width]
        if self.text_left:
            self.art.write_string(0, 0, 0, 0, label)
        else:
            self.art.write_string(0, 0, -1, 0, label, None, None, True)
    
    def reset_art(self):
        self.art.clear_frame_layer(0, 0, self.bg_color, self.fg_color)
        self.draw_titlebar()
        self.refresh_items()
        UIElement.reset_art(self)
    
    def clicked(self, mouse_button):
        # always handle input, even if we didn't hit a button
        UIElement.clicked(self, mouse_button)
        return True
    
    def hovered(self):
        # mouse hover on focus
        if self.ui.app.mouse_dx or self.ui.app.mouse_dy and \
           not self is self.ui.keyboard_focus_element:
            self.ui.keyboard_focus_element = self
            if self.ui.active_dialog:
                self.ui.active_dialog.reset_art()


class ListButton(UIButton):
    width = 28
    clear_before_caption_draw = True

class ListScrollArrowButton(ScrollArrowButton):
    x = ListButton.width
    normal_bg_color = UIButton.normal_bg_color

class ListScrollUpArrowButton(ListScrollArrowButton):
    y = 1

class ListScrollDownArrowButton(ListScrollArrowButton):
    up = False

class EditListPanel(GamePanel):
    tile_width = ListButton.width + 1
    tile_y = 5
    scrollbar_shade_char = 54
    # height will change based on how many items in list
    tile_height = 30
    snap_left = True
    spawn_msg = 'Click anywhere in the world view to spawn a %s'
    # transient state
    titlebar = 'List titlebar'
    items = []
    # text helping user know how to bail
    cancel_tip = 'ESC cancels'
    list_operation_labels = {
        LO_NONE: 'Stuff:',
        LO_SELECT_OBJECTS: 'Select objects:',
        LO_SET_SPAWN_CLASS: 'Class to spawn:',
        LO_LOAD_STATE: 'State to load:',
        LO_SET_ROOM: 'Change room:',
        LO_SET_ROOM_OBJECTS: "Set objects for %s:",
        LO_SET_OBJECT_ROOMS: "Set rooms for %s:",
        LO_OPEN_GAME_DIR: 'Open game:',
        LO_SET_ROOM_EDGE_WARP: 'Set edge warp room/object:',
        LO_SET_ROOM_EDGE_OBJ: 'Set edge bounds object:',
        LO_SET_ROOM_CAMERA: 'Set room camera marker:'
    }
    list_operations_allow_kb_focus = [
        LO_SET_ROOM_EDGE_WARP,
        LO_SET_ROOM_EDGE_OBJ,
        LO_SET_ROOM_CAMERA
    ]
    
    class ListItem:
        def __init__(self, name, obj): self.name, self.obj = name, obj
        def __str__(self): return self.name
    
    def __init__(self, ui):
        # topmost index of items to show in view
        self.list_scroll_index = 0
        # list operation, ie what does clicking in list do
        self.list_operation = LO_NONE
        # save & restore a scroll index for each flavor of list
        self.scroll_indices = {}
        for list_op in self.list_operation_labels:
            self.scroll_indices[list_op] = 0
        # map list operations to list builder functions
        self.list_functions = {LO_NONE: self.list_none,
                               LO_SELECT_OBJECTS: self.list_objects,
                               LO_SET_SPAWN_CLASS: self.list_classes,
                               LO_LOAD_STATE: self.list_states,
                               LO_SET_ROOM: self.list_rooms,
                               LO_SET_ROOM_OBJECTS: self.list_objects,
                               LO_SET_OBJECT_ROOMS: self.list_rooms,
                               LO_OPEN_GAME_DIR: self.list_games,
                               LO_SET_ROOM_EDGE_WARP: self.list_rooms_and_objects,
                               LO_SET_ROOM_EDGE_OBJ: self.list_objects,
                               LO_SET_ROOM_CAMERA: self.list_objects
        }
        # map list operations to "item clicked" functions
        self.click_functions = {LO_SELECT_OBJECTS: self.select_object,
                                LO_SET_SPAWN_CLASS: self.set_spawn_class,
                                LO_LOAD_STATE: self.load_state,
                                LO_SET_ROOM: self.set_room,
                                LO_SET_ROOM_OBJECTS: self.set_room_object,
                                LO_SET_OBJECT_ROOMS: self.set_object_room,
                                LO_OPEN_GAME_DIR: self.open_game_dir,
                                LO_SET_ROOM_EDGE_WARP: self.set_room_edge_warp,
                                LO_SET_ROOM_EDGE_OBJ: self.set_room_bounds_obj,
                                LO_SET_ROOM_CAMERA: self.set_room_camera
        }
        # separate lists for item buttons vs other controls
        self.list_buttons = []
        # set when game resets
        self.should_reset_list = False
        GamePanel.__init__(self, ui)
    
    def create_buttons(self):
        def list_callback(item=None):
            if not item: return
            self.clicked_item(item)
        for y in range(self.tile_height-1):
            button = ListButton(self)
            button.y = y + 1
            button.callback = list_callback
            # button.cb_art set by refresh_items()
            self.list_buttons.append(button)
        self.buttons = self.list_buttons[:]
        self.up_button = ListScrollUpArrowButton(self)
        self.up_button.callback = self.scroll_list_up
        self.buttons.append(self.up_button)
        self.down_button = ListScrollDownArrowButton(self)
        self.down_button.callback = self.scroll_list_down
        # TODO: adjust height according to screen tile height
        self.down_button.y = self.tile_height - 1
        self.buttons.append(self.down_button)
    
    def reset_art(self):
        GamePanel.reset_art(self)
        x = self.tile_width - 1
        for y in range(1, self.tile_height):
            self.art.set_tile_at(0, 0, x, y, self.scrollbar_shade_char,
                                 UIColors.medgrey)
    
    def cancel(self):
        self.set_list_operation(LO_NONE)
        self.world.classname_to_spawn = None
    
    def scroll_list_up(self):
        if self.list_scroll_index > 0:
            self.list_scroll_index -= 1
    
    def scroll_list_down(self):
        max_scroll = len(self.items) - self.tile_height
        #max_scroll = len(self.element.items) - self.element.items_in_view
        if self.list_scroll_index <= max_scroll:
            self.list_scroll_index += 1
    
    def clicked_item(self, item):
        # do thing appropriate to current list operation
        self.click_functions[self.list_operation](item)
    
    def wheel_moved(self, wheel_y):
        if wheel_y > 0:
            self.scroll_list_up()
            return True
        if wheel_y < 0:
            self.scroll_list_down()
            return True
    
    def set_list_operation(self, new_op):
        "changes list type and sets new items"
        if new_op == LO_LOAD_STATE and not self.world.game_dir:
            return
        if new_op == LO_NONE:
            self.list_operation = new_op
            self.ui.keyboard_focus_element = None
            self.ui.refocus_keyboard()
            return
        # list is doing something, set us as keyboard focus
        # (but not if a dialog just came up)
        if not self.ui.active_dialog:
            self.ui.keyboard_focus_element = self
        self.items = []
        self.clear_buttons(self.list_buttons)
        # save old list type's scroll index so we can restore it later
        self.scroll_indices[self.list_operation] = self.list_scroll_index
        self.list_operation = new_op
        self.items = self.list_functions[self.list_operation]()
        # restore saved scroll index for new list type
        self.list_scroll_index = self.scroll_indices[self.list_operation]
        # keep in bounds if list size changed since last view
        self.list_scroll_index = min(self.list_scroll_index, len(self.items))
    
    def get_label(self):
        label = '%s (%s)' % (self.list_operation_labels[self.list_operation], self.cancel_tip)
        # some labels contain variables
        if '%s' in label:
            if self.list_operation == LO_SET_ROOM_OBJECTS:
                if self.world.current_room:
                    label %= self.world.current_room.name
            elif self.list_operation == LO_SET_OBJECT_ROOMS:
                if len(self.world.selected_objects) == 1:
                    label %= self.world.selected_objects[0].name
        return label
    
    def should_highlight(self, item):
        if self.list_operation == LO_SELECT_OBJECTS:
            return item.obj in self.world.selected_objects
        elif self.list_operation == LO_SET_SPAWN_CLASS:
            return item.name == self.world.classname_to_spawn
        elif self.list_operation == LO_LOAD_STATE:
            last_gs = os.path.basename(self.world.last_state_loaded)
            last_gs = os.path.splitext(last_gs)[0]
            return item.name == last_gs
        elif self.list_operation == LO_SET_ROOM:
            return self.world.current_room and item.name == self.world.current_room.name
        elif self.list_operation == LO_SET_ROOM_OBJECTS:
            return self.world.current_room and item.name in self.world.current_room.objects
        elif self.list_operation == LO_SET_OBJECT_ROOMS:
            return len(self.world.selected_objects) == 1 and item.name in self.world.selected_objects[0].rooms
        return False
    
    def game_reset(self):
        self.should_reset_list = True
    
    def items_changed(self):
        "called by anything that changes the items list, eg object add/delete"
        self.items = self.list_functions[self.list_operation]()
        # change selected item index if it's OOB
        if self.keyboard_nav_index >= len(self.items):
            self.keyboard_nav_index = len(self.items) - 1
    
    def refresh_items(self):
        for i,b in enumerate(self.list_buttons):
            if i >= len(self.items):
                b.caption = ''
                b.cb_arg = None
                self.reset_button(b)
                b.can_hover = False
            else:
                index = self.list_scroll_index + i
                item = self.items[index]
                b.cb_arg = item
                b.caption = item.name[:self.tile_width - 1]
                b.can_hover = True
                # change button appearance if this item should remain
                # highlighted/selected
                if self.should_highlight(item):
                    self.highlight_button(b)
                else:
                    self.reset_button(b)
        self.draw_buttons()
    
    def post_keyboard_navigate(self):
        # check for scrolling
        if len(self.items) <= len(self.list_buttons):
            return
        # wrap if at end of list
        if self.keyboard_nav_index + self.list_scroll_index >= len(self.items):
            self.keyboard_nav_index = 0
            self.list_scroll_index = 0
        # scroll down
        elif self.keyboard_nav_index >= len(self.list_buttons):
            self.scroll_list_down()
            self.keyboard_nav_index -= 1
        # wrap if at top of list
        elif self.list_scroll_index == 0 and self.keyboard_nav_index < 0:
            self.list_scroll_index = len(self.items) - len(self.list_buttons)
            self.keyboard_nav_index = len(self.list_buttons) - 1
        # scroll up
        elif self.keyboard_nav_index < 0:
            self.scroll_list_up()
            self.keyboard_nav_index += 1
    
    def update(self):
        if self.should_reset_list:
            self.set_list_operation(self.list_operation)
            self.should_reset_list = False
        # redraw contents every update
        self.draw_titlebar()
        self.refresh_items()
        GamePanel.update(self)
        self.renderable.alpha = 1 if self is self.ui.keyboard_focus_element else 0.5
    
    def is_visible(self):
        return GamePanel.is_visible(self) and self.list_operation != LO_NONE
    
    #
    # list functions
    #
    def list_classes(self):
        items = []
        base_class = self.world.modules['game_object'].GameObject
        # get list of available classes from GameWorld
        for classname,classdef in self.world._get_all_loaded_classes().items():
            # ignore non-GO classes, eg GameRoom, GameHUD
            if not issubclass(classdef, base_class):
                continue
            if classdef.exclude_from_class_list:
                continue
            item = self.ListItem(classname, classdef)
            items.append(item)
        # sort classes alphabetically
        items.sort(key=lambda i: i.name)
        return items
    
    def list_objects(self):
        items = []
        # include just-spawned objects too
        all_objects = self.world.objects.copy()
        all_objects.update(self.world.new_objects)
        for obj in all_objects.values():
            if obj.exclude_from_object_list:
                continue
            if self.world.list_only_current_room_objects and not self.world.current_room.name in obj.rooms:
                continue
            li = self.ListItem(obj.name, obj)
            items.append(li)
        # sort object names alphabetically
        items.sort(key=lambda i: i.name)
        return items
    
    def list_states(self):
        items = []
        # list state files in current game dir
        for filename in os.listdir(self.world.game_dir):
            if filename.endswith('.' + STATE_FILE_EXTENSION):
                li = self.ListItem(filename[:-3], None)
                items.append(li)
        items.sort(key=lambda i: i.name)
        return items
    
    def list_rooms(self):
        items = []
        for room in self.world.rooms.values():
            li = self.ListItem(room.name, room)
            items.append(li)
        items.sort(key=lambda i: i.name)
        return items
    
    def list_games(self):
        def get_dirs(dirname):
            dirs = []
            for filename in os.listdir(dirname):
                if os.path.isdir(dirname + filename):
                    dirs.append(filename)
            return dirs
        # get list of both app dir games and user dir games
        docs_game_dir = self.ui.app.documents_dir + TOP_GAME_DIR
        items = []
        game_dirs = get_dirs(TOP_GAME_DIR) + get_dirs(docs_game_dir)
        game_dirs.sort()
        for game in game_dirs:
            li = self.ListItem(game, None)
            items.append(li)
        return items
    
    def list_rooms_and_objects(self):
        items = self.list_rooms()
        # prefix room names with "ROOM:"
        for i,item in enumerate(items):
            item.name = 'ROOM: %s' % item.name
        items += self.list_objects()
        return items
    
    def list_none(self):
        return []
    
    #
    # "clicked list item" functions
    #
    def select_object(self, item):
        # add to/remove from/overwrite selected list based on mod keys
        if self.ui.app.il.ctrl_pressed:
            self.world.deselect_object(item.obj)
        elif self.ui.app.il.shift_pressed:
            self.world.select_object(item.obj, force=True)
        else:
            self.world.deselect_all()
            self.world.select_object(item.obj, force=True)
    
    def set_spawn_class(self, item):
        # set this class to be the one spawned when GameWorld is clicked
        self.world.classname_to_spawn = item.name
        self.ui.message_line.post_line(self.spawn_msg % self.world.classname_to_spawn, 5)
    
    def load_state(self, item):
        self.world.load_game_state(item.name)
    
    def set_room(self, item):
        self.world.change_room(item.name)
    
    def set_room_object(self, item):
        # add/remove object from current room
        if item.name in self.world.current_room.objects:
            self.world.current_room.remove_object_by_name(item.name)
        else:
            self.world.current_room.add_object_by_name(item.name)
    
    def set_object_room(self, item):
        # UI can only show a single object's rooms, do nothing if many selected
        if len(self.world.selected_objects) != 1:
            return
        # add if not in room, remove if in room
        obj = self.world.selected_objects[0]
        room = self.world.rooms[item.name]
        if room.name in obj.rooms:
            room.remove_object(obj)
        else:
            room.add_object(obj)
    
    def open_game_dir(self, item):
        self.world.set_game_dir(item.name, True)
    
    def set_room_edge_warp(self, item):
        dialog = self.ui.active_dialog
        dialog.field_texts[dialog.active_field] = item.obj.name
        self.ui.keyboard_focus_element = dialog
    
    def set_room_bounds_obj(self, item):
        dialog = self.ui.active_dialog
        dialog.field_texts[dialog.active_field] = item.obj.name
        self.ui.keyboard_focus_element = dialog
    
    def set_room_camera(self, item):
        dialog = self.ui.active_dialog
        dialog.field_texts[dialog.active_field] = item.obj.name
        self.ui.keyboard_focus_element = dialog
