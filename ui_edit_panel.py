import os

from ui_element import UIElement
from ui_button import UIButton
from ui_dialog import LoadGameStateDialog, SaveGameStateDialog, SetGameDirDialog
from ui_chooser_dialog import ScrollArrowButton
from ui_colors import UIColors

from game_world import STATE_FILE_EXTENSION

class ToggleEditUIButton(UIButton):
    caption = '<< Hide edit UI'
    y = 0
    def selected(button):
        button.element.ui.toggle_game_edit_ui()

class ToggleGameModeButton(UIButton):
    caption = 'Toggle Game Mode'
    y = 0
    def selected(button):
        button.element.ui.app.exit_game_mode()

class ResetStateButton(UIButton):
    caption = 'Reset'
    def selected(button):
        button.element.world.reset_game()


class PauseGameButton(UIButton):
    
    caption = 'blah'
    clear_before_caption_draw = True
    
    def refresh_caption(button):
        captions = ['Pause game', 'Unpause game']
        button.caption = ' %s' % captions[button.element.world.paused]
        button.draw_caption()
    
    def selected(button):
        button.element.world.toggle_pause()
        button.refresh_caption()


class SetGameDirButton(UIButton):
    caption = 'Set new game dir...'
    def selected(button):
        button.element.ui.open_dialog(SetGameDirDialog)
        button.element.highlight_button(button)

class LoadStateButton(UIButton):
    caption = 'Load game state...'
    def selected(button):
        button.element.list_panel.list_states()
        button.element.highlight_button(button)

class SaveStateButton(UIButton):
    caption = 'Save game state...'
    def selected(button):
        button.element.ui.open_dialog(SaveGameStateDialog)
        # show states in list for convenience
        button.element.list_panel.list_states()
        button.element.highlight_button(button)

class SpawnObjectButton(UIButton):
    caption = 'Spawn object...'
    def selected(button):
        # change list to show object classes
        button.element.list_panel.list_classes()
        button.element.highlight_button(button)

class DuplicateObjectButton(UIButton):
    caption = 'Duplicate selected objects'
    def selected(button):
        button.element.world.duplicate_selected_objects()

class SelectObjectsButton(UIButton):
    caption = 'Select objects...'
    def selected(button):
        # change list to show objects
        button.element.list_panel.list_objects()
        button.element.highlight_button(button)

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

class TogglePlayerCameraLockButton(GameEditToggleButton):
    base_caption = 'Player camera lock:'
    caption_true, caption_false = 'On', 'Off'
    def get_caption_value(button):
        return button.element.world.player_camera_lock
    def selected(button):
        button.element.world.toggle_player_camera_lock()
        button.refresh_caption()

class ToggleGridSnapButton(GameEditToggleButton):
    base_caption = 'Object grid snap:'
    caption_true, caption_false = 'On', 'Off'
    def get_caption_value(button):
        return button.element.world.object_grid_snap
    def selected(button):
        button.element.world.toggle_grid_snap()
        button.refresh_caption()

class ToggleOriginVizButton(GameEditToggleButton):
    base_caption = 'Object origins:'
    def get_caption_value(button):
        return button.element.ui.app.show_origin_all
    def selected(button):
        button.element.world.toggle_all_origin_viz()
        button.refresh_caption()

class ToggleBoundsVizButton(GameEditToggleButton):
    base_caption = 'Object bounds:'
    def get_caption_value(button):
        return button.element.ui.app.show_bounds_all
    def selected(button):
        button.element.world.toggle_all_bounds_viz()
        button.refresh_caption()

class ToggleCollisionVizButton(GameEditToggleButton):
    base_caption = 'Object collision:'
    def get_caption_value(button):
        return button.element.ui.app.show_collision_all
    def selected(button):
        button.element.world.toggle_all_collision_viz()
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
    
    def clicked(self, button):
        if self.ui.active_dialog:
            return False
        # always handle input, even if we didn't hit a button
        UIElement.clicked(self, button)
        return True


# list type constants
LIST_NONE, LIST_CLASSES, LIST_OBJECTS, LIST_STATES = 0, 1, 2, 3

class EditGamePanel(GamePanel):
    tile_width = 28
    tile_y = 5
    snap_left = True
    button_classes = [ToggleEditUIButton, ToggleGameModeButton,
                      SetGameDirButton, ResetStateButton, PauseGameButton,
                      LoadStateButton, SaveStateButton, SpawnObjectButton,
                      DuplicateObjectButton, SelectObjectsButton,
                      TogglePlayerCameraLockButton, ToggleGridSnapButton,
                      ToggleOriginVizButton,
                      ToggleBoundsVizButton, ToggleCollisionVizButton]
    tile_height = len(button_classes) + 1
    
    def __init__(self, ui):
        GamePanel.__init__(self, ui)
        self.list_panel = self.ui.edit_list_panel
    
    def create_buttons(self):
        for i,button_class in enumerate(self.button_classes):
            button = button_class(self)
            button.width = self.tile_width
            button.y = i + 1
            button.callback = button.selected
            # draw buttons with dynamic caption
            if button.clear_before_caption_draw:
                button.refresh_caption()
            else:
                button.caption = ' %s' % button.caption
            self.buttons.append(button)
    
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
    
    def clicked(self, button):
        self.world.classname_to_spawn = None
        self.list_panel.list_mode = LIST_NONE
        # reset all buttons
        self.clear_buttons()
        # draw to set proper visual state
        self.draw_buttons()
        return GamePanel.clicked(self, button)


class ListButton(UIButton):
    width = EditGamePanel.tile_width - 1
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
    tile_height = 12
    snap_left = True
    spawn_msg = 'Click anywhere in the world view to spawn a %s'
    # transient state
    titlebar = 'List titlebar'
    items = []
    
    class ListItem:
        def __init__(self, name, obj): self.name, self.obj = name, obj
        def __str__(self): return self.name
    
    def __init__(self, ui):
        # topmost index of items to show in view
        self.list_scroll_index = 0
        self.list_mode = LIST_NONE
        # separate lists for item buttons vs other controls
        self.list_buttons = []
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
                self.world.select_object(item.obj)
            else:
                self.world.deselect_all()
                self.world.select_object(item.obj)
        elif self.list_mode == LIST_STATES:
            self.world.load_game_state(item.name)
    
    def list_classes(self):
        self.items = []
        # get list of available classes from GameWorld
        for classname,classdef in self.world.get_all_loaded_classes().items():
            item = self.ListItem(classname, classdef)
            self.items.append(item)
        # sort classes alphabetically
        self.items.sort(key=lambda i: i.name)
        self.clear_buttons(self.list_buttons)
        self.titlebar = 'Object classes:'
        self.list_mode = LIST_CLASSES
    
    def list_objects(self):
        self.items = []
        self.clear_buttons(self.list_buttons)
        for obj in self.world.objects.values():
            li = self.ListItem(obj.name, obj)
            self.items.append(li)
        self.titlebar = 'Objects:'
        self.list_mode = LIST_OBJECTS
    
    def list_states(self):
        if not self.world.game_dir:
            return
        self.items = []
        self.clear_buttons(self.list_buttons)
        # list state files in current game dir
        for filename in os.listdir(self.world.game_dir):
            if filename.endswith('.' + STATE_FILE_EXTENSION):
                li = self.ListItem(filename[:-3], None)
                self.items.append(li)
        self.titlebar = 'States:'
        self.list_mode = LIST_STATES
    
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
                b.caption = item.name[:self.tile_width]
                b.can_hover = True
                # change button appearance if this item should remain
                # highlighted/selected
                if self.should_highlight(item):
                    self.highlight_button(b)
                else:
                    self.reset_button(b)
        self.draw_buttons()
    
    def update(self):
        # redraw contents every update
        self.draw_titlebar()
        self.refresh_items()
        GamePanel.update(self)
    
    def is_visible(self):
        return GamePanel.is_visible(self) and self.list_mode != LIST_NONE
