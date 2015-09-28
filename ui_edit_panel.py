import os

from ui_element import UIElement
from ui_button import UIButton
from ui_dialog import LoadGameStateDialog, SaveGameStateDialog, SetGameDirDialog
from ui_chooser_dialog import ScrollArrowButton
from ui_colors import UIColors

from game_world import STATE_FILE_EXTENSION

# list type constants
LIST_NONE, LIST_CLASSES, LIST_OBJECTS, LIST_STATES, LIST_GAMES, LIST_ROOMS = 0, 1, 2, 3, 4, 5

# list operations - tells list what to do when clicked
# TODO: finish this
LO_SELECT_OBJECTS = 0

list_operation_labels = {
    LO_SELECT_OBJECTS: 'Select objects:'
}

class GamePanel(UIElement):
    "base class of game edit UI panels"
    tile_y = 5
    game_mode_visible = True
    fg_color = UIColors.black
    bg_color = UIColors.lightgrey
    titlebar_fg = UIColors.white
    titlebar_bg = UIColors.darkgrey
    text_left = True
    
    def __init__(self, ui):
        self.ui = ui
        self.world = self.ui.app.gw
        UIElement.__init__(self, ui)
        self.buttons = []
        self.create_buttons()
    
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
        self.art.clear_line(0, 0, 0, self.titlebar_fg, self.titlebar_bg)
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
        if self.ui.active_dialog:
            return False
        # always handle input, even if we didn't hit a button
        UIElement.clicked(self, mouse_button)
        return True


class EditGamePanel(GamePanel):
    # TODO: delete this class once it's safe to
    tile_width = 28
    tile_y = 5
    snap_left = True
    button_classes = []
    tile_height = len(button_classes) + 1
    
    def __init__(self, ui):
        GamePanel.__init__(self, ui)
        self.list_panel = self.ui.edit_list_panel
    
    def cancel(self):
        self.world.deselect_all()
        self.list_panel.list_mode = LIST_NONE
        self.world.classname_to_spawn = None
        self.clear_buttons()
        self.draw_buttons()
    
    def refresh_all_captions(self):
        for b in self.buttons:
            if hasattr(b, 'refresh_caption'):
                b.refresh_caption()
    
    def get_label(self):
        return ' %s' % self.world.game_name
    
    def clicked(self, mouse_button):
        self.world.classname_to_spawn = None
        # reset all buttons
        self.clear_buttons()
        # draw to set proper visual state
        self.draw_buttons()
        return GamePanel.clicked(self, mouse_button)


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
    list_titlebar_text = {LIST_CLASSES: 'Object classes:',
                          LIST_OBJECTS: 'Objects:',
                          LIST_STATES: 'States:'}
    
    class ListItem:
        def __init__(self, name, obj): self.name, self.obj = name, obj
        def __str__(self): return self.name
    
    def __init__(self, ui):
        # topmost index of items to show in view
        self.list_scroll_index = 0
        # save & restore a scroll index for each type of list
        self.scroll_indices = {LIST_CLASSES: 0, LIST_OBJECTS: 0, LIST_STATES: 0}
        self.list_mode = LIST_NONE
        # map list type to list builder functions
        self.list_functions = {LIST_CLASSES: self.list_classes,
                               LIST_OBJECTS: self.list_objects,
                               LIST_STATES: self.list_states}
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
        self.world.deselect_all()
        self.list_mode = LIST_NONE
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
        # clear message line if not in class list
        # TODO: do this also for game edit panel buttons
        self.ui.message_line.post_line('')
        # check list type, do appropriate thing
        if self.list_mode == LIST_CLASSES:
            # set this class to be the one spawned when GameWorld is clicked
            self.world.classname_to_spawn = item.name
            self.ui.message_line.post_line(self.spawn_msg % self.world.classname_to_spawn, 5)
        elif self.list_mode == LIST_OBJECTS:
            # add to/remove from/overwrite selected list based on mod keys
            if self.ui.app.il.ctrl_pressed:
                self.world.deselect_object(item.obj)
            elif self.ui.app.il.shift_pressed:
                self.world.select_object(item.obj, force=True)
            else:
                self.world.deselect_all()
                self.world.select_object(item.obj, force=True)
        elif self.list_mode == LIST_STATES:
            self.world.load_game_state(item.name)
    
    def wheel_moved(self, wheel_y):
        if wheel_y > 0:
            self.scroll_list_up()
            return True
        if wheel_y < 0:
            self.scroll_list_down()
            return True
    
    def list_classes(self):
        # get list of available classes from GameWorld
        for classname,classdef in self.world.get_all_loaded_classes().items():
            item = self.ListItem(classname, classdef)
            self.items.append(item)
        # sort classes alphabetically
        self.items.sort(key=lambda i: i.name)
    
    def list_objects(self):
        for obj in self.world.objects.values():
            if obj.do_not_list:
                continue
            li = self.ListItem(obj.name, obj)
            self.items.append(li)
        # sort object names alphabetically
        self.items.sort(key=lambda i: i.name)
    
    def list_states(self):
        # list state files in current game dir
        for filename in os.listdir(self.world.game_dir):
            if filename.endswith('.' + STATE_FILE_EXTENSION):
                li = self.ListItem(filename[:-3], None)
                self.items.append(li)
        self.items.sort(key=lambda i: i.name)
    
    def set_list_mode(self, new_mode):
        "changes list type and sets new items"
        if new_mode == LIST_STATES and not self.world.game_dir:
            return
        if new_mode == LIST_NONE:
            self.list_mode = new_mode
            return
        self.items = []
        self.clear_buttons(self.list_buttons)
        # save old list type's scroll index so we can restore it later
        self.scroll_indices[self.list_mode] = self.list_scroll_index
        self.list_mode = new_mode
        self.titlebar = self.list_titlebar_text[self.list_mode]
        self.list_functions[self.list_mode]()
        # restore saved scroll index for new list type
        self.list_scroll_index = self.scroll_indices[self.list_mode]
        # keep in bounds if list size changed since last view
        self.list_scroll_index = min(self.list_scroll_index, len(self.items))
    
    def get_label(self):
        return self.titlebar
    
    def should_highlight(self, item):
        if self.list_mode == LIST_OBJECTS:
            if item.obj in self.world.selected_objects:
                return True
        elif self.list_mode == LIST_CLASSES:
            if item.name == self.world.classname_to_spawn:
                return True
        elif self.list_mode == LIST_STATES:
            last_gs = os.path.basename(self.world.last_state_loaded)
            last_gs = os.path.splitext(last_gs)[0]
            if item.name == last_gs:
                return True
        return False
    
    def game_reset(self):
        self.should_reset_list = True
    
    def refresh_items(self):
        # prune any objects that have been deleted from items
        if self.list_mode == LIST_OBJECTS:
            for item in self.items:
                if not item.obj in self.world.objects.values():
                    self.items.remove(item)
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
    
    def update(self):
        if self.should_reset_list:
            self.set_list_mode(self.list_mode)
            self.should_reset_list = False
        # redraw contents every update
        self.draw_titlebar()
        self.refresh_items()
        GamePanel.update(self)
    
    def is_visible(self):
        return GamePanel.is_visible(self) and self.list_mode != LIST_NONE
