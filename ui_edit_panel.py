import os

from ui_element import UIElement
from ui_button import UIButton
from ui_dialog import LoadGameStateDialog, SaveGameStateDialog, SetGameDirDialog
from ui_chooser_dialog import ScrollArrowButton
from ui_colors import UIColors

from game_world import TOP_GAME_DIR, STATE_FILE_EXTENSION

class ToggleEditUIButton(UIButton):
    caption = '<< Hide edit UI'
    y = 0
    def clicked(button):
        button.element.ui.toggle_game_edit_ui()

class ResetStateButton(UIButton):
    caption = 'Reset'
    def clicked(button):
        button.element.ui.app.gw.reset_game()

class SetGameDirButton(UIButton):
    caption = 'Set new game dir...'
    def clicked(button):
        button.element.ui.open_dialog(SetGameDirDialog)

class LoadStateButton(UIButton):
    caption = 'Load game state...'
    def clicked(button):
        button.element.list_panel.list_states()

class SaveStateButton(UIButton):
    caption = 'Save game state...'
    def clicked(button):
        button.element.ui.open_dialog(SaveGameStateDialog)
        # show states in list for convenience
        button.element.list_panel.list_states()

class SpawnObjectButton(UIButton):
    caption = 'Spawn object...'
    def clicked(button):
        # change list to show object classes
        button.element.list_panel.list_classes()

class SelectObjectsButton(UIButton):
    caption = 'Select objects...'
    def clicked(button):
        # change list to show objects
        button.element.list_panel.list_objects()

class GameEditToggleButton(UIButton):
    "button whose caption reflects an on/off state"
    
    base_caption = 'Toggleable thing:'
    caption_true = 'Visible'
    caption_false = 'Hidden'
    caption = base_caption
    clear_before_caption_draw = True
    
    def get_caption_value(button):
        return True
    
    def refresh_caption(button):
        button.caption = ' %s ' % button.base_caption
        button.caption += [button.caption_true, button.caption_false][not button.get_caption_value()]
        button.draw_caption()

class ToggleOriginVizButton(GameEditToggleButton):
    base_caption = 'Object origins:'
    def get_caption_value(button):
        return button.element.ui.app.show_origin_all
    def clicked(button):
        button.element.ui.app.gw.toggle_all_origin_viz()
        button.refresh_caption()

class ToggleBoundsVizButton(GameEditToggleButton):
    base_caption = 'Object bounds:'
    def get_caption_value(button):
        return button.element.ui.app.show_bounds_all
    def clicked(button):
        button.element.ui.app.gw.toggle_all_bounds_viz()
        button.refresh_caption()

class ToggleCollisionVizButton(GameEditToggleButton):
    base_caption = 'Object collision:'
    def get_caption_value(button):
        return button.element.ui.app.show_collision_all
    def clicked(button):
        button.element.ui.app.gw.toggle_all_collision_viz()
        button.refresh_caption()

class GamePanel(UIElement):
    "base class of game edit UI panels"
    tile_y = 5
    game_mode_visible = True
    fg_color = UIColors.black
    bg_color = UIColors.lightgrey
    titlebar_fg = UIColors.white
    titlebar_bg = UIColors.darkgrey
    text_left = True
    
    # label and main item draw functions - overridden in subclasses
    def get_label(self): pass
    def refresh_items(self): pass
    
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
    
    def clicked(self, button):
        if self.ui.active_dialog:
            return False
        return UIElement.clicked(self, button)


# list type constants
LIST_NONE, LIST_CLASSES, LIST_OBJECTS, LIST_STATES = 0, 1, 2, 3

class EditGamePanel(GamePanel):
    tile_width = 26
    tile_y = 5
    snap_left = True
    button_classes = [ToggleEditUIButton, SetGameDirButton, ResetStateButton,
                      LoadStateButton, SaveStateButton, SpawnObjectButton,
                      SelectObjectsButton, ToggleOriginVizButton,
                      ToggleBoundsVizButton, ToggleCollisionVizButton]
    tile_height = len(button_classes) + 1
    
    def __init__(self, ui):
        self.world = ui.app.gw
        GamePanel.__init__(self, ui)
        self.buttons = []
        for i,button_class in enumerate(self.button_classes):
            button = button_class(self)
            button.width = self.tile_width
            button.y = i + 1
            button.callback = button.clicked
            # draw buttons with dynamic caption
            if button.clear_before_caption_draw:
                button.refresh_caption()
            else:
                button.caption = ' %s' % button.caption
            self.buttons.append(button)
        self.list_panel = self.ui.edit_list_panel
    
    def cancel(self):
        self.world.deselect_all()
        self.list_panel.list_mode = LIST_NONE
        self.world.classname_to_spawn = None
    
    def refresh_all_captions(self):
        for b in self.buttons:
            if hasattr(b, 'refresh_caption'):
                b.refresh_caption()
    
    def get_label(self):
        l = ' %s' % self.ui.app.gw.game_dir
        if self.world.last_state_loaded:
            l += self.world.last_state_loaded
        return l
    
    def clicked(self, button):
        self.world.classname_to_spawn = None
        self.list_panel.list_mode = LIST_NONE
        return GamePanel.clicked(self, button)


class ListButton(UIButton):
    width = 25
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
    tile_y = EditGamePanel.tile_y + EditGamePanel.tile_height + 1
    scrollbar_shade_char = 54
    # height will change based on how many items in list
    tile_height = 16
    snap_left = True
    spawn_msg = 'Click anywhere in the world view to spawn a %s'
    # transient state
    titlebar = 'List titlebar'
    items = []
    
    class ListItem:
        def __init__(self, name, obj): self.name, self.obj = name, obj
        def __str__(self): return self.name
    
    def __init__(self, ui):
        # separate lists for item buttons vs other controls
        self.list_buttons = []
        self.list_mode = LIST_NONE
        def list_callback(item):
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
        # topmost index of items to show in view
        self.list_scroll_index = 0
        GamePanel.__init__(self, ui)
    
    def reset_art(self):
        UIElement.reset_art(self)
        x = self.tile_width - 1
        for y in range(1, self.tile_height):
            self.art.set_tile_at(0, 0, x, y, self.scrollbar_shade_char,
                                 UIColors.medgrey)
    
    def scroll_list_up(self):
        if self.list_scroll_index > 0:
            self.list_scroll_index -= 1
    
    def scroll_list_down(self):
        max_scroll = len(self.items) - self.tile_height
        #max_scroll = len(self.element.items) - self.element.items_in_view
        if self.list_scroll_index < max_scroll:
            self.list_scroll_index += 1
    
    def clicked_item(self, item):
        # clear message line if not in class list
        # TODO: do this also for game edit panel buttons
        self.ui.message_line.post_line('')
        # check list type, do appropriate thing
        if self.list_mode == LIST_CLASSES:
            # set this class to be the one spawned when GameWorld is clicked
            self.ui.app.gw.classname_to_spawn = item.name
            self.ui.message_line.post_line(self.spawn_msg % self.ui.app.gw.classname_to_spawn, 5)
        elif self.list_mode == LIST_OBJECTS:
            # add to/remove from/overwrite selected list based on mod keys
            if self.ui.app.il.ctrl_pressed:
                self.ui.app.gw.deselect_object(item.obj)
            elif self.ui.app.il.shift_pressed:
                self.ui.app.gw.select_object(item.obj)
            else:
                self.ui.app.gw.deselect_all()
                self.ui.app.gw.select_object(item.obj)
        elif self.list_mode == LIST_STATES:
            self.ui.app.gw.load_game_state(item.name)
    
    def list_classes(self):
        self.items = []
        # get list of available classes from GameWorld
        for classname,classdef in self.ui.app.gw.get_all_loaded_classes().items():
            item = self.ListItem(classname, classdef)
            self.items.append(item)
        # sort classes alphabetically
        self.items.sort(key=lambda i: i.name)
        self.clear_buttons()
        self.titlebar = 'Object classes:'
        self.list_mode = LIST_CLASSES
    
    def list_objects(self):
        self.items = []
        self.clear_buttons()
        for obj in self.ui.app.gw.objects:
            li = self.ListItem(obj.name, obj)
            self.items.append(li)
        self.titlebar = 'Objects:'
        self.list_mode = LIST_OBJECTS
    
    def list_states(self):
        if not self.ui.app.gw.game_dir:
            return
        self.items = []
        self.clear_buttons()
        # list state files in current game dir
        game_path = TOP_GAME_DIR + self.ui.app.gw.game_dir
        for filename in os.listdir(game_path):
            if filename.endswith('.%s' % STATE_FILE_EXTENSION):
                li = self.ListItem(filename[:-3], None)
                self.items.append(li)
        self.titlebar = 'States:'
        self.list_mode = LIST_STATES
    
    def get_label(self):
        return self.titlebar
    
    def should_highlight(self, item):
        if self.list_mode == LIST_OBJECTS:
            if item.obj in self.ui.app.gw.selected_objects:
                return True
        elif self.list_mode == LIST_CLASSES:
            if item.name == self.ui.app.gw.classname_to_spawn:
                return True
        elif self.list_mode == LIST_STATES:
            # TODO: this doesn't work, though it doesn't matter too much
            if item.name == self.ui.app.gw.last_state_loaded:
                return True
        return False
    
    def clear_buttons(self):
        for b in self.list_buttons:
            b.normal_fg_color = UIButton.normal_fg_color
            b.normal_bg_color = UIButton.normal_bg_color
            b.hovered_fg_color = UIButton.hovered_fg_color
            b.hovered_bg_color = UIButton.hovered_bg_color
    
    def refresh_items(self):
        # prune any objects that have been deleted from items
        if self.list_mode == LIST_OBJECTS:
            for item in self.items:
                if not item.obj in self.ui.app.gw.objects:
                    self.items.remove(item)
        def reset_button(button):
            button.normal_fg_color = UIButton.normal_fg_color
            button.normal_bg_color = UIButton.normal_bg_color
            button.hovered_fg_color = UIButton.hovered_fg_color
            button.hovered_bg_color = UIButton.hovered_bg_color
        for i,b in enumerate(self.list_buttons):
            if i >= len(self.items):
                b.caption = ''
                b.can_hover = False
                reset_button(b)
            else:
                index = self.list_scroll_index + i
                item = self.items[index]
                b.cb_arg = item
                b.caption = item.name[:self.tile_width]
                b.can_hover = True
                # change button appearance if this item should remain
                # highlighted/selected
                if self.should_highlight(item):
                    b.normal_fg_color = UIButton.clicked_fg_color
                    b.normal_bg_color = UIButton.clicked_bg_color
                    b.hovered_fg_color = UIButton.clicked_fg_color
                    b.hovered_bg_color = UIButton.clicked_bg_color
                else:
                    reset_button(b)
        self.draw_buttons()
    
    def update(self):
        # redraw contents every update
        self.draw_titlebar()
        self.refresh_items()
        GamePanel.update(self)
    
    def clicked(self, button):
        if self.ui.active_dialog:
            return False
        return UIElement.clicked(self, button)
    
    def render(self):
        if self.list_mode != LIST_NONE:
            GamePanel.render(self)


class EditObjectPanel(GamePanel):
    
    "panel showing info for selected game object"
    tile_width = 32
    tile_height = 10
    snap_right = True
    text_left = False
    
    def get_label(self):
        # if 1 object seleted, show its name; if >1 selected, show #
        selected = len(self.ui.app.gw.selected_objects)
        # panel shouldn't draw when nothing selected, fill in anyway
        if selected == 0:
            return '[nothing selected]'
        elif selected == 1:
            return self.ui.app.gw.selected_objects[0].name
        else:
            return '[%s selected]' % selected
    
    def draw_obj_property_on_line(self, obj, propname, y):
        self.art.clear_line(0, 0, y+1, self.fg_color, self.bg_color)
        # if multiple selected, clear line but don't write anything
        # TODO: think about how to show common values for multiple objects
        if len(self.ui.app.gw.selected_objects) > 1:
            return
        value = getattr(obj, propname)
        if type(value) is float:
            valstr = '%.3f' % value
            # non-fixed decimal version may be shorter, if so use it
            if len(str(value)) < len(valstr):
                valstr = str(value)
        elif type(value) is str:
            # file? shorten to basename minus extension
            if os.path.exists:
                valstr = os.path.basename(value)
                valstr = os.path.splitext(valstr)[0]
            else:
                valstr = value
        else:
            valstr = str(value)
        self.art.write_string(0, 0, -1, y+1, valstr, None, None, True)
        fg = UIColors.darkgrey
        x = -len(valstr) - 1
        self.art.write_string(0, 0, x, y+1, '%s: ' % propname, fg, None, True)
    
    def refresh_items(self):
        if len(self.ui.app.gw.selected_objects) == 0:
            return
        obj = self.ui.app.gw.selected_objects[0]
        # list each serialized property on its own line
        for y,propname in enumerate(obj.serialized):
            if y < self.tile_height:
                self.draw_obj_property_on_line(obj, propname, y)
    
    def update(self):
        # redraw contents every update
        self.draw_titlebar()
        if len(self.ui.app.gw.selected_objects) > 0:
            self.refresh_items()
        GamePanel.update(self)
    
    def render(self):
        if len(self.ui.app.gw.selected_objects) > 0:
            GamePanel.render(self)
