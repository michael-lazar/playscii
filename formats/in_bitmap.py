
# bitmap image conversion predates the import/export system so it's a bit weird.
# conversion happens over time, so it merely kicks off the process.

import os
from PIL import Image

from ui_file_chooser_dialog import ImageFileChooserDialog
from ui_dialog import UIDialog, Field
from ui_art_dialog import ImportOptionsDialog
from image_convert import ImageConverter
from art_import import ArtImporter
from palette import PaletteFromFile
from art import DEFAULT_CHARSET, DEFAULT_PALETTE, DEFAULT_WIDTH, DEFAULT_HEIGHT

# custom chooser showing image previews, shares parent w/ "palette from image"

class ConvertImageChooserDialog(ImageFileChooserDialog):
    
    title = 'Convert image'
    confirm_caption = 'Choose'
    
    def confirm_pressed(self):
        filename = self.field_texts[0]
        if not os.path.exists(filename) or not os.path.isfile(filename):
            return
        self.ui.app.last_import_dir = self.current_dir
        self.dismiss()
        # get dialog box class and invoke it
        dialog_class = self.ui.app.importer.options_dialog_class
        # tell the dialog which image we chose, store its size
        w, h = Image.open(filename).size
        options = {
            'filename': filename,
            'image_width': w,
            'image_height': h
        }
        self.ui.open_dialog(dialog_class, options)


# custom dialog box providing convert options

class ConvertImageOptionsDialog(ImportOptionsDialog):
    
    title = 'Convert bitmap image options'
    field0_label = 'Color palette:'
    field1_label = 'Current palette (%s)'
    field2_label = 'From source image; # of colors:'
    field3_label = '  '
    field5_label = 'Converted art size:'
    field6_label = 'Best fit to current size (%s)'
    field7_label = '%% of source image: (%s)'
    field8_label = '  '
    field10_label = 'Smooth (bicubic) scale source image'
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
        Field(label='', type=None, width=0, oneline=True),
        Field(label=field10_label, type=bool, width=0, oneline=True),
        Field(label='', type=None, width=0, oneline=True)
    ]
    invalid_color_error = 'Palettes must be between 2 and 256 colors.'
    invalid_scale_error = 'Scale must be greater than 0.0'
    # redraw dynamic labels
    always_redraw_labels = True
    
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
        elif field_number == 10:
            return ' '
        return ''
    
    def get_field_label(self, field_index):
        label = self.fields[field_index].label
        # custom label replacements to show palette, possible convert sizes
        if field_index == 1:
            label %= self.ui.active_art.palette.name if self.ui.active_art else DEFAULT_PALETTE
        elif field_index == 6:
            # can't assume any art is open, use defaults if needed
            w = self.ui.active_art.width if self.ui.active_art else DEFAULT_WIDTH
            h = self.ui.active_art.height if self.ui.active_art else DEFAULT_HEIGHT
            label %= '%s x %s' % (w, h)
        elif field_index == 7:
            # scale # might not be valid
            valid,_ = self.is_input_valid()
            if not valid:
                return label % '???'
            label %= '%s x %s' % self.get_tile_scale()
        return label
    
    def get_tile_scale(self):
        "returns scale in tiles of image dimensions"
        # filename won't be set just after dialog is created
        if not hasattr(self, 'filename'):
            return 0, 0
        scale = float(self.field_texts[8]) / 100
        # can't assume any art is open, use defaults if needed
        if self.ui.active_art:
            cw = self.ui.active_art.charset.char_width
            ch = self.ui.active_art.charset.char_height
        else:
            charset = self.ui.app.load_charset(DEFAULT_CHARSET)
            cw, ch = charset.char_width, charset.char_height
        width = self.image_width / cw
        height = self.image_height / ch
        width *= scale
        height *= scale
        return int(width), int(height)
    
    def is_input_valid(self):
        # colors: int between 2 and 256
        try: int(self.field_texts[3])
        except: return False, self.invalid_color_error
        colors = int(self.field_texts[3])
        if colors < 2  or colors > 256:
            return False, self.invalid_color_error
        # % scale: >0 float
        try: float(self.field_texts[8])
        except: return False, self.invalid_scale_error
        if float(self.field_texts[8]) <= 0:
            return False, self.invalid_scale_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        self.dismiss()
        # compile options for importer
        options = {}
        # create new palette from image?
        if self.field_texts[1].strip():
            options['palette'] = self.ui.active_art.palette.name if self.ui.active_art else DEFAULT_PALETTE
        else:
            # create new palette
            palette_filename = os.path.basename(self.filename)
            colors = int(self.field_texts[3])
            new_pal = PaletteFromFile(self.ui.app, self.filename,
                                      palette_filename, colors)
            # palette now loaded and saved to disk
            options['palette'] = new_pal.name
        # rescale art?
        if self.field_texts[6].strip():
            options['art_width'] = self.ui.active_art.width if self.ui.active_art else DEFAULT_WIDTH
            options['art_height'] = self.ui.active_art.height if self.ui.active_art else DEFAULT_HEIGHT
        else:
            # art dimensions = scale% of image dimensions, in tiles
            options['art_width'], options['art_height'] = self.get_tile_scale()
        options['bicubic_scale'] = bool(self.field_texts[10].strip())
        ImportOptionsDialog.do_import(self.ui.app, self.filename, options)


class BitmapImageImporter(ArtImporter):
    format_name = 'Bitmap image'
    format_description = """
Bitmap image in PNG, JPEG, or BMP format.
    """
    file_chooser_dialog_class = ConvertImageChooserDialog
    options_dialog_class = ConvertImageOptionsDialog
    completes_instantly = False
    
    def run_import(self, in_filename, options={}):
        # modify self.app.ui.active_art based on options
        palette = self.app.load_palette(options['palette'])
        self.art.set_palette(palette)
        width, height = options['art_width'], options['art_height']
        self.art.resize(width, height) # Importer.init will adjust UI
        bicubic_scale = options['bicubic_scale']
        # let ImageConverter do the actual heavy lifting
        ic = ImageConverter(self.app, in_filename, self.art, bicubic_scale)
        # early failures: file no longer exists, PIL fails to load and convert image
        if not ic.init_success:
            return False
        self.app.update_window_title()
        return True
