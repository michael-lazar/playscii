
from art_export import ArtExporter
from image_export import export_still_image
from ui_dialog import UIDialog, Field
from ui_art_dialog import ExportOptionsDialog

DEFAULT_SCALE = 4
DEFAULT_CRT = True

class PNGExportOptionsDialog(ExportOptionsDialog):
    title = 'PNG image export options'
    field0_label = 'Scale factor (%s pixels)'
    field1_label = 'CRT filter'
    fields = [
        Field(label=field0_label, type=int, width=6, oneline=False),
        Field(label=field1_label, type=bool, width=0, oneline=True)
    ]
    # redraw dynamic labels
    always_redraw_labels = True
    invalid_scale_error = 'Scale must be greater than 0'
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return str(DEFAULT_SCALE)
        elif field_number == 1:
            return [' ', UIDialog.true_field_text][DEFAULT_CRT]
    
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
        # compile options for exporter
        options = {
            'scale': int(self.field_texts[0]),
            'crt': bool(self.field_texts[1].strip())
        }
        ExportOptionsDialog.do_export(self.ui.app, self.filename, options)


class PNGExporter(ArtExporter):
    format_name = 'PNG image'
    format_description = """
PNG format (lossless compression) still image of current frame.
Can be exported with or without CRT filter effect.
If palette has only one transparent (alpha <1.0) color,
exported image will be 8-bit with same palette as this Art.
Otherwise it will be 32-bit with alpha transparency.
If CRT filter is enabled, image will always be 32-bit.
    """
    file_extension = 'png'
    options_dialog_class = PNGExportOptionsDialog
    
    def run_export(self, out_filename, options):
        # heavy lifting done by image_export module
        return export_still_image(self.app, self.app.ui.active_art,
                           out_filename,
                           crt=options.get('crt', DEFAULT_CRT),
                           scale=options.get('scale', DEFAULT_SCALE))
