import os
import sdl2

from renderable_sprite import SpriteRenderable
from ui_dialog import UIDialog
from ui_button import UIButton
from palette import Palette, PALETTE_DIR
from charset import CharacterSet, CHARSET_DIR, CHARSET_FILE_EXTENSION
from ui_console import LoadCharSetCommand, LoadPaletteCommand

class ChooserItemButton(UIButton):
    
    item_data = None
    width = 20
    
    def __init__(self, element):
        UIButton.__init__(self, element)
        self.callback = self.pick_item
    
    def pick_item(self):
        print('hi %s' % self.item_data)
        # TODO: update self.element.preview
        # TODO: update self.element.selected_item


class ChooserItem:
    label = 'Chooser item'
    data = 'data_filename.blah'
    preview = 'ui/logo.png'

class ChooserDialog(UIDialog):
    
    title = 'Chooser'
    confirm_caption = 'Choose'
    fields = 0
    tile_width, tile_height = 60, 20
    items_in_view = tile_height - 5
    item_start_x, item_start_y = 2, 3
    no_preview_label = 'No preview available!'
    item_button_class = ChooserItemButton
    
    def __init__(self, ui):
        UIDialog.__init__(self, ui)
        # preview SpriteRenderable (loaded on item change?)
        self.preview_renderable = SpriteRenderable(ui.app)
        self.position_preview()
        self.preview_renderable.scale_x = 0.25 * ui.scale
        self.preview_renderable.scale_y = 0.25 * ui.scale
        self.items = self.get_items()
        if len(self.items) > self.items_in_view:
            # TODO: if items list is longer, allow arrows click to "scroll" list
            pass
        for i,item in enumerate(self.items):
            # generate buttons from self.items
            # each button's callback loads charset/palette/whatev
            button = self.item_button_class(self)
            button.caption = item.label
            button.x = self.item_start_x
            button.y = i + self.item_start_y
            button.item_data = item.data
            self.buttons.append(button)
        self.reset_art()
    
    def select_item(self, item_button):
        pass
    
    def get_items(self):
        # TODO: map pickable items, preview images, stuff to load
        items = []
        for i in range(10):
            item = ChooserItem()
            item.label += ' %s' % i
            item.data += ' %s' % i
            items.append(item)
        return items
    
    def position_preview(self):
        self.preview_renderable.x = self.x
        self.preview_renderable.x += (self.tile_width * 0.4) * self.art.quad_width
        self.preview_renderable.y = self.y - (self.preview_renderable.scale_y / 2)
    
    def get_height(self, msg_lines):
        return self.tile_height
    
    def reset_art(self):
        # UIDialog does: clear window, draw titlebar and confirm/cancel buttons
        # doesn't: draw message or fields
        UIDialog.reset_art(self)
        # TODO: set selected state of each item button
        # draw scrollbars
        # draw "no preview available" text caption beneath thumbnail
    
    def update_drag(self, mouse_dx, mouse_dy):
        UIDialog.update_drag(self, mouse_dx, mouse_dy)
        # update thumbnail renderable's position too
        self.position_preview()
    
    def render(self):
        UIDialog.render(self)
        self.preview_renderable.render()


class PaletteChooserItemButton(ChooserItemButton):
    
    def pick_item(self):
        ChooserItemButton.pick_item(self)
        # run console command - single code path
        LoadPaletteCommand.execute(self.element.ui.console, [self.item_data])

class PaletteChooserDialog(ChooserDialog):
    title = 'Choose palette'
    item_button_class = PaletteChooserItemButton
    
    def get_items(self):
        items = []
        filenames = os.listdir(PALETTE_DIR)
        for filename in filenames:
            if not filename.lower().endswith('.png'):
                continue
            item = ChooserItem()
            item.label = os.path.splitext(filename)[0]
            item.data = filename
            items.append(item)
        return items


class CharSetChooserItemButton(ChooserItemButton):
    
    def pick_item(self):
        ChooserItemButton.pick_item(self)
        LoadCharSetCommand.execute(self.element.ui.console, [self.item_data])

class CharSetChooserDialog(ChooserDialog):
    title = 'Choose character set'
    item_button_class = CharSetChooserItemButton
    
    def get_items(self):
        items = []
        filenames = os.listdir(CHARSET_DIR)
        for filename in filenames:
            if not filename.lower().endswith(CHARSET_FILE_EXTENSION):
                continue
            item = ChooserItem()
            item.label = os.path.splitext(filename)[0]
            item.data = filename
            items.append(item)
        return items
