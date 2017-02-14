
# bitmap image conversion predates the import/export system so it's a bit weird.
# conversion happens over time, so it merely kicks off the process.

import os
from PIL import Image

from ui_file_chooser_dialog import ImageFileChooserDialog
from ui_dialog import UIDialog, Field
from image_convert import ImageConverter
from art_import import ArtImporter
from palette import PaletteFromFile

# custom chooser showing image previews, shares parent w/ "palette from image"

class ConvertImageChooserDialog(ImageFileChooserDialog):
    
    title = 'Convert image'
    confirm_caption = 'Choose'
    
    def confirm_pressed(self):
        filename = self.field_texts[0]
        if not os.path.exists(filename):
            return
        self.ui.app.last_import_dir = self.current_dir
        self.dismiss()
        # get dialog box class and invoke it
        dialog_class = self.ui.app.importer.options_dialog_class
        self.ui.open_dialog(dialog_class)
        # stash the filename we chose in a special property in new dialog
        self.ui.active_dialog.filename = filename


# custom dialog box providing convert options

class ConvertImageOptionsDialog(UIDialog):
    
    title = 'Convert image options'
    field0_label = 'Color palette:'
    field1_label = 'Current palette (%s)'
    field2_label = 'From source image; # of colors:'
    field3_label = '  '
    field5_label = 'Converted art size:'
    field6_label = 'Best fit to current size (%s)'
    field7_label = '% of source image: (%s)'
    field8_label = '  '
    radio_groups = [(1, 2), (6, 7)]
    field_width = UIDialog.default_short_field_width
    # to get the layout we want, we must specify 0 padding lines and
    # add some blank ones :/
    y_spacing = 0
    fields = [
        Field(label=field0_label, type=None, width=0, oneline=True),
        Field(label=field1_label, type=bool, width=0, oneline=True),
        Field(label=field2_label, type=bool, width=0, oneline=True),
        Field(label=field3_label, type=int, width=field_width, oneline=True),
        Field(label='', type=None, width=0, oneline=True),
        Field(label=field5_label, type=None, width=0, oneline=True),
        Field(label=field6_label, type=bool, width=0, oneline=True),
        Field(label=field7_label, type=bool, width=0, oneline=True),
        Field(label=field8_label, type=float, width=field_width, oneline=True),
        Field(label='', type=None, width=0, oneline=True)
    ]
    confirm_caption = 'Convert'
    invalid_color_error = 'Palettes must be between 2 and 256 colors.'
    invalid_scale_error = 'Scale must be greater than 0.0'
    
    def get_initial_field_text(self, field_number):
        if field_number == 1:
            return UIDialog.true_field_text
        elif field_number == 3:
            # # of colors from source image
            return '64'
        elif field_number == 6:
            return UIDialog.true_field_text
        elif field_number == 8:
            # % of source image size
            return '50.0'
        return ''
    
    def is_input_valid(self):
        
        try: int(self.field_texts[3])
        except: return False, self.invalid_color_error
        
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        self.dismiss()
        # compile options for importer
        options = {}
        # create new palette from image?
        if self.field_texts[1].strip():
            options['palette'] = self.ui.active_art.palette.name
        else:
            # create new palette
            palette_filename = os.path.basename(self.filename)
            palette_filename = os.path.splitext(palette_filename)[0]
            colors = int(self.field_texts[3])
            new_pal = PaletteFromFile(self.ui.app, self.filename,
                                      palette_filename, colors)
            # palette now loaded and saved to disk
            options['palette'] = new_pal.name
        # rescale art?
        if self.field_texts[6].strip():
            options['art_width'] = self.ui.active_art.width
            options['art_height'] = self.ui.active_art.height
        else:
            # art dimensions = scale% of image dimensions, in tiles
            img = Image.open(self.filename)
            img_width, img_height = img.size
            scale = float(self.field_texts[8]) / 100
            width = img_width / self.ui.active_art.charset.char_width
            height = img_height / self.ui.active_art.charset.char_height
            options['art_width'] = int(width * scale)
            options['art_height'] = int(height * scale)
        importer = self.ui.app.importer(self.ui.app, self.filename, options)
        self.ui.app.importer = None


class BitmapImageImporter(ArtImporter):
    format_name = 'Image'
    format_description = """
Bitmap image in PNG, JPEG, or BMP format.
    """
    file_chooser_dialog_class = ConvertImageChooserDialog
    options_dialog_class = ConvertImageOptionsDialog
    
    def run_import(self, in_filename, options={}):
        # modify self.app.ui.active_art based on options
        palette = self.app.load_palette(options['palette'])
        self.art.set_palette(palette)
        width, height = options['art_width'], options['art_height']
        self.art.resize(width, height) # Importer.init will adjust UI
        # let ImageConverter do the actual heavy lifting
        ImageConverter(self.app, in_filename, self.art)
        self.app.update_window_title()
        return True
