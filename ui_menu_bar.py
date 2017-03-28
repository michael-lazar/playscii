from math import ceil

from ui_element import UIElement
from ui_button import UIButton, TEXT_LEFT, TEXT_CENTER, TEXT_RIGHT
from ui_menu_pulldown_item import FileMenuData, EditMenuData, ToolMenuData, ViewMenuData, ArtMenuData, FrameMenuData, LayerMenuData, CharColorMenuData, HelpMenuData
from ui_game_menu_pulldown_item import GameMenuData, GameStateMenuData, GameViewMenuData, GameWorldMenuData, GameRoomMenuData, GameObjectMenuData
from ui_info_dialog import AboutDialog
from ui_colors import UIColors
from renderable_sprite import UISpriteRenderable

class MenuButton(UIButton):
    caption = 'Base Class Menu Button'
    caption_justify = TEXT_CENTER
    # menu data is just a class w/ little more than a list of items, partly
    # so we don't have to list all the items here in a different module
    menu_data = None
    # styling
    normal_bg_color = UIColors.white
    hovered_bg_color = UIColors.lightgrey
    dimmed_bg_color = UIColors.lightgrey
    
    def __init__(self, element):
        UIButton.__init__(self, element)
        self.callback = self.open_pulldown
    
    def open_pulldown(self):
        # don't open menus if a dialog is up
        if self.element.ui.active_dialog:
            return
        # if clicking the same button twice, close it
        if self.element.active_menu_name == self.name:
            self.element.close_active_menu()
            return
        # close any existing menu before opening new one
        if self.element.active_menu_name:
            self.element.close_active_menu()
        # tell pulldown what's opening it, it can populate its items based on
        # our data
        self.pulldown.open_at(self)
        self.element.active_menu_name = self.name
        # set button state to be dimmed until menu is closed
        self.dimmed = True


# playscii logo button = normal UIButton, opens About screen directly
class PlaysciiMenuButton(UIButton):
    name = 'playscii'
    caption = '  '
    caption_justify = TEXT_CENTER
    width = len(caption) + 2
    normal_bg_color = MenuButton.normal_bg_color
    hovered_bg_color = MenuButton.hovered_bg_color
    dimmed_bg_color = MenuButton.dimmed_bg_color

#
# art mode menu buttons
#

class FileMenuButton(MenuButton):
    name = 'file'
    caption = 'File'
    menu_data = FileMenuData

class EditMenuButton(MenuButton):
    name = 'edit'
    caption = 'Edit'
    menu_data = EditMenuData

class ToolMenuButton(MenuButton):
    name = 'tool'
    caption = 'Tool'
    menu_data = ToolMenuData

class ViewMenuButton(MenuButton):
    name = 'view'
    caption = 'View'
    menu_data = ViewMenuData

class ArtMenuButton(MenuButton):
    name = 'art'
    caption = 'Art'
    menu_data = ArtMenuData

class FrameMenuButton(MenuButton):
    name = 'frame'
    caption = 'Frame'
    menu_data = FrameMenuData

class LayerMenuButton(MenuButton):
    name = 'layer'
    caption = 'Layer'
    menu_data = LayerMenuData

class CharColorMenuButton(MenuButton):
    name = 'char_color'
    caption = 'Char/Color'
    menu_data = CharColorMenuData

# (appears in both art and game mode menus)
class HelpMenuButton(MenuButton):
    name = 'help'
    caption = 'Help'
    menu_data = HelpMenuData

#
# game mode menu buttons
#

class GameMenuButton(MenuButton):
    name = 'game'
    caption = 'Game'
    menu_data = GameMenuData

class StateMenuButton(MenuButton):
    name = 'state'
    caption = 'State'
    menu_data = GameStateMenuData

class GameViewMenuButton(MenuButton):
    name = 'view'
    caption = 'View'
    menu_data = GameViewMenuData

class WorldMenuButton(MenuButton):
    name = 'world'
    caption = 'World'
    menu_data = GameWorldMenuData

class RoomMenuButton(MenuButton):
    name = 'room'
    caption = 'Room'
    menu_data = GameRoomMenuData

class ObjectMenuButton(MenuButton):
    name = 'object'
    caption = 'Object'
    menu_data = GameObjectMenuData

class ModeMenuButton(UIButton):
    caption_justify = TEXT_CENTER
    normal_bg_color = UIColors.black
    normal_fg_color = UIColors.white
    #hovered_bg_color = UIColors.lightgrey
    #dimmed_bg_color = UIColors.lightgrey

class ArtModeMenuButton(ModeMenuButton):
    caption = 'Game Mode'
    width = len(caption) + 2

class GameModeMenuButton(ModeMenuButton):
    caption = 'Art Mode'
    width = len(caption) + 2


class MenuBar(UIElement):
    
    "main menu bar element, has lots of buttons which control the pulldown"
    
    snap_top = True
    snap_left = True
    always_consume_input = True
    # buttons set in subclasses
    button_classes = []
    # button to toggle between art and game mode
    mode_button_class = None
    # empty tiles between each button
    button_padding = 1
    
    def __init__(self, ui):
        # bitmap icon for about menu button
        self.playscii_sprite = UISpriteRenderable(ui.app)
        self.mode_button = None
        UIElement.__init__(self, ui)
        self.active_menu_name = None
        # list of menu buttons that can be navigated etc
        self.menu_buttons = []
        x = PlaysciiMenuButton.width + self.button_padding
        for button_class in self.button_classes:
            button = button_class(self)
            button.width = len(button.caption) + 2
            button.x = x
            x += button.width + self.button_padding
            setattr(self, '%s_button' % button.name, button)
            # NOTE: callback already defined in MenuButton class,
            # menu data for pulldown with set in MenuButton subclass
            button.pulldown = self.ui.pulldown
            self.menu_buttons.append(button)
        playscii_button = PlaysciiMenuButton(self)
        playscii_button.callback = self.open_about
        # implement Playscii logo menu as a normal UIButton that opens
        # the About screen directly
        self.menu_buttons.append(playscii_button)
        self.reset_icon()
        # copy from menu buttons, any buttons past this point are not menus
        self.buttons = self.menu_buttons[:]
        # toggle mode button at far right
        if not self.mode_button_class:
            return
        self.mode_button = self.mode_button_class(self)
        self.mode_button.x = int(self.ui.width_tiles * self.ui.scale) - self.mode_button.width
        self.mode_button.callback = self.toggle_game_mode
        self.buttons.append(self.mode_button)
    
    def reset_icon(self):
        inv_aspect = self.ui.app.window_height / self.ui.app.window_width
        self.playscii_sprite.scale_x = self.art.quad_height * inv_aspect
        self.playscii_sprite.scale_y = self.art.quad_height
        self.playscii_sprite.x = -1 + self.art.quad_width
        self.playscii_sprite.y = 1 - self.art.quad_height
    
    def open_about(self):
        if self.ui.active_dialog:
            return
        self.ui.open_dialog(AboutDialog)
    
    def toggle_game_mode(self):
        if self.ui.active_dialog:
            return
        if not self.ui.app.game_mode:
            self.ui.app.enter_game_mode()
        else:
            self.ui.app.exit_game_mode()
        self.ui.app.update_window_title()
    
    def close_active_menu(self):
        # un-dim active menu button
        for button in self.menu_buttons:
            if button.name == self.active_menu_name:
                button.dimmed = False
                button.set_state('normal')
        self.active_menu_name = None
        self.ui.pulldown.visible = False
        self.ui.keyboard_focus_element = None
        self.ui.refocus_keyboard()
    
    def refresh_active_menu(self):
        if not self.ui.pulldown.visible:
            return
        for button in self.menu_buttons:
            if button.name == self.active_menu_name:
                # don't reset keyboard nav index
                self.ui.pulldown.open_at(button, False)
    
    def open_menu_by_name(self, menu_name):
        if not self.ui.app.can_edit:
            return
        for button in self.menu_buttons:
            if button.name == menu_name:
                button.callback()
    
    def open_menu_by_index(self, index):
        if index > len(self.menu_buttons) - 1:
            return
        # don't navigate to the about menu
        # (does this mean it's not accessible via kb-only? probably, that's fine)
        if self.menu_buttons[index].name == 'playscii':
            return
        self.menu_buttons[index].callback()
    
    def get_menu_index(self, menu_name):
        for i,button in enumerate(self.menu_buttons):
            if button.name == self.active_menu_name:
                return i
    
    def next_menu(self):
        i = self.get_menu_index(self.active_menu_name)
        self.open_menu_by_index(i + 1)
    
    def previous_menu(self):
        i = self.get_menu_index(self.active_menu_name)
        self.open_menu_by_index(i - 1)
    
    def reset_art(self):
        self.tile_width = ceil(self.ui.width_tiles * self.ui.scale)
        # must resize here, as window width will vary
        self.art.resize(self.tile_width, self.tile_height)
        # repaint bar contents
        bg = self.ui.colors.white
        fg = self.ui.colors.black
        self.art.clear_frame_layer(0, 0, bg, fg)
        # reposition right-justified mode switch button
        if self.mode_button:
            self.mode_button.x = int(self.ui.width_tiles * self.ui.scale) - self.mode_button.width
        # draw buttons, etc
        UIElement.reset_art(self)
        self.reset_icon()
    
    def render(self):
        UIElement.render(self)
        self.playscii_sprite.render()
    
    def destroy(self):
        UIElement.destroy(self)
        self.playscii_sprite.destroy()

class ArtMenuBar(MenuBar):
    button_classes = [FileMenuButton, EditMenuButton, ToolMenuButton,
                      ViewMenuButton, ArtMenuButton, FrameMenuButton,
                      LayerMenuButton, CharColorMenuButton, HelpMenuButton]
    mode_button_class = GameModeMenuButton

class GameMenuBar(MenuBar):
    button_classes = [GameMenuButton, StateMenuButton, GameViewMenuButton,
                      WorldMenuButton, RoomMenuButton, ObjectMenuButton,
                      HelpMenuButton]
    game_mode_visible = True
    mode_button_class = ArtModeMenuButton
