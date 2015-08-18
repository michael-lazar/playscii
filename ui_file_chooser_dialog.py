import os

from ui_chooser_dialog import ChooserDialog, ChooserItem, ChooserItemButton
from palette import Palette, PALETTE_DIR, PALETTE_EXTENSIONS
from charset import CharacterSet, CHARSET_DIR, CHARSET_FILE_EXTENSION
from ui_console import LoadCharSetCommand, LoadPaletteCommand

class BaseFileChooserDialog(ChooserDialog):
    
    "base class for choosers whose items correspond with files"
    
    def get_filenames(self):
        "subclasses override: get list of desired filenames"
        return []
    
    def get_description_filename(self, item):
        "returns a description-appropriate filename for given item"
        filename = item.filename
        # truncate from start to fit in description area if needed
        max_width = self.tile_width
        max_width -= self.item_start_x + ChooserItemButton.width + 5
        if len(filename) > max_width - 1:
            filename = '…' + filename[-max_width:]
        return filename
    
    def load_item(self, item_name):
        "subclasses override: return loaded item"
        return {}
    
    def get_items(self):
        "populate and return items from list of files, loading as needed"
        items = []
        # find all suitable files (images)
        filenames = self.get_filenames()
        filenames.sort()
        # use manual counter, as we skip past some files that don't fit
        i = 0
        for filename in filenames:
            item = ChooserItem()
            item.index = i
            # load item from filename
            item.data = self.load_item(filename)
            # data might be bad, bail
            if not hasattr(item.data, 'init_success') or not item.data.init_success:
                continue
            item.label = item.data.name
            items.append(item)
            i += 1
        return items


class PaletteChooserDialog(BaseFileChooserDialog):
    
    title = 'Choose palette'
    
    def get_selected_description_lines(self):
        item = self.get_selected_data()
        # display source filename and # of unique colors
        lines = [self.get_description_filename(item)]
        lines += ['Unique colors: %s' % str(len(item.colors) - 1)]
        return lines
    
    def get_initial_selection(self):
        for item in self.items:
            if item.data is self.ui.active_art.palette:
                return item.index
        print("couldn't find initial selection for %s, returning 0" % self.__class__.__name__)
        return 0
    
    def set_preview(self):
        pal = self.get_selected_data()
        self.preview_renderable.texture = pal.src_texture
    
    def get_filenames(self):
        filenames = []
        # search all files in dirs with appropriate extensions
        for dirname in self.ui.app.get_dirnames(PALETTE_DIR, False):
            for filename in os.listdir(dirname):
                for ext in PALETTE_EXTENSIONS:
                    if filename.lower().endswith(ext):
                        filenames.append(filename)
        return filenames
    
    def load_item(self, item_name):
        return self.ui.app.load_palette(item_name, False)
    
    def confirm_pressed(self):
        new_pal = self.get_selected_data()
        self.ui.active_art.set_palette(new_pal)
        self.ui.popup.set_active_palette(new_pal)


class CharSetChooserDialog(BaseFileChooserDialog):
    
    title = 'Choose character set'
    flip_preview_y = False
    
    def get_selected_description_lines(self):
        item = self.get_selected_data()
        lines = [self.get_description_filename(item)]
        lines += ['Characters: %s' % str(item.last_index)]
        return lines
    
    def get_initial_selection(self):
        for item in self.items:
            if item.data is self.ui.active_art.charset:
                return item.index
        print("couldn't find initial selection for %s, returning 0" % self.__class__.__name__)
        return 0
    
    def set_preview(self):
        charset = self.get_selected_data()
        self.preview_renderable.texture = charset.texture
    
    def get_filenames(self):
        filenames = []
        # search all files in dirs with appropriate extensions
        for dirname in self.ui.app.get_dirnames(CHARSET_DIR, False):
            for filename in os.listdir(dirname):
                if filename.lower().endswith(CHARSET_FILE_EXTENSION):
                    filenames.append(filename)
        return filenames
    
    def load_item(self, item_name):
        return self.ui.app.load_charset(item_name, False)
    
    def confirm_pressed(self):
        new_set = self.get_selected_data()
        self.ui.active_art.set_charset(new_set)
        self.ui.popup.set_active_charset(new_set)
