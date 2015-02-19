
from ui_element import UIElement
from ui_button import UIButton
from ui_colors import UIColors

#
# specific pulldown menu items, eg File > Save, Edit > Copy
#

class PulldownMenuItem:
    # label that displays for this item
    label = 'Test Menu Item'
    # bindable command we look up from InputLord to get binding text from
    command = 'test_command'

# TODO: this needs to invoke a dialog box, wait til that's implemented
#class FileOpenMenuItem(PulldownMenuItem):
#    label = 'Open'
#    command = 'open_art'

class FileSaveMenuItem(PulldownMenuItem):
    label = 'Save'
    command = 'save_art'

class FilePNGExportMenuItem(PulldownMenuItem):
    label = 'Export PNG'
    command = 'export_image'

class EditCutMenuItem(PulldownMenuItem):
    label = 'Cut'
    command = 'cut_selection'

class EditCopyMenuItem(PulldownMenuItem):
    label = 'Copy'
    command = 'copy_selection'

class EditPasteMenuItem(PulldownMenuItem):
    label = 'Paste'
    command = 'select_paste_tool'


class PulldownMenuData:
    "data for pulldown menus, eg File, Edit, etc; mainly a list of menu items"
    items = []

class FileMenuData(PulldownMenuData):
    items = [FileSaveMenuItem, FilePNGExportMenuItem]

class EditMenuData(PulldownMenuData):
    items = [EditCutMenuItem, EditCopyMenuItem, EditPasteMenuItem]


class PulldownMenu(UIElement):
    
    "element that's moved and resized based on currently active pulldown"
    
    label_shortcut_padding = 3
    visible = False
    border_color = UIColors.medgrey
    border_corner_char = 77
    border_horizontal_line_char = 78
    border_vertical_line_char = 79
    
    def open_at(self, menu_button):
        # set X and Y based on calling menu button's location
        self.tile_x = menu_button.x
        self.tile_y = menu_button.y + 1
        # determine pulldown width from longest item label length
        self.tile_width = 1
        # save shortcuts as we got through
        shortcuts = []
        callbacks = []
        for item in menu_button.menu_data.items:
            shortcut,command = self.get_shortcut(item)
            shortcuts.append(shortcut)
            callbacks.append(command)
            # get full width of item, label shortcut and some padding
            item_width = len(item.label) + self.label_shortcut_padding
            item_width += len(shortcut)
            if item_width > self.tile_width:
                self.tile_width = item_width
        self.tile_height = len(menu_button.menu_data.items) + 2
        self.art.resize(self.tile_width, self.tile_height)
        bg = self.ui.colors.white
        fg = self.ui.colors.black
        self.art.clear_frame_layer(0, 0, bg, fg)
        # TODO: draw fancy lil frame around buttons
        
        # create as many buttons as needed, set their sizes, captions, callbacks
        self.buttons = []
        for i,item in enumerate(menu_button.menu_data.items):
            button = UIButton(self)
            full_label = item.label
            full_label += shortcuts[i].rjust(self.tile_width - 2 - len(item.label))
            button.caption = full_label
            button.width = len(full_label)
            button.x = 1
            button.y = i+1
            button.callback = callbacks[i]
            self.buttons.append(button)
        # set our X and Y, draw buttons, etc
        self.reset_loc()
        self.reset_art()
        self.visible = True
    
    def get_shortcut(self, menu_item):
        # get InputLord's binding from given menu item's command name,
        # return concise string for bind and the actual function it runs
        binds = self.ui.app.il.edit_binds
        for bind_tuple in binds:
            command_function = binds[bind_tuple]
            if command_function.__name__ == 'BIND_%s' % menu_item.command:
                shortcut = ''
                # shift, alt, ctrl
                if bind_tuple[1]:
                    shortcut += 'Shift-'
                if bind_tuple[2]:
                    shortcut += 'Alt-'
                if bind_tuple[3]:
                    # TODO: cmd vs ctrl for mac vs non
                    shortcut += 'C-'
                shortcut += bind_tuple[0]
                return shortcut, command_function
        def null():
            pass
        return 'X', null
