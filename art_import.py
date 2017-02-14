
import os, traceback

from art import Art, ART_FILE_EXTENSION
from ui_file_chooser_dialog import GenericImportChooserDialog

class ArtImporter:
    
    """
    Class for creating a new Art from data in non-Playscii format.
    Import logic happens in run_import; importer authors simply extend this
    class, override run_import and the class properties below.
    """
    
    format_name = 'ERROR - ArtImporter.format_name'
    "User-visible name for this format, shown in import chooser."
    format_description = "ERROR - ArtImporter.format_description"
    "String (can be triple-quoted) describing format, shown in import chooser."
    allowed_file_extensions = []
    "List of file extensions for this format - if empty, any file is accepted."
    file_chooser_dialog_class = GenericImportChooserDialog
    """
    BaseFileChooserDialog subclass for picking files. Only needed for things
    like custom preview images.
    """
    options_dialog_class = None
    "UIDialog subclass exposing import options to user."
    
    def __init__(self, app, in_filename, options={}):
        self.app = app
        new_filename = '%s.%s' % (os.path.splitext(in_filename)[0],
                                  ART_FILE_EXTENSION)
        self.art = self.app.new_art(new_filename)
        self.app.set_new_art_for_edit(self.art)
        self.success = False
        # run_import returns success, log it separately from exceptions
        try:
            if self.run_import(in_filename, options):
                self.success = True
                # TODO: GROSS! figure out why this works but
                # art.geo_changed=True and art.mark_all_frames_changed() don't!
                self.app.ui.erase_selection_or_art()
                self.app.ui.undo()
                # adjust for new art size and set it active
                self.app.ui.adjust_for_art_resize(self.art)
                self.app.ui.set_active_art(self.art)
            else:
                classname = self.__class__.__name__
                self.app.log('%s failed to import %s' % (classname, in_filename))
        except:
            for line in traceback.format_exc().split('\n'):
                self.app.log(line)
    
    def set_art_charset(self, charset_name):
        "Convenience function for setting charset by name from run_import."
        charset = self.app.load_charset(charset_name)
        self.art.set_charset(charset)
    
    def set_art_palette(self, palette_name):
        palette = self.app.load_palette(palette_name)
        self.art.set_palette(palette)
    
    def run_import(self, in_filename, options):
        """
        Read input file, set Art size/charset/palette, set tiles from data,
        return success.
        """
        return False
