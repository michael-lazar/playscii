
import os

from art_export import ArtExporter
from image_export import export_still_image
from ui_dialog import UIDialog, Field
from ui_art_dialog import ExportOptionsDialog
from renderable import LAYER_VIS_FULL, LAYER_VIS_NONE

FILE_EXTENSION = 'png'

DEFAULT_SCALE = 1
DEFAULT_CRT = False

def get_full_filename(in_filename, frame, layer_name,
                      use_frame, use_layer,
                      forbidden_chars):
    "Returns properly mutated filename for given frame/layer data"
    # strip out path and extension from filename as we mutate it
    dirname = os.path.dirname(in_filename)
    base_filename = os.path.basename(in_filename)
    base_filename = os.path.splitext(base_filename)[0]
    fn = base_filename
    if use_frame:
        fn += '_%s' % (str(frame).rjust(4, '0'))
    if use_layer:
        fn += '_%s' % layer_name
    # strip unfriendly chars from output filename
    for forbidden_char in ['\\', '/', '*', ':']:
        fn = fn.replace(forbidden_char, '')
    # add path and extension for final mutated filename
    return '%s/%s.%s' % (dirname, fn, FILE_EXTENSION)

class PNGSetExportOptionsDialog(ExportOptionsDialog):
    title = 'PNG set export options'
    tile_width = 60 # extra width for filename preview
    field0_label = 'Scale factor (%s pixels)'
    field1_label = 'CRT filter'
    field2_label = 'Export frames'
    field3_label = 'Export layers'
    field4_label = 'First filename (in set of %s):'
    field5_label = '  %s'
    fields = [
        Field(label=field0_label, type=int, width=6, oneline=False),
        Field(label=field1_label, type=bool, width=0, oneline=True),
        Field(label=field2_label, type=bool, width=0, oneline=True),
        Field(label=field3_label, type=bool, width=0, oneline=True),
        Field(label=field4_label, type=None, width=0, oneline=True),
        Field(label=field5_label, type=None, width=0, oneline=True)
    ]
    # redraw dynamic labels
    always_redraw_labels = True
    invalid_scale_error = 'Scale must be greater than 0'
    
    def get_initial_field_text(self, field_number):
        art = self.ui.active_art
        if field_number == 0:
            return str(DEFAULT_SCALE)
        elif field_number == 1:
            return [' ', UIDialog.true_field_text][DEFAULT_CRT]
        elif field_number == 2:
            # default false if only one frame
            return [' ', UIDialog.true_field_text][art.frames > 1]
        elif field_number == 3:
            # default false if only one layer
            return [' ', UIDialog.true_field_text][art.layers > 1]
    
    def get_field_label(self, field_index):
        label = self.fields[field_index].label
        if field_index == 0:
            valid,_ = self.is_input_valid()
            if not valid:
                label %= '???'
            else:
                # calculate exported image size
                art = self.ui.active_art
                scale = int(self.field_texts[0])
                width = art.charset.char_width * art.width * scale
                height = art.charset.char_height * art.height * scale
                label %= '%s x %s' % (width, height)
        # show how many images exported set will be
        elif field_index == 4:
            export_frames = bool(self.field_texts[2].strip())
            export_layers = bool(self.field_texts[3].strip())
            art = self.ui.active_art
            if export_frames and export_layers:
                label %= str(art.frames * art.layers)
            elif export_frames:
                label %= str(art.frames)
            elif export_layers:
                label %= str(art.layers)
            else:
                label %= '1'
        # preview frame + layer filename mutations based on current settings
        elif field_index == 5:
            export_frames = bool(self.field_texts[2].strip())
            export_layers = bool(self.field_texts[3].strip())
            art = self.ui.active_art
            fn = get_full_filename(self.filename, 0, art.layer_names[0],
                                   export_frames, export_layers,
                                   self.ui.app.forbidden_filename_chars)
            fn = os.path.basename(fn)
            label %= fn
        return label
    
    def is_input_valid(self):
        # scale factor: >0 int
        try: int(self.field_texts[0])
        except: return False, self.invalid_scale_error
        if int(self.field_texts[0]) <= 0:
            return False, self.invalid_scale_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        self.dismiss()
        # compile options for importer
        options = {
            'scale': int(self.field_texts[0]),
            'crt': bool(self.field_texts[1].strip()),
            'frames': bool(self.field_texts[2].strip()),
            'layers': bool(self.field_texts[3].strip())
        }
        ExportOptionsDialog.do_export(self.ui.app, self.filename, options)


class PNGSetExporter(ArtExporter):
    format_name = 'PNG image set'
    format_description = """
PNG image set for each frame and/or layer.
    """
    file_extension = FILE_EXTENSION
    options_dialog_class = PNGSetExportOptionsDialog
    
    def run_export(self, out_filename, options):
        export_frames = options['frames']
        export_layers = options['layers']
        art = self.app.ui.active_art
        # remember user's active frame/layer/viz settings so we
        # can set em back when done
        start_frame = art.active_frame
        start_layer = art.active_layer
        start_onion = self.app.onion_frames_visible
        start_layer_viz = self.app.inactive_layer_visibility
        self.app.onion_frames_visible = False
        # if multi-player, only show active layer
        self.app.inactive_layer_visibility = LAYER_VIS_NONE if export_layers else LAYER_VIS_FULL
        success = True
        for frame in range(art.frames):
            # if exporting layers but not frames, only export active frame
            if not export_frames and frame != art.active_frame:
                continue
            art.set_active_frame(frame)
            for layer in range(art.layers):
                art.set_active_layer(layer)
                full_filename = get_full_filename(out_filename, frame,
                                                  art.layer_names[layer],
                                                  export_frames, export_layers,
                                                  self.app.forbidden_filename_chars)
                if not export_still_image(self.app, art, full_filename,
                           crt=options.get('crt', DEFAULT_CRT),
                           scale=options.get('scale', DEFAULT_SCALE)):
                    success = False
        # put everything back how user left it
        art.set_active_frame(start_frame)
        art.set_active_layer(start_layer)
        self.app.onion_frames_visible = start_onion
        self.app.inactive_layer_visibility = start_layer_viz
        return success
