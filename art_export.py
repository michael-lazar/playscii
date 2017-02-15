
import traceback

from art import ART_DIR

class ArtExporter:
    
    """
    Class for exporting an Art into a non-Playscii format.
    Export logic happens in run_export; exporter authors simply extend this
    class, override run_export and the class properties below.
    """
    
    format_name = 'ERROR - ArtExporter.format_name'
    "User-visible name for this format, shown in export chooser."
    format_description = "ERROR - ArtExporter.format_description"
    "String (can be triple-quoted) describing format, shown in export chooser."
    file_extension = ''
    "Extension to give the exported file"
    options_dialog_class = None
    "UIDialog subclass exposing export options to user."
    
    def __init__(self, app, out_filename, options={}):
        self.app = app
        self.art = self.app.ui.active_art
        # add file extension to output filename if not present
        if self.file_extension and not out_filename.endswith('.%s' % self.file_extension):
            out_filename += '.%s' % self.file_extension
        # output filename in documents/art dir
        if not out_filename.startswith(self.app.documents_dir + ART_DIR):
            out_filename = self.app.documents_dir + ART_DIR + out_filename
        self.success = False
        try:
            if self.run_export(out_filename, options):
                self.success = True
            else:
                classname = self.__class__.__name__
                self.app.log('%s failed to export %s' % (classname, out_filename))
        except:
            for line in traceback.format_exc().split('\n'):
                self.app.log(line)
        # store last used export options for "Export last"
        self.app.last_export_options = options
    
    def run_export(self, out_filename, options):
        return False
