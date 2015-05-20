import os

from ui_element import UIElement
from ui_button import UIButton
from ui_dialog import LoadGameStateDialog, SaveGameStateDialog, SetGameDirDialog
from ui_colors import UIColors

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
        button.element.ui.open_dialog(LoadGameStateDialog)

class SaveStateButton(UIButton):
    caption = 'Save game state...'
    def clicked(button):
        button.element.ui.open_dialog(SaveGameStateDialog)

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

class ToggleEditUIButton(UIButton):
    caption = '<< Hide edit UI'
    y = 0
    def clicked(button):
        button.element.ui.toggle_game_edit_ui()

class GamePanel(UIElement):
    "base class of game edit UI panels"
    tile_width = 32
    tile_y = 5
    game_mode_visible = True
    fg_color = UIColors.black
    bg_color = UIColors.lightgrey
    titlebar_fg = UIColors.white
    titlebar_bg = UIColors.darkgrey
    text_left = True
    
    # label and main item draw functions - overridden in subclasses
    def get_label(self): pass
    def draw_items(self): pass
    
    def draw_titlebar(self):
        self.art.clear_line(0, 0, 0, self.titlebar_fg, self.titlebar_bg)
        label = self.get_label()
        if self.text_left:
            self.art.write_string(0, 0, 0, 0, label)
        else:
            self.art.write_string(0, 0, -1, 0, label, None, None, True)
    
    def reset_art(self):
        self.art.clear_frame_layer(0, 0, self.bg_color, self.fg_color)
        self.draw_titlebar()
        self.draw_items()
        UIElement.reset_art(self)
    
    def clicked(self, button):
        if self.ui.active_dialog:
            return
        UIElement.clicked(self, button)
    
    def render(self):
        if self.ui.app.game_mode:
            UIElement.render(self)


class EditGamePanel(GamePanel):
    tile_y = 5
    snap_left = True
    button_classes = [SetGameDirButton, ResetStateButton, LoadStateButton,
                      SaveStateButton, SpawnObjectButton, SelectObjectsButton,
                      ToggleEditUIButton]
    tile_height = len(button_classes) + 1
    
    def __init__(self, ui):
        GamePanel.__init__(self, ui)
        self.buttons = []
        for i,button_class in enumerate(self.button_classes):
            button = button_class(self)
            button.width = self.tile_width
            button.y = i + 1
            button.callback = button.clicked
            button.caption = ' %s' % button.caption
            self.buttons.append(button)
        self.list_panel = self.ui.edit_list_panel
    
    def get_label(self):
        l = ' %s' % self.ui.app.gw.game_dir
        if self.ui.app.gw.last_state_loaded:
            l += self.ui.app.gw.last_state_loaded
        return l


class EditListPanel(GamePanel):
    tile_y = EditGamePanel.tile_y + EditGamePanel.tile_height + 1
    # height will change based on how many items in list
    tile_height = 10
    snap_left = True
    titlebar = 'List titlebar'
    items = {}
    
    def list_classes(self):
        class_table = {}
        # TODO: get list of available classes (probably from GameWorld)
        self.items = class_table
    
    def list_objects(self):
        self.items = {}
        for obj in self.ui.app.gw.objects:
            self.items[obj.name] = obj
        self.titlebar = 'Objects:'
    
    def get_label(self):
        return self.titlebar
    
    def draw_items(self):
        for y,name in enumerate(self.items):
            obj = self.items[name]
            fg, bg = self.fg_color, self.bg_color
            if obj in self.ui.app.gw.selected_objects:
                fg, bg = self.bg_color, self.fg_color
            self.art.clear_line(0, 0, y+1, fg, bg)
            self.art.write_string(0, 0, 1, y+1, name)
    
    def update(self):
        # redraw contents every update
        self.draw_titlebar()
        self.draw_items()
        GamePanel.update(self)


class EditObjectPanel(GamePanel):
    
    "panel showing info for selected game object"
    
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
    
    def draw_items(self):
        selected = len(self.ui.app.gw.selected_objects)
        if selected == 0:
            return
        obj = self.ui.app.gw.selected_objects[0]
        # list each serialized property on its own line
        for y,propname in enumerate(obj.serialized):
            if y > self.tile_height:
                break
            self.art.clear_line(0, 0, y+1, self.fg_color, self.bg_color)
            # if multiple selected, clear line but don't write anything
            if selected > 1:
                continue
            s = '%s: ' % propname
            value = getattr(obj, propname)
            if type(value) is float:
                s += '%.3f' % value
            elif type(value) is str:
                # file? shorten to basename minus extension
                if os.path.exists:
                    filename = os.path.basename(value)
                    filename = os.path.splitext(filename)[0]
                    s += filename
                else:
                    s += value
            else:
                s += str(value)
            self.art.write_string(0, 0, -1, y+1, s, None, None, True)
    
    def update(self):
        # redraw contents every update
        self.draw_titlebar()
        if len(self.ui.app.gw.selected_objects) > 0:
            self.draw_items()
        GamePanel.update(self)
    
    def render(self):
        if len(self.ui.app.gw.selected_objects) > 0:
            GamePanel.render(self)
