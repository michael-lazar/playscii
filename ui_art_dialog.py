import os.path

from ui_dialog import UIDialog, Field
from ui_chooser_dialog import ChooserDialog, ChooserItemButton, ChooserItem

from ui_console import OpenCommand, SaveCommand
from art import ART_DIR, ART_FILE_EXTENSION, DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FRAME_DELAY, DEFAULT_LAYER_Z_OFFSET
from palette import PaletteFromFile


class BaseFileDialog(UIDialog):
    
    invalid_filename_error = 'Filename is not valid.'
    filename_exists_error = 'File by that name already exists.'
    
    def get_file_extension(self):
        return ''
    
    def get_dir(self):
        return ''
    
    def get_full_filename(self, filename, dir=None):
        for forbidden_char in self.ui.app.forbidden_filename_chars:
            if forbidden_char in filename:
                return
        full_filename = self.get_dir() + '/' + filename
        full_filename += '.' + self.get_file_extension()
        return full_filename
    
    def is_filename_valid(self, field_number):
        filename = self.field_texts[field_number].strip()
        # filename can't be only whitespace
        if not filename:
            return False, self.invalid_filename_error
        full_filename = self.get_full_filename(filename)
        if not full_filename:
            return False, self.invalid_filename_error
        # if file exists, allow saving but show the warning
        if os.path.exists(full_filename):
            return True, self.filename_exists_error
        return True, None

class NewArtDialog(BaseFileDialog):
    
    title = 'New art'
    field0_label = 'Filename of new art:'
    field2_label = 'Width:'
    field4_label = 'Height:'
    field6_label = 'Save folder:'
    field7_label = ' %s'
    tile_width = 60
    field0_width = 56
    y_spacing = 0
    field1_width = field2_width = UIDialog.default_short_field_width
    fields = [
        Field(label=field0_label, type=str, width=field0_width, oneline=False),
        Field(label='', type=None, width=0, oneline=True),
        Field(label=field2_label, type=int, width=field1_width, oneline=True),
        Field(label='', type=None, width=0, oneline=True),
        Field(label=field4_label, type=int, width=field2_width, oneline=True),
        Field(label='', type=None, width=0, oneline=True),
        Field(label=field6_label, type=None, width=0, oneline=True),
        Field(label=field7_label, type=None, width=0, oneline=True),
        Field(label='', type=None, width=0, oneline=True)
    ]
    confirm_caption = 'Create'
    invalid_width_error = 'Invalid width.'
    invalid_height_error = 'Invalid height.'
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return 'new%s' % len(self.ui.app.art_loaded_for_edit)
        elif field_number == 2:
            return str(DEFAULT_WIDTH)
        elif field_number == 4:
            return str(DEFAULT_HEIGHT)
        return ''
    
    def get_field_label(self, field_index):
        label = self.fields[field_index].label
        # show dir art will be saved into
        if field_index == 7:
            label %= self.get_dir()
        return label
    
    def get_file_extension(self):
        return ART_FILE_EXTENSION
    
    def get_dir(self):
        return self.ui.app.documents_dir + ART_DIR
    
    def is_input_valid(self):
        "warn if file already exists, dimensions must be >0 and <= max"
        if not self.is_valid_dimension(self.field_texts[2], self.ui.app.max_art_width):
            return False, self.invalid_width_error
        if not self.is_valid_dimension(self.field_texts[4], self.ui.app.max_art_height):
            return False, self.invalid_height_error
        return self.is_filename_valid(0)
    
    def is_valid_dimension(self, dimension, max_dimension):
        try: dimension = int(dimension)
        except: return False
        return 0 < dimension <= max_dimension
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        name = self.field_texts[0]
        w, h = int(self.field_texts[2]), int(self.field_texts[4])
        self.ui.app.new_art_for_edit(name, w, h)
        self.ui.app.log('Created %s.psci with size %s x %s' % (name, w, h))
        self.dismiss()


class SaveAsDialog(BaseFileDialog):
    
    title = 'Save art'
    field0_label = 'New filename for art:'
    field2_label = 'Save folder:'
    field3_label = ' %s'
    tile_width = 60
    field0_width = 56
    y_spacing = 0
    fields = [
        Field(label=field0_label, type=str, width=field0_width, oneline=False),
        Field(label='', type=None, width=0, oneline=True),
        Field(label=field2_label, type=None, width=0, oneline=True),
        Field(label=field3_label, type=None, width=0, oneline=True),
        Field(label='', type=None, width=0, oneline=True)
    ]
    confirm_caption = 'Save'
    always_redraw_labels = True
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            # special case: if opening playscii/art/new, change
            # it to documents dir to avoid writing to application dir
            # (still possible if you open other files)
            if os.path.dirname(self.ui.active_art.filename) == ART_DIR[:-1]:
                self.ui.active_art.filename = self.ui.app.documents_dir + self.ui.active_art.filename
            # TODO: handle other files from app dir as well? not as important
            filename = os.path.basename(self.ui.active_art.filename)
            filename = os.path.splitext(filename)[0]
            return filename
        return ''
    
    def get_file_extension(self):
        """
        Return file extension this dialog saves as; other dialogs
        are based on this class so we don't want to hardcore .psci
        """
        return ART_FILE_EXTENSION
    
    def get_dir(self):
        return os.path.dirname(self.ui.active_art.filename)
    
    def get_field_label(self, field_index):
        label = self.fields[field_index].label
        # show dir art will be saved into
        if field_index == 3:
            label %= self.get_dir()
        return label
    
    def is_input_valid(self):
        return self.is_filename_valid(0)
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        SaveCommand.execute(self.ui.console, [self.field_texts[0]])
        self.dismiss()

class ConvertItemButton(ChooserItemButton):
    width = 15
    big_width = 20

class ConvertChooserItem(ChooserItem):
    
    def picked(self, element):
        
        # TODO: following is c+p'd from BaseFileChooserItem.picked,
        # move this functionality into ChooserItem and override in BFCI?
        
        # if this is different from the last clicked item, pick it
        if element.selected_item_index != self.index:
            ChooserItem.picked(self, element)
            element.first_selection_made = True
            return
        # if we haven't yet clicked something in this view, require another
        # click before opening it (consistent double click behavior for
        # initial selections)
        if not element.first_selection_made:
            element.first_selection_made = True
            return
        element.confirm_pressed()
        element.first_selection_made = False
    
    def get_description_lines(self):
        return self.description.split('\n')

class ConvertFileDialog(ChooserDialog):
    "Common functionality for importer and exporter selection dialogs"
    tile_width, big_width = 85, 90
    tile_height, big_height = 15, 25
    confirm_caption = 'Choose'
    show_preview_image = False
    item_button_class = ConvertItemButton
    chooser_item_class = ConvertChooserItem
    
    def get_converters(self):
        return []
    
    def get_items(self):
        items = []
        converters = self.get_converters()
        # sort alphabetically
        converters.sort(key=lambda item: item.format_name.lower())
        i = 0
        for converter in converters:
            item = self.chooser_item_class(i, converter.__name__)
            item.converter_class = converter
            item.label = converter.format_name
            item.description = converter.format_description
            items.append(item)
            i += 1
        return items


class ImportFileDialog(ConvertFileDialog):
    title = 'Choose an importer'
    
    def get_converters(self):
        return self.ui.app.get_importers()
    
    def confirm_pressed(self):
        # open file select dialog so user can choose what to import
        item = self.get_selected_item()
        self.ui.app.importer = item.converter_class
        if not self.ui.app.importer:
            return
        self.dismiss()
        self.ui.open_dialog(self.ui.app.importer.file_chooser_dialog_class)

class ImportOptionsDialog(UIDialog):
    "Generic base class for importer options"
    confirm_caption = 'Import'
    def do_import(app, filename, options):
        "Common 'run importer' code for end of import options dialog"
        # if importer needs no options, run it
        importer = app.importer(app, filename, options)
        if importer.success:
            if app.importer.completes_instantly:
                app.log('Imported %s successfully.' % filename)
            app.importer = None

class ExportOptionsDialog(UIDialog):
    "Generic base class for exporter options"
    confirm_caption = 'Export'
    def do_export(app, filename, options):
        "Common 'run exporter' code for end of import options dialog"
        # if importer needs no options, run it
        exporter = app.exporter(app, filename, options)
        if exporter.success:
            app.log('Exported %s successfully.' % exporter.out_filename)

class ExportFileDialog(ConvertFileDialog):
    title = 'Choose an exporter'
    
    def get_converters(self):
        return self.ui.app.get_exporters()
    
    def confirm_pressed(self):
        # open file select dialog so user can choose what to import
        item = self.get_selected_item()
        self.ui.app.exporter = item.converter_class
        if not self.ui.app.exporter:
            return
        self.dismiss()
        self.ui.open_dialog(ExportFilenameInputDialog)


class ExportFilenameInputDialog(SaveAsDialog):
    title = 'Export art'
    field0_label = 'New filename for exported art:'
    confirm_caption = 'Export'
    
    def get_initial_field_text(self, field_number):
        # base output filename on art filename
        if field_number == 0:
            out_filename = self.ui.active_art.filename
            out_filename = os.path.basename(out_filename)
            out_filename = os.path.splitext(out_filename)[0]
            return out_filename
    
    def get_file_extension(self):
        return self.ui.app.exporter.file_extension
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        filename = self.field_texts[0]
        self.dismiss()
        # invoke options dialog if exporter has one, else invoke exporter
        if self.ui.app.exporter.options_dialog_class:
            # pass filename into new dialog
            options = {'filename': filename}
            self.ui.open_dialog(self.ui.app.exporter.options_dialog_class,
                                options)
        else:
            ExportOptionsDialog.do_export(self.ui.app, filename, {})


class QuitUnsavedChangesDialog(UIDialog):
    
    title = 'Unsaved changes'
    message = 'Save changes to %s?'
    confirm_caption = 'Save'
    other_button_visible = True
    other_caption = "Don't Save"
    
    def confirm_pressed(self):
        SaveCommand.execute(self.ui.console, [])
        self.dismiss()
        # try again, see if another art has unsaved changes
        self.ui.app.il.BIND_quit()
    
    def other_pressed(self):
        # kind of a hack: make the check BIND_quit does come up false
        # for this art. externalities fairly minor.
        self.ui.active_art.unsaved_changes = False
        self.dismiss()
        self.ui.app.il.BIND_quit()
    
    def get_message(self):
        # get base name (ie no dirs)
        filename = os.path.basename(self.ui.active_art.filename)
        return [self.message % filename]


class CloseUnsavedChangesDialog(QuitUnsavedChangesDialog):
    
    def confirm_pressed(self):
        SaveCommand.execute(self.ui.console, [])
        self.dismiss()
        self.ui.app.il.BIND_close_art()
    
    def other_pressed(self):
        self.ui.active_art.unsaved_changes = False
        self.dismiss()
        self.ui.app.il.BIND_close_art()


class RevertChangesDialog(UIDialog):
    
    title = 'Revert changes'
    message = 'Revert changes to %s?'
    confirm_caption = 'Revert'
    
    def confirm_pressed(self):
        self.ui.app.revert_active_art()
        self.dismiss()
    
    def get_message(self):
        filename = os.path.basename(self.ui.active_art.filename)
        return [self.message % filename]


class ResizeArtDialog(UIDialog):
    
    title = 'Resize art'
    field_width = UIDialog.default_short_field_width
    field0_label = 'New Width:'
    field1_label = 'New Height:'
    field2_label = 'Crop Start X:'
    field3_label = 'Crop Start Y:'
    field4_label = 'Fill new tiles with BG color'
    fields = [
        Field(label=field0_label, type=int, width=field_width, oneline=True),
        Field(label=field1_label, type=int, width=field_width, oneline=True),
        Field(label=field2_label, type=int, width=field_width, oneline=True),
        Field(label=field3_label, type=int, width=field_width, oneline=True),
        Field(label=field4_label, type=bool, width=0, oneline=True)
    ]
    confirm_caption = 'Resize'
    invalid_width_error = 'Invalid width.'
    invalid_height_error = 'Invalid height.'
    invalid_start_error = 'Invalid crop origin.'
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return str(self.ui.active_art.width)
        elif field_number == 1:
            return str(self.ui.active_art.height)
        elif field_number == 4:
            return UIDialog.true_field_text
        else:
            return '0'
    
    def is_input_valid(self):
        "file can't already exist, dimensions must be >0 and <= max"
        if not self.is_valid_dimension(self.field_texts[0], self.ui.app.max_art_width):
            return False, self.invalid_width_error
        if not self.is_valid_dimension(self.field_texts[1], self.ui.app.max_art_height):
            return False, self.invalid_height_error
        try: int(self.field_texts[2])
        except: return False, self.invalid_start_error
        if not 0 <= int(self.field_texts[2]) < self.ui.active_art.width:
            return False, self.invalid_start_error
        try: int(self.field_texts[3])
        except: return False, self.invalid_start_error
        if not 0 <= int(self.field_texts[3]) < self.ui.active_art.height:
            return False, self.invalid_start_error
        return True, None
    
    def is_valid_dimension(self, dimension, max_dimension):
        try: dimension = int(dimension)
        except: return False
        return 0 < dimension <= max_dimension
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        w, h = int(self.field_texts[0]), int(self.field_texts[1])
        start_x, start_y = int(self.field_texts[2]), int(self.field_texts[3])
        bg_fill = bool(self.field_texts[4].strip())
        self.ui.resize_art(self.ui.active_art, w, h, start_x, start_y, bg_fill)
        self.dismiss()


#
# layer menu dialogs
#

class AddFrameDialog(UIDialog):
    
    title = 'Add new frame'
    field0_label = 'Index to add frame before:'
    field1_label = 'Hold time (in seconds) for new frame:'
    field_width = UIDialog.default_short_field_width
    fields = [
        Field(label=field0_label, type=int, width=field_width, oneline=True),
        Field(label=field1_label, type=float, width=field_width, oneline=False)
    ]
    confirm_caption = 'Add'
    invalid_index_error = 'Invalid index. (1-%s allowed)'
    invalid_delay_error = 'Invalid hold time.'
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return str(self.ui.active_art.frames + 1)
        elif field_number == 1:
            return str(DEFAULT_FRAME_DELAY)
    
    def is_valid_frame_index(self, index):
        try: index = int(index)
        except: return False
        if index < 1 or index > self.ui.active_art.frames + 1:
            return False
        return True
    
    def is_valid_frame_delay(self, delay):
        try: delay = float(delay)
        except: return False
        return delay > 0
    
    def is_input_valid(self):
        if not self.is_valid_frame_index(self.field_texts[0]):
            return False, self.invalid_index_error % str(self.ui.active_art.frames + 1)
        if not self.is_valid_frame_delay(self.field_texts[1]):
            return False, self.invalid_delay_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        index = int(self.field_texts[0])
        delay = float(self.field_texts[1])
        self.ui.active_art.insert_frame_before_index(index - 1, delay)
        self.dismiss()

class DuplicateFrameDialog(AddFrameDialog):
    title = 'Duplicate frame'
    confirm_caption = 'Duplicate'
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        index = int(self.field_texts[0])
        delay = float(self.field_texts[1])
        self.ui.active_art.duplicate_frame(self.ui.active_art.active_frame, index - 1, delay)
        self.dismiss()

class FrameDelayDialog(AddFrameDialog):
    
    field0_label = 'New hold time (in seconds) for frame:'
    field_width = UIDialog.default_short_field_width
    fields = [
        Field(label=field0_label, type=float, width=field_width, oneline=False)
    ]
    confirm_caption = 'Set'
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return str(self.ui.active_art.frame_delays[self.ui.active_art.active_frame])
    
    def is_input_valid(self):
        if not self.is_valid_frame_delay(self.field_texts[0]):
            return False, self.invalid_delay_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        delay = float(self.field_texts[0])
        self.ui.active_art.frame_delays[self.ui.active_art.active_frame] = delay
        self.dismiss()

class FrameDelayAllDialog(FrameDelayDialog):
    field0_label = 'New hold time (in seconds) for all frames:'
    field_width = UIDialog.default_short_field_width
    fields = [
        Field(label=field0_label, type=float, width=field_width, oneline=False)
    ]
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        delay = float(self.field_texts[0])
        for i in range(self.ui.active_art.frames):
            self.ui.active_art.frame_delays[i] = delay
        self.dismiss()

class FrameIndexDialog(AddFrameDialog):
    field0_label = 'Move this frame before index:'
    field_width = UIDialog.default_short_field_width
    fields = [
        Field(label=field0_label, type=int, width=field_width, oneline=False)
    ]
    confirm_caption = 'Set'
    
    def is_input_valid(self):
        if not self.is_valid_frame_index(self.field_texts[0]):
            return False, self.invalid_index_error % str(self.ui.active_art.frames + 1)
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        # set new frame index (effectively moving it in the sequence)
        dest_index = int(self.field_texts[0])
        self.ui.active_art.move_frame_to_index(self.ui.active_art.active_frame, dest_index)
        self.dismiss()


#
# layer menu dialogs
#

class AddLayerDialog(UIDialog):
    
    title = 'Add new layer'
    field0_label = 'Name for new layer:'
    field1_label = 'Z-depth for new layer:'
    field0_width = UIDialog.default_field_width
    field1_width = UIDialog.default_short_field_width
    fields = [
        Field(label=field0_label, type=str, width=field0_width, oneline=False),
        Field(label=field1_label, type=float, width=field1_width, oneline=True)
    ]
    confirm_caption = 'Add'
    name_exists_error = 'Layer by that name already exists.'
    invalid_z_error = 'Invalid number.'
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return 'Layer %s' % str(self.ui.active_art.layers + 1)
        elif field_number == 1:
            return str(self.ui.active_art.layers_z[self.ui.active_art.active_layer] + DEFAULT_LAYER_Z_OFFSET)
    
    def is_valid_layer_name(self, name, exclude_active_layer=False):
        for i,layer_name in enumerate(self.ui.active_art.layer_names):
            if exclude_active_layer and i == self.ui.active_layer:
                continue
            if layer_name == name:
                return False
        return True
    
    def is_input_valid(self):
        valid_name = self.is_valid_layer_name(self.field_texts[0])
        if not valid_name:
            return False, self.name_exists_error
        try: z = float(self.field_texts[1])
        except: return False, self.invalid_z_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        name = self.field_texts[0]
        z = float(self.field_texts[1])
        self.ui.active_art.add_layer(z, name)
        self.dismiss()


class DuplicateLayerDialog(AddLayerDialog):
    title = 'Duplicate layer'
    confirm_caption = 'Duplicate'
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        name = self.field_texts[0]
        z = float(self.field_texts[1])
        self.ui.active_art.duplicate_layer(self.ui.active_art.active_layer, z, name)
        self.dismiss()


class SetLayerNameDialog(AddLayerDialog):
    
    title = 'Set layer name'
    field0_label = 'New name for this layer:'
    field_width = UIDialog.default_field_width
    fields = [
        Field(label=field0_label, type=str, width=field_width, oneline=False)
    ]
    confirm_caption = 'Rename'
    
    def confirm_pressed(self):
        new_name = self.field_texts[0]
        self.ui.active_art.layer_names[self.ui.active_art.active_layer] = new_name
        self.ui.active_art.set_unsaved_changes(True)
        self.dismiss()


class SetLayerZDialog(UIDialog):
    title = 'Set layer Z-depth'
    field0_label = 'Z-depth for layer:'
    field_width = UIDialog.default_short_field_width
    fields = [
        Field(label=field0_label, type=float, width=field_width, oneline=False)
    ]
    confirm_caption = 'Set'
    invalid_z_error = 'Invalid number.'
    
    def get_initial_field_text(self, field_number):
        # populate with existing z
        if field_number == 0:
            return str(self.ui.active_art.layers_z[self.ui.active_art.active_layer])
    
    def is_input_valid(self):
        try: z = float(self.field_texts[0])
        except: return False, self.invalid_z_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        new_z = float(self.field_texts[0])
        self.ui.active_art.layers_z[self.ui.active_art.active_layer] = new_z
        self.ui.active_art.set_unsaved_changes(True)
        self.ui.app.grid.reset()
        self.dismiss()


class PaletteFromFileDialog(UIDialog):
    title = 'Create palette from file'
    field0_label = 'Filename to create palette from:'
    field1_label = 'Filename for new palette:'
    field2_label = 'Colors in new palette:'
    field0_width = field1_width = UIDialog.default_field_width
    field2_width = UIDialog.default_short_field_width
    fields = [
        Field(label=field0_label, type=str, width=field0_width, oneline=False),
        Field(label=field1_label, type=str, width=field1_width, oneline=False),
        Field(label=field2_label, type=int, width=field2_width, oneline=True)
    ]
    confirm_caption = 'Create'
    invalid_color_error = 'Palettes must be between 2 and 256 colors.'
    bad_output_filename_error = 'Enter a filename for the new palette.'
    
    def get_initial_field_text(self, field_number):
        # NOTE: PaletteFromImageChooserDialog.confirm_pressed which invokes us
        # sets fields 0 and 1
        if field_number == 2:
            return str(256)
        return ''
    
    def valid_colors(self, colors):
        try: c = int(colors)
        except: return False
        return 2 <= c <= 256
    
    def is_input_valid(self):
        valid_colors = self.valid_colors(self.field_texts[2])
        if not valid_colors:
            return False, self.invalid_color_error
        if not self.field_texts[1].strip():
            return False, self.bad_output_filename_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        src_filename = self.field_texts[0]
        palette_filename = self.field_texts[1]
        colors = int(self.field_texts[2])
        new_pal = PaletteFromFile(self.ui.app, src_filename, palette_filename, colors)
        self.dismiss()


class SetCameraZoomDialog(UIDialog):
    title = 'Set camera zoom'
    field0_label = 'New camera zoom %:'
    field_width = UIDialog.default_short_field_width
    fields = [
        Field(label=field0_label, type=float, width=field_width, oneline=True)
    ]
    confirm_caption = 'Set'
    invalid_zoom_error = 'Zoom % must be a number greater than zero.'
    all_modes_visible = True
    game_mode_visible = True
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return '%.1f' % self.ui.app.camera.get_current_zoom_pct()
        return ''
    
    def is_input_valid(self):
        try: zoom = float(self.field_texts[0])
        except: return False, self.invalid_zoom_error
        if zoom <= 0:
            return False, self.invalid_zoom_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        new_zoom_pct = float(self.field_texts[0])
        camera = self.ui.app.camera
        camera.z = camera.get_base_zoom() / (new_zoom_pct / 100)
        self.dismiss()
