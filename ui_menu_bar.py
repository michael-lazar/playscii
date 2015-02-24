from math import ceil

from ui_element import UIElement
from ui_button import UIButton, TEXT_LEFT, TEXT_CENTER, TEXT_RIGHT
from ui_menu_pulldown_item import FileMenuData, EditMenuData, ToolMenuData, ArtMenuData, FrameMenuData, LayerMenuData, HelpMenuData
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

class HelpMenuButton(MenuButton):
    name = 'help'
    caption = 'Help'
    menu_data = HelpMenuData


class MenuBar(UIElement):
    
    "main menu bar element, has lots of buttons which control the pulldown"
    
    snap_top = True
    snap_left = True
    button_classes = [FileMenuButton, EditMenuButton, ToolMenuButton, ArtMenuButton,
                      FrameMenuButton, LayerMenuButton, HelpMenuButton]
    # empty tiles between each button
    button_padding = 1
    
    def __init__(self, ui):
        # bitmap icon for about menu button
        self.playscii_sprite = UISpriteRenderable(ui.app)
        UIElement.__init__(self, ui)
        self.active_menu_name = None
        self.buttons = []
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
            self.buttons.append(button)
        playscii_button = PlaysciiMenuButton(self)
        playscii_button.callback = self.open_about
        # implement Playscii logo menu as a normal UIButton that opens
        # the About screen directly
        self.buttons.append(playscii_button)
        self.reset_icon()
    
    def reset_icon(self):
        inv_aspect = self.ui.app.window_height / self.ui.app.window_width
        self.playscii_sprite.scale_x = self.art.quad_height * inv_aspect
        self.playscii_sprite.scale_y = self.art.quad_height
        self.playscii_sprite.x = -1 + self.art.quad_width
        self.playscii_sprite.y = 1 - self.art.quad_height
    
    def open_about(self):
        self.ui.open_dialog(AboutDialog)
    
    def close_active_menu(self):
        # un-dim active menu button
        for button in self.buttons:
            if button.name == self.active_menu_name:
                button.dimmed = False
                button.set_state('normal')
        self.active_menu_name = None
        self.ui.pulldown.visible = False
    
    def refresh_active_menu(self):
        for button in self.buttons:
            if button.name == self.active_menu_name:
                self.ui.pulldown.open_at(button)
    
    def open_menu_by_name(self, menu_name):
        for button in self.buttons:
            if button.name == menu_name:
                button.callback()
    
    def reset_art(self):
        self.tile_width = ceil(self.ui.width_tiles * self.ui.scale)
        # must resize here, as window width will vary
        self.art.resize(self.tile_width, self.tile_height)
        # repaint bar contents
        bg = self.ui.colors.white
        fg = self.ui.colors.black
        self.art.clear_frame_layer(0, 0, bg, fg)
        # draw buttons, etc
        UIElement.reset_art(self)
        self.reset_icon()
    
    def render(self):
        UIElement.render(self)
        self.playscii_sprite.render()
    
    def destroy(self):
        UIElement.destroy(self)
        self.playscii_sprite.destroy()
