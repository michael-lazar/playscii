
import os, time, json

from PIL import Image

from texture import Texture
from ui_chooser_dialog import ChooserDialog, ChooserItem, ChooserItemButton
from ui_console import OpenCommand, LoadCharSetCommand, LoadPaletteCommand
from art import ART_DIR, ART_FILE_EXTENSION, THUMBNAIL_CACHE_DIR
from palette import Palette, PALETTE_DIR, PALETTE_EXTENSIONS
from charset import CharacterSet, CHARSET_DIR, CHARSET_FILE_EXTENSION
from image_export import write_thumbnail

class BaseFileChooserDialog(ChooserDialog):
    
    "base class for choosers whose items correspond with files"
    show_filenames = True
    
    def get_filenames(self):
        "subclasses override: get list of desired filenames"
        return []
    
    def get_items(self):
        "populate and return items from list of files, loading as needed"
        items = []
        # find all suitable files (images)
        filenames = self.get_filenames()
        # use manual counter, as we skip past some files that don't fit
        i = 0
        for filename in filenames:
            item = self.chooser_item_class(i, filename)
            if not item.valid:
                continue
            items.append(item)
            i += 1
        return items

#
# art chooser
#

class ArtChooserItem(ChooserItem):
    
    # set in load()
    art_width = None
    
    def get_short_dir_name(self):
        # name should end in / but don't assume
        dir_name = self.name[:-1] if self.name.endswith('/') else self.name
        return os.path.basename(dir_name) + '/'
    
    def get_label(self):
        if os.path.isdir(self.name):
            return self.get_short_dir_name()
        else:
            label = os.path.basename(self.name)
            return os.path.splitext(label)[0]
    
    def get_description_lines(self):
        if os.path.isdir(self.name):
            if self.name == '..':
                return ['[parent directory]']
            # TODO: # of items in dir?
            return []
        if not self.art_width:
            return []
        mod_time = time.gmtime(self.art_mod_time)
        mod_time = time.strftime('%Y-%m-%d %H:%M:%S', mod_time)
        lines = ['last change: %s' % mod_time]
        lines += ['%s x %s, %s frames, %s layers' % (self.art_width,
                                                     self.art_height,
                                                     self.art_frames,
                                                     self.art_layers)]
        lines += ['char: %s, pal: %s' % (self.art_charset, self.art_palette)]
        return lines
    
    def get_preview_texture(self, app):
        if os.path.isdir(self.name):
            return
        thumbnail_filename = app.cache_dir + THUMBNAIL_CACHE_DIR + self.art_hash + '.png'
        # create thumbnail if it doesn't exist
        if not os.path.exists(thumbnail_filename):
            write_thumbnail(app, self.name, thumbnail_filename)
        # read thumbnail
        img = Image.open(thumbnail_filename)
        img = img.convert('RGBA')
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        return Texture(img.tostring(), *img.size)
    
    def load(self, app):
        if os.path.isdir(self.name):
            return
        if not os.path.exists(self.name):
            return
        # get last modified time for description
        self.art_mod_time = os.path.getmtime(self.name)
        # get file's hash for unique thumbnail name
        self.art_hash = app.get_file_hash(self.name)
        # rather than load the entire art, just get some high level stats
        d = json.load(open(self.name))
        self.art_width, self.art_height = d['width'], d['height']
        self.art_frames = len(d['frames'])
        self.art_layers = len(d['frames'][0]['layers'])
        self.art_charset = d['charset']
        self.art_palette = d['palette']
    
    def picked(self, element):
        # if this is different from the last clicked item, pick it
        if element.selected_item_index != self.index:
            ChooserItem.picked(self, element)
            element.first_selection_made = True
            return
        # if we haven't yet clicked something in this view, require another
        # click before opening it (consistent double click behavior for
        # initial selections)
        if not element.first_selection_made:
            element.first_selection_made = True
            return
        if self.name == '..' and self.name != '/':
            new_dir = os.path.abspath(element.current_dir + '..')
            element.change_current_dir(new_dir)
        elif os.path.isdir(self.name):
            new_dir = element.current_dir + self.get_short_dir_name()
            element.change_current_dir(new_dir)
        else:
            element.confirm_pressed()
        element.first_selection_made = False


class ArtChooserDialog(BaseFileChooserDialog):
    
    title = 'Open art'
    confirm_caption = 'Open'
    cancel_caption = 'Cancel'
    chooser_item_class = ArtChooserItem
    flip_preview_y = False
    directory_aware = True
    
    def set_initial_dir(self):
        # TODO: IF no art in Documents dir yet, start in app/art/ for examples?
        # get last opened dir, else start in docs/game art dir
        if self.ui.app.last_art_dir:
            self.current_dir = self.ui.app.last_art_dir
        else:
            self.current_dir = self.ui.app.gw.game_dir if self.ui.app.gw.game_dir else self.ui.app.documents_dir
            self.current_dir += ART_DIR
        self.set_field_text(self.active_field, self.current_dir)
    
    def get_initial_selection(self):
        # first item in dir list
        return 0
    
    def get_filenames(self):
        # list parent, then dirs, then filenames with art extension
        parent = [] if self.current_dir == '/' else ['..']
        dirs, files = [], []
        for filename in os.listdir(self.current_dir):
            # skip unix-hidden files
            if filename.startswith('.'):
                continue
            full_filename = self.current_dir + filename
            if os.path.isdir(full_filename):
                dirs += [full_filename + '/']
            elif filename.endswith(ART_FILE_EXTENSION):
                files += [full_filename]
        dirs.sort()
        files.sort()
        return parent + dirs + files
    
    def confirm_pressed(self):
        if not os.path.exists(self.get_field_text(0)):
            return
        self.ui.app.last_art_dir = self.current_dir
        OpenCommand.execute(self.ui.console, [self.get_field_text(0)])
        self.dismiss()

#
# palette chooser
#

class PaletteChooserItem(ChooserItem):
    
    def get_label(self):
        return os.path.splitext(self.name)[0]
    
    def get_description_lines(self):
        colors = len(self.palette.colors)
        return ['Unique colors: %s' % str(colors - 1)]
    
    def get_preview_texture(self, app):
        return self.palette.src_texture
    
    def load(self, app):
        self.palette = app.load_palette(self.name)
    
    def picked(self, element):
        element.confirm_pressed()

class PaletteChooserDialog(BaseFileChooserDialog):
    
    title = 'Choose palette'
    chooser_item_class = PaletteChooserItem
    
    def get_initial_selection(self):
        if not self.ui.active_art:
            return 0
        for item in self.items:
            # depend on label being same as palette's internal name,
            # eg filename minus extension
            if item.label == self.ui.active_art.palette.name:
                return item.index
        #print("couldn't find initial selection for %s, returning 0" % self.__class__.__name__)
        return 0
    
    def get_filenames(self):
        filenames = []
        # search all files in dirs with appropriate extensions
        for dirname in self.ui.app.get_dirnames(PALETTE_DIR, False):
            for filename in os.listdir(dirname):
                for ext in PALETTE_EXTENSIONS:
                    if filename.lower().endswith(ext):
                        filenames.append(filename)
        filenames.sort()
        return filenames
    
    def confirm_pressed(self):
        item = self.get_selected_item()
        self.ui.active_art.set_palette(item.palette)
        self.ui.popup.set_active_palette(item.palette)

#
# charset chooser
#

class CharsetChooserItem(ChooserItem):
    
    def get_label(self):
        return os.path.splitext(self.name)[0]
    
    def get_description_lines(self):
        return ['Characters: %s' % str(self.charset.last_index)]
    
    def get_preview_texture(self, app):
        return self.charset.texture
    
    def load(self, app):
        self.charset = app.load_charset(self.name)
    
    def picked(self, element):
        element.confirm_pressed()

class CharSetChooserDialog(BaseFileChooserDialog):
    
    title = 'Choose character set'
    flip_preview_y = False
    chooser_item_class = CharsetChooserItem
    
    def get_initial_selection(self):
        if not self.ui.active_art:
            return 0
        for item in self.items:
            if item.label is self.ui.active_art.charset:
                return item.index
        #print("couldn't find initial selection for %s, returning 0" % self.__class__.__name__)
        return 0
    
    def get_filenames(self):
        filenames = []
        # search all files in dirs with appropriate extensions
        for dirname in self.ui.app.get_dirnames(CHARSET_DIR, False):
            for filename in os.listdir(dirname):
                if filename.lower().endswith(CHARSET_FILE_EXTENSION):
                    filenames.append(filename)
        filenames.sort()
        return filenames
    
    def confirm_pressed(self):
        item = self.get_selected_item()
        self.ui.active_art.set_charset(item.charset)
        self.ui.popup.set_active_charset(item.charset)
