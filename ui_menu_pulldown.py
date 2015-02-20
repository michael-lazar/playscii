
from ui_element import UIElement
from ui_button import UIButton
from ui_colors import UIColors
from art import UV_NORMAL, UV_ROTATE90, UV_ROTATE180, UV_ROTATE270, UV_FLIPX, UV_FLIPY

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

class SeparatorMenuItem(PulldownMenuItem):
    pass

class FileSaveMenuItem(PulldownMenuItem):
    label = 'Save'
    command = 'save_art'

class FileSaveAsMenuItem(PulldownMenuItem):
    label = 'Save As...'
    command = 'save_art_as'

class FilePNGExportMenuItem(PulldownMenuItem):
    label = 'Export PNG'
    command = 'export_image'

class FileQuitMenuItem(PulldownMenuItem):
    label = 'Quit'
    command = 'quit'

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
    items = [FileSaveMenuItem, FileSaveAsMenuItem, FilePNGExportMenuItem, SeparatorMenuItem, FileQuitMenuItem]

class EditMenuData(PulldownMenuData):
    items = [EditCutMenuItem, EditCopyMenuItem, EditPasteMenuItem]


class PulldownMenu(UIElement):
    
    "element that's moved and resized based on currently active pulldown"
    
    label_shortcut_padding = 5
    visible = False
    bg_color = UIColors.lightgrey
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
        # draw
        fg = self.ui.colors.black
        self.art.clear_frame_layer(0, 0, self.bg_color, fg)
        self.draw_border(menu_button)
        # create as many buttons as needed, set their sizes, captions, callbacks
        self.buttons = []
        for i,item in enumerate(menu_button.menu_data.items):
            # skip button creation for separators, just draw a line
            if item is SeparatorMenuItem:
                for x in range(1, self.tile_width - 1):
                    self.art.set_tile_at(0, 0, x, i+1, self.border_horizontal_line_char, self.border_color)
                continue
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
    
    def draw_border(self, menu_button):
        "draws a fancy lil frame around the pulldown's edge"
        fg = self.border_color
        char = self.border_horizontal_line_char
        # top/bottom edges
        for x in range(self.tile_width):
            self.art.set_tile_at(0, 0, x, 0, char, fg)
            self.art.set_tile_at(0, 0, x, self.tile_height-1, char, fg)
        # left/right edges
        char = self.border_vertical_line_char
        for y in range(self.tile_height):
            self.art.set_tile_at(0, 0, 0, y, char, fg)
            self.art.set_tile_at(0, 0, self.tile_width-1, y, char, fg)
        # corners: bottom left, bottom right, top right
        char = self.border_corner_char
        x, y = 0, self.tile_height - 1
        xform = UV_FLIPY
        self.art.set_tile_at(0, 0, x, y, char, fg, None, xform)
        x = self.tile_width - 1
        xform = UV_ROTATE180
        self.art.set_tile_at(0, 0, x, y, char, fg, None, xform)
        y = 0
        xform = UV_FLIPX
        self.art.set_tile_at(0, 0, x, y, char, fg, None, xform)
        # gap beneath menu bar button
        for x in range(1, len(menu_button.caption) + 2):
            self.art.set_tile_at(0, 0, x, 0, 0)
        self.art.set_tile_at(0, 0, x, 0, char, fg, None, UV_FLIPY)
    
    def get_shortcut(self, menu_item):
        # get InputLord's binding from given menu item's command name,
        # return concise string for bind and the actual function it runs.
        def null():
            pass
        # special handling of SeparatorMenuItem, no command or label
        if menu_item is SeparatorMenuItem:
            return '', null
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
                # bind strings that start with _ will be disregarded
                if not (bind_tuple[0].startswith('_') and len(bind_tuple[0]) > 1):
                    shortcut += bind_tuple[0]
                return shortcut, command_function
        self.ui.app.log('Shortcut/command not found: %s' % menu_item.command)
        return '', null
