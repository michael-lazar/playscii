
# bitmap image conversion predates the import/export system so it's a bit weird.
# conversion happens over time, so it merely kicks off the process.

import os
from PIL import Image

from texture import Texture
from ui_file_chooser_dialog import ImageFileChooserDialog

from image_convert import ImageConverter

from art_import import ArtImporter

# custom chooser showing image previews, shares parent w/ "palette from image"

class ConvertImageChooserDialog(ImageFileChooserDialog):
    
    title = 'Convert image'
    confirm_caption = 'Convert'
    
    def confirm_pressed(self):
        filename = self.field_texts[0]
        if not os.path.exists(filename):
            return
        self.dismiss()
        importer = self.ui.app.importer(self.ui.app, filename)
        self.ui.app.importer = None

class BitmapImageImporter(ArtImporter):
    format_name = 'Image'
    format_description = """
Bitmap image in PNG, JPEG, or BMP format.
    """
    file_chooser_dialog_class = ConvertImageChooserDialog
    #options_dialog_class = TODO: conversion options
    
    def run_import(self, in_filename):
        # ImageConverter does all the heavy lifting
        ImageConverter(self.app, in_filename, self.app.ui.active_art)
        self.app.update_window_title()
        return True
