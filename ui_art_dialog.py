import os.path

from ui_dialog import UIDialog, Field
from ui_chooser_dialog import ChooserDialog, ChooserItemButton

from ui_console import OpenCommand, SaveCommand
from art import ART_DIR, ART_FILE_EXTENSION, DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FRAME_DELAY, DEFAULT_LAYER_Z_OFFSET
from palette import PaletteFromFile


class NewArtDialog(UIDialog):
    
    title = 'New art'
    field0_label = 'Filename of new art:'
    field1_label = 'Width:'
    field2_label = 'Height:'
    field0_width = UIDialog.default_field_width
    field1_width = field2_width = int(field0_width / 4)
    fields = [
        Field(label=field0_label, type=str, width=field0_width, oneline=False),
        Field(label=field1_label, type=int, width=field1_width, oneline=True),
        Field(label=field2_label, type=int, width=field2_width, oneline=True)
    ]
    confirm_caption = 'Create'
    file_exists_error = 'File by that name already exists.'
    invalid_width_error = 'Invalid width.'
    invalid_height_error = 'Invalid height.'
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return 'new%s' % len(self.ui.app.art_loaded_for_edit)
        elif field_number == 1:
            return str(DEFAULT_WIDTH)
        elif field_number == 2:
            return str(DEFAULT_HEIGHT)
        return ''
    
    def is_input_valid(self):
        "file can't already exist, dimensions must be >0 and <= max"
        if os.path.exists('%s%s.%s' % (ART_DIR, self.field_texts[0], ART_FILE_EXTENSION)):
            return False, self.file_exists_error
        if not self.is_valid_dimension(self.field_texts[1], self.ui.app.max_art_width):
            return False, self.invalid_width_error
        if not self.is_valid_dimension(self.field_texts[2], self.ui.app.max_art_height):
            return False, self.invalid_height_error
        return True, None
    
    def is_valid_dimension(self, dimension, max_dimension):
        try: dimension = int(dimension)
        except: return False
        return 0 < dimension <= max_dimension
    
    def confirm_pressed(self):
        name = self.field_texts[0]
        w, h = int(self.field_texts[1]), int(self.field_texts[2])
        self.ui.app.new_art_for_edit(name, w, h)
        self.ui.app.log('Created %s.psci with size %s x %s' % (name, w, h))
        self.dismiss()


class OpenArtDialog(UIDialog):
    
    title = 'Open art'
    fields = 1
    field0_label = 'Filename of art to open:'
    confirm_caption = 'Open'
    
    def confirm_pressed(self):
        # run console command for same code path
        OpenCommand.execute(self.ui.console, [self.get_field_text(0)])
        self.dismiss()


class SaveAsDialog(UIDialog):
    
    title = 'Save art'
    field0_label = 'New filename for art:'
    fields = 1
    confirm_caption = 'Save'
    
    def confirm_pressed(self):
        SaveCommand.execute(self.ui.console, [self.field0_text])
        self.dismiss()

class ImportItemButton(ChooserItemButton):
    width = 15
    big_width = 20

class ImportFileDialog(ChooserDialog):
    # TODO: generalize this so exporter can inherit from it trivially
    title = 'Choose an importer'
    confirm_caption = 'Choose'
    show_preview_image = False
    item_button_class = ImportItemButton
    
    def get_items(self):
        items = []
        importers = self.ui.app.get_importers()
        i = 0
        for importer in importers:
            item = self.chooser_item_class(i, importer.format_name)
            item.importer_class = importer
            item.description = importer.format_description
            items.append(item)
            i += 1
        return items
    
    def set_preview(self):
        item = self.get_selected_item()
        x = self.item_button_width + 4
        y = 3
        for line in item.description.split('\n'):
            self.art.write_string(0, 0, x, y, line)
            y += 1
    
    def confirm_pressed(self):
        # TODO: open file dialog, sets importer as current
        self.dismiss()


class ImportEDSCIIDialog(UIDialog):
    title = 'Import EDSCII (legacy format) art'
    field0_label = 'Filename of EDSCII art to open:'
    fields = 2
    field1_label = 'Width override (leave 0 to guess):'
    field1_type = int
    confirm_caption = 'Import'
    invalid_width_error = 'Invalid width override.'
    
    def get_initial_field_text(self, field_number):
        if field_number == 1:
            return '0'
        return ''
    
    def is_input_valid(self):
        try: int(self.field1_text)
        except: return False, self.invalid_width_error
        if int(self.field1_text) < 0:
            return False, self.invalid_width_error
        return True, None
    
    def confirm_pressed(self):
        filename = self.field0_text
        width = int(self.get_field_text(1))
        width = width if width > 0 else None
        self.ui.app.import_edscii(filename, width)
        self.dismiss()


class QuitUnsavedChangesDialog(UIDialog):
    
    title = 'Unsaved changes'
    message = 'Save changes to %s?'
    confirm_caption = 'Save'
    other_button_visible = True
    other_caption = "Don't Save"
    fields = 0
    
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
    fields = 0
    
    def confirm_pressed(self):
        self.ui.app.revert_active_art()
        self.dismiss()
    
    def get_message(self):
        filename = os.path.basename(self.ui.active_art.filename)
        return [self.message % filename]


class ResizeArtDialog(UIDialog):
    
    title = 'Resize art'
    fields = 4
    field0_label = 'New Width:'
    field1_label = 'New Height:'
    field2_label = 'Crop Start X:'
    field3_label = 'Crop Start Y:'
    field0_type = int
    field1_type = int
    field2_type = int
    field3_type = int
    confirm_caption = 'Resize'
    # TODO: warning about how this can't be undone at the moment!
    field0_width = field1_width = field2_width = field3_width = int(36 / 4)
    invalid_width_error = 'Invalid width.'
    invalid_height_error = 'Invalid height.'
    invalid_start_error = 'Invalid crop origin.'
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return str(self.ui.active_art.width)
        elif field_number == 1:
            return str(self.ui.active_art.height)
        else:
            return '0'
    
    def is_input_valid(self):
        "file can't already exist, dimensions must be >0 and <= max"
        if not self.is_valid_dimension(self.field0_text, self.ui.app.max_art_width):
            return False, self.invalid_width_error
        if not self.is_valid_dimension(self.field1_text, self.ui.app.max_art_height):
            return False, self.invalid_height_error
        try: int(self.field2_text)
        except: return False, self.invalid_start_error
        if not 0 <= int(self.field2_text) < self.ui.active_art.width:
            return False, self.invalid_start_error
        try: int(self.field3_text)
        except: return False, self.invalid_start_error
        if not 0 <= int(self.field3_text) < self.ui.active_art.height:
            return False, self.invalid_start_error
        return True, None
    
    def is_valid_dimension(self, dimension, max_dimension):
        try: dimension = int(dimension)
        except: return False
        return 0 < dimension <= max_dimension
    
    def confirm_pressed(self):
        w, h = int(self.get_field_text(0)), int(self.get_field_text(1))
        start_x, start_y = int(self.get_field_text(2)), int(self.get_field_text(3))
        self.ui.resize_art(self.ui.active_art, w, h, start_x, start_y)
        self.dismiss()


#
# layer menu dialogs
#

class AddFrameDialog(UIDialog):
    
    title = 'Add new frame'
    fields = 2
    field0_type = int
    field0_label = 'Index to add frame before:'
    field1_type = float
    field1_label = 'Hold time (in seconds) for new frame:'
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
        if not self.is_valid_frame_index(self.field0_text):
            return False, self.invalid_index_error % str(self.ui.active_art.frames + 1)
        if not self.is_valid_frame_delay(self.field1_text):
            return False, self.invalid_delay_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        index = int(self.get_field_text(0))
        delay = float(self.get_field_text(1))
        self.ui.active_art.insert_frame_before_index(index - 1, delay)
        self.dismiss()

class DuplicateFrameDialog(AddFrameDialog):
    title = 'Duplicate frame'
    confirm_caption = 'Duplicate'
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        index = int(self.get_field_text(0))
        delay = float(self.get_field_text(1))
        self.ui.active_art.duplicate_frame(self.ui.active_art.active_frame, index - 1, delay)
        self.dismiss()

class FrameDelayDialog(AddFrameDialog):
    
    fields = 1
    field0_type = float
    field0_label = 'New hold time (in seconds) for frame:'
    confirm_caption = 'Set'
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return str(self.ui.active_art.frame_delays[self.ui.active_art.active_frame])
    
    def is_input_valid(self):
        if not self.is_valid_frame_delay(self.field0_text):
            return False, self.invalid_delay_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        delay = float(self.get_field_text(0))
        self.ui.active_art.frame_delays[self.ui.active_art.active_frame] = delay
        self.dismiss()

class FrameDelayAllDialog(FrameDelayDialog):
    field0_label = 'New hold time (in seconds) for all frames:'
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        delay = float(self.get_field_text(0))
        for i in range(self.ui.active_art.frames):
            self.ui.active_art.frame_delays[i] = delay
        self.dismiss()

class FrameIndexDialog(AddFrameDialog):
    fields = 1
    field0_type = int
    field0_label = 'Move this frame before index:'
    confirm_caption = 'Set'
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        # set new frame index (effectively moving it in the sequence)
        dest_index = int(self.get_field_text(0))
        self.ui.active_art.move_frame_to_index(self.ui.active_art.active_frame, dest_index)
        self.dismiss()


#
# layer menu dialogs
#

class AddLayerDialog(UIDialog):
    
    title = 'Add new layer'
    fields = 2
    field0_type = str
    field0_label = 'Name for new layer:'
    field1_type = float
    field1_label = 'Z-depth for new layer:'
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
        valid_name = self.is_valid_layer_name(self.get_field_text(0))
        if not valid_name:
            return False, self.name_exists_error
        try: z = float(self.get_field_text(1))
        except: return False, self.invalid_z_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        name = self.get_field_text(0)
        z = float(self.get_field_text(1))
        self.ui.active_art.add_layer(z, name)
        self.dismiss()


class DuplicateLayerDialog(AddLayerDialog):
    title = 'Duplicate layer'
    confirm_caption = 'Duplicate'
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        name = self.get_field_text(0)
        z = float(self.get_field_text(1))
        self.ui.active_art.duplicate_layer(self.ui.active_art.active_layer, z, name)
        self.dismiss()


class SetLayerNameDialog(AddLayerDialog):
    
    title = 'Set layer name'
    fields = 1
    field0_type = str
    field0_label = 'New name for this layer:'
    confirm_caption = 'Rename'
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        new_name = self.get_field_text(0)
        self.ui.active_art.layer_names[self.ui.active_art.active_layer] = new_name
        self.ui.active_art.set_unsaved_changes(True)
        self.dismiss()


class SetLayerZDialog(UIDialog):
    title = 'Set layer Z-depth'
    fields = 1
    field0_type = float
    field0_label = 'Z-depth for layer:'
    confirm_caption = 'Set'
    invalid_z_error = 'Invalid number.'
    
    def get_initial_field_text(self, field_number):
        # populate with existing z
        if field_number == 0:
            return str(self.ui.active_art.layers_z[self.ui.active_art.active_layer])
    
    def is_input_valid(self):
        try: z = float(self.get_field_text(0))
        except: return False, self.invalid_z_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        new_z = float(self.get_field_text(0))
        self.ui.active_art.layers_z[self.ui.active_art.active_layer] = new_z
        self.ui.active_art.set_unsaved_changes(True)
        self.ui.app.grid.reset()
        self.dismiss()


class PaletteFromFileDialog(UIDialog):
    title = 'Create palette from file'
    confirm_caption = 'Create'
    fields = 3
    field0_type = str
    field0_label = 'Filename to create palette from:'
    field1_type = str
    field1_label = 'Filename for new palette:'
    field2_type = int
    field2_label = 'Colors in new palette:'
    field2_width = int(36 / 4)
    invalid_color_error = 'Palettes must be between 2 and 256 colors.'
    
    def get_initial_field_text(self, field_number):
        if field_number == 2:
            return str(256)
        return ''
    
    def valid_colors(self, colors):
        try: c = int(colors)
        except: return False
        return 2 <= c <= 256
    
    def is_input_valid(self):
        valid_colors = self.valid_colors(self.get_field_text(2))
        if not valid_colors:
            return False, self.invalid_color_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        src_filename = self.get_field_text(0)
        palette_filename = self.get_field_text(1)
        colors = int(self.get_field_text(2))
        new_pal = PaletteFromFile(self.ui.app, src_filename, palette_filename, colors)
        self.dismiss()


class SetCameraZoomDialog(UIDialog):
    title = 'Set camera zoom'
    confirm_caption = 'Set'
    fields = 1
    field0_type = float
    field0_label = 'New camera zoom:'
    invalid_zoom_error = 'Invalid number.'
    all_modes_visible = True
    game_mode_visible = True
    
    def get_initial_field_text(self, field_number):
        if field_number == 0:
            return str(ui.app.camera.z)
        return ''
    
    def is_input_valid(self):
        try: zoom = float(self.get_field_text(0))
        except: return False, self.invalid_zoom_error
        return True, None
    
    def confirm_pressed(self):
        valid, reason = self.is_input_valid()
        if not valid: return
        new_zoom = float(self.get_field_text(0))
        self.ui.app.camera.z = new_zoom
        self.dismiss()
