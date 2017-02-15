
from art_export import ArtExporter
from image_export import export_animation

class GIFExporter(ArtExporter):
    format_name = 'Animated GIF image'
    format_description = """
Animated GIF of all frames in current document, with
transparency and proper frame timings.
    """
    file_extension = 'gif'
    def run_export(self, out_filename, options):
        # heavy lifting done by image_export module
        export_animation(self.app, self.app.ui.active_art, out_filename)
        return True
