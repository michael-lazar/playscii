
# "convert folder of images to animation"
# heavy lifting still done by ImageConverter, this mainly coordinates
# conversion of multiple frames

import os, time

import image_convert
import formats.in_bitmap as bm

class ImageSequenceConverter:
    
    def __init__(self, app, image_filenames, art, bicubic_scale):
        self.init_success = False
        self.app = app
        self.start_time = time.time()
        self.image_filenames = image_filenames
        # App.update_window_title uses image_filename for titlebar
        self.image_filename = ''
        # common name of sequence
        self.image_name = os.path.splitext(self.image_filename)[0]
        self.art = art
        self.bicubic_scale = bicubic_scale
        # queue up first frame
        self.next_image(first=True)
        self.init_success = True
    
    def next_image(self, first=False):
        # pop last image off stack
        if not first:
            self.image_filenames.pop(0)
        # done?
        if len(self.image_filenames) == 0:
            self.finish()
            return
        # next frame
        self.art.set_active_frame(self.art.active_frame + 1)
        try:
            self.current_frame_converter = image_convert.ImageConverter(self.app,
                                                      self.image_filenames[0],
                                                      self.art,
                                                      self.bicubic_scale, self)
        except:
            self.fail()
            return
        if not self.current_frame_converter.init_success:
            self.fail()
            return
        self.image_filename = self.image_filenames[0]
        self.preview_sprite = self.current_frame_converter.preview_sprite
        self.app.update_window_title()
    
    def fail(self):
        self.app.log('Bad frame %s' % self.image_filenames[0], error=True)
        self.finish(True)
    
    def update(self):
        # create converter for new frame if current one is done,
        # else update current one
        if self.current_frame_converter.finished:
            self.next_image()
        else:
            self.current_frame_converter.update()
    
    def finish(self, cancelled=False):
        time_taken = time.time() - self.start_time
        (verb, error) = ('cancelled', True) if cancelled else ('finished', False)
        self.app.log('Conversion of image sequence %s %s after %.3f seconds' % (self.image_name, verb, time_taken), error)
        self.app.converter = None
        self.app.update_window_title()


class ConvertImageSequenceChooserDialog(bm.ConvertImageChooserDialog):
    title = 'Convert folder'
    confirm_caption = 'Choose First Image'


class BitmapImageSequenceImporter(bm.BitmapImageImporter):
    format_name = 'Bitmap image folder'
    format_description = """
Converts a folder of Bitmap images (PNG, JPEG, or BMP)
into an animation. Dimensions will be based on first
image chosen.
    """
    file_chooser_dialog_class = ConvertImageSequenceChooserDialog
    #options_dialog_class = bm.ConvertImageOptionsDialog
    
    def run_import(self, in_filename, options={}):
        palette = self.app.load_palette(options['palette'])
        self.art.set_palette(palette)
        width, height = options['art_width'], options['art_height']
        self.art.resize(width, height) # Importer.init will adjust UI
        bicubic_scale = options['bicubic_scale']
        # get dir listing with full pathname
        in_dir = os.path.dirname(in_filename)
        in_files = ['%s/%s' % (in_dir, f) for f in os.listdir(in_dir)]
        in_files.sort()
        # assume numeric sequence starts from chosen file
        in_files = in_files[in_files.index(in_filename):]
        # remove files from end of list if they don't end in a number
        while not os.path.splitext(in_files[-1])[0][-1].isdecimal() and \
              len(in_files) > 0:
            in_files.pop()
        # add frames to art as needed
        while self.art.frames < len(in_files):
            self.art.add_frame_to_end(log=False)
        self.art.set_active_frame(0)
        # create converter
        isc = ImageSequenceConverter(self.app, in_files, self.art,
                                     bicubic_scale)
        # bail on early failure
        if not isc.init_success:
            return False
        self.app.converter = isc
        self.app.update_window_title()
        return True
