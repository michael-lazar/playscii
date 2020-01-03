
import os, traceback

from art import Art, ART_FILE_EXTENSION, DEFAULT_CHARSET, DEFAULT_PALETTE
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
    generic_error = '%s failed to import %s'
    # if False (eg bitmap conversion), "Imported successfully" message
    # won't show on successful creation
    completes_instantly = True
    
    def __init__(self, app, in_filename, options={}):
        self.app = app
        new_filename = '%s.%s' % (os.path.splitext(in_filename)[0],
                                  ART_FILE_EXTENSION)
        self.art = self.app.new_art(new_filename)
        # use charset and palette of existing art
        charset = self.app.ui.active_art.charset if self.app.ui.active_art else self.app.load_charset(DEFAULT_CHARSET)
        self.art.set_charset(charset)
        palette = self.app.ui.active_art.palette if self.app.ui.active_art else self.app.load_palette(DEFAULT_PALETTE)
        self.art.set_palette(palette)
        self.app.set_new_art_for_edit(self.art)
        self.art.clear_frame_layer(0, 0, 1)
        self.success = False
        "Set True on successful import."
        # run_import returns success, log it separately from exceptions
        try:
            if self.run_import(in_filename, options):
                self.success = True
        except:
            for line in traceback.format_exc().split('\n'):
                self.app.log(line)
        if not self.success:
            line = self.generic_error % (self.__class__.__name__, in_filename)
            self.app.log(line)
            self.app.close_art(self.art)
            # post message now after close_art sets active art back
            self.app.ui.message_line.post_line(line, error=True)
            return
        # tidy final result, whether or not it was successful
        # TODO: GROSS! figure out why this works but
        # art.geo_changed=True and art.mark_all_frames_changed() don't!
        self.app.ui.erase_selection_or_art()
        self.app.ui.undo()
        # adjust for new art size and set it active
        self.app.ui.adjust_for_art_resize(self.art)
        self.app.ui.set_active_art(self.art)
    
    def set_art_charset(self, charset_name):
        "Convenience function for setting charset by name from run_import."
        self.art.set_charset_by_name(charset_name)
    
    def set_art_palette(self, palette_name):
        "Convenience function for setting palette by name from run_import."
        self.art.set_palette_by_name(palette_name)
    
    def resize(self, new_width, new_height):
        "Convenience function for resizing art from run_import"
        self.art.resize(new_width, new_height)
        self.app.ui.adjust_for_art_resize(self.art)
    
    def run_import(self, in_filename, options):
        """
        Contains the actual import logic. Read input file, set Art
        size/charset/palette, set tiles from data, return success.
        """
        return False
