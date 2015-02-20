from math import ceil

from ui_element import UIElement
from ui_button import UIButton, TEXT_LEFT, TEXT_CENTER, TEXT_RIGHT
from ui_menu_pulldown import FileMenuData, EditMenuData
from ui_colors import UIColors

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
        if self.element.active_menu_name == self.name:
            self.element.close_active_menu()
            return
        # tell pulldown what's opening it, it can populate its items based on
        # our data
        self.pulldown.open_at(self)
        self.element.active_menu_name = self.name
        # set button state to be dimmed until menu is closed
        self.dimmed = True


# playscii logo button = normal UIButton, opens About screen directly
class PlaysciiMenuButton(UIButton):
    name = 'playscii'
    caption = '<3'
    caption_justify = TEXT_CENTER
    width = len(caption) + 2
    normal_bg_color = UIColors.white
    hovered_bg_color = UIColors.lightgrey
    dimmed_bg_color = UIColors.lightgrey

class FileMenuButton(MenuButton):
    name = 'file'
    caption = 'File'
    width = len(caption) + 2
    x = PlaysciiMenuButton.width + 2
    menu_data = FileMenuData

class EditMenuButton(MenuButton):
    name = 'edit'
    caption = 'Edit'
    width = len(caption) + 2
    x = FileMenuButton.x + FileMenuButton.width + 2
    menu_data = EditMenuData


class MenuBar(UIElement):
    
    "main menu bar element, has lots of buttons which control the pulldown"
    
    snap_top = True
    snap_left = True
    button_classes = [FileMenuButton, EditMenuButton]
    
    def __init__(self, ui):
        UIElement.__init__(self, ui)
        self.active_menu_name = None
        self.buttons = []
        for button_class in self.button_classes:
            button = button_class(self)
            setattr(self, '%s_button' % button.name, button)
            # NOTE: callback already defined in MenuButton class,
            # menu data for pulldown with set in MenuButton subclass
            button.pulldown = self.ui.pulldown
            self.buttons.append(button)
        playscii_button = PlaysciiMenuButton(self)
        playscii_button.callback = self.open_about()
        # implement Playscii logo menu as a normal UIButton that opens
        # the About screen directly
        self.buttons.append(playscii_button)
    
    def open_about(self):
        # TODO: about screen based on dialog box
        self.ui.message_line.post_line('<3')
    
    def close_active_menu(self):
        # un-dim active menu button
        for button in self.buttons:
            if button.name == self.active_menu_name:
                button.dimmed = False
                button.set_state('normal')
        self.active_menu_name = None
        self.ui.pulldown.visible = False
    
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
