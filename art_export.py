
import traceback

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
    
    def __init__(self, app, out_filename):
        self.app = app
        self.art = self.app.ui.active_art
        try:
            if self.run_export(out_filename):
                pass
            else:
                classname = self.__class__.__name__
                self.app.log('%s failed to export %s' % (classname, out_filename))
        except:
            for line in traceback.format_exc().split('\n'):
                self.app.log(line)
    
    def run_export(self, out_filename):
        return False
