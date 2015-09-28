import platform, os.path
import sdl2

from ui_element import UIElement
from ui_button import UIButton, TEXT_LEFT, TEXT_CENTER, TEXT_RIGHT
from ui_colors import UIColors
from ui_console import OpenCommand, SaveCommand, ConvertImageCommand, SetGameDirCommand, LoadGameStateCommand, SaveGameStateCommand

from art import ART_DIR, ART_FILE_EXTENSION, DEFAULT_FRAME_DELAY, DEFAULT_LAYER_Z_OFFSET
from key_shifts import shift_map
from palette import PaletteFromFile

class ConfirmButton(UIButton):
    caption = 'Confirm'
    caption_justify = TEXT_CENTER
    width = len(caption) + 2
    dimmed_fg_color = UIColors.lightgrey
    dimmed_bg_color = UIColors.white

class CancelButton(ConfirmButton):
    caption = 'Cancel'
    width = len(caption) + 2

class OtherButton(ConfirmButton):
    "button for 3rd option in some dialogs, eg Don't Save"
    caption = 'Other'
    width = len(caption) + 2
    visible = False


class UIDialog(UIElement):
    
    tile_width, tile_height = 40, 8
    # extra lines added to height beyond contents length
    extra_lines = 0
    fg_color = UIColors.black
    bg_color = UIColors.white
    title = 'Test Dialog Box'
    # string message not tied to a specific field
    message = None
    other_button_visible = False
    titlebar_fg_color = UIColors.white
    titlebar_bg_color = UIColors.black
    fields = 3
    field_width = 36
    active_field_fg_color = UIColors.white
    active_field_bg_color = UIColors.darkgrey
    inactive_field_fg_color = UIColors.black
    inactive_field_bg_color = UIColors.lightgrey
    field0_label = 'Field 1 label:'
    field1_label = 'Field 2 label:'
    field2_label = 'Field 3 label:'
    # if False, skip line where field label would go entirely
    draw_field_labels = True
    # field types - filters text input handling
    field0_type = str
    field1_type = int
    field2_type = int
    field0_width = field1_width = field2_width = field_width
    # allow subclasses to override confirm caption, eg Save
    confirm_caption = None
    other_caption = None
    cancel_caption = None
    # center in window vs use tile_x/y to place
    center_in_window = True
    
    def __init__(self, ui):
        self.ui = ui
        self.confirm_button = ConfirmButton(self)
        self.other_button = OtherButton(self)
        self.cancel_button = CancelButton(self)
        # handle caption overrides
        def caption_override(button, alt_caption):
            if alt_caption and button.caption != alt_caption:
                button.caption = alt_caption
                button.width = len(alt_caption) + 2
        caption_override(self.confirm_button, self.confirm_caption)
        caption_override(self.other_button, self.other_caption)
        caption_override(self.cancel_button, self.cancel_caption)
        self.confirm_button.callback = self.confirm_pressed
        self.other_button.callback = self.other_pressed
        self.cancel_button.callback = self.cancel_pressed
        self.buttons = [self.confirm_button, self.other_button, self.cancel_button]
        self.field0_text = self.get_initial_field_text(0)
        self.field1_text = self.get_initial_field_text(1)
        self.field2_text = self.get_initial_field_text(2)
        self.field3_text = self.get_initial_field_text(3)
        # field cursor starts on
        self.active_field = 0
        UIElement.__init__(self, ui)
        if self.ui.menu_bar and self.ui.menu_bar.active_menu_name:
            self.ui.menu_bar.close_active_menu()
    
    def get_initial_field_text(self, field_number):
        "subclasses specify a given field's initial text here"
        return ''
    
    def get_height(self, msg_lines):
        "determine size based on contents (subclasses can use custom logic)"
        # base height = 4, titlebar + padding + buttons + padding
        h = 4
        h += 0 if len(msg_lines) == 0 else len(msg_lines) + 1
        h += 3 * self.fields
        h += self.extra_lines
        return h
    
    def reset_art(self, resize=True):
        # get_message splits into >1 line if too long
        msg_lines = self.get_message() if self.message else []
        if resize:
            self.tile_height = self.get_height(msg_lines)
            self.art.resize(self.tile_width, self.tile_height)
            if self.center_in_window:
                qw, qh = self.art.quad_width, self.art.quad_height
                self.x = -(self.tile_width * qw) / 2
                self.y = (self.tile_height * qh) / 2
        # draw window
        self.art.clear_frame_layer(0, 0, self.bg_color, self.fg_color)
        s = ' ' + self.title.ljust(self.tile_width - 1)
        # invert titlebar
        self.art.write_string(0, 0, 0, 0, s, self.titlebar_fg_color, self.titlebar_bg_color)
        # message
        if self.message:
            y = 2
            for i,line in enumerate(msg_lines):
                self.art.write_string(0, 0, 2, y+i, line)
        # field caption(s)
        self.draw_fields()
        # position buttons
        self.confirm_button.x = self.tile_width - self.confirm_button.width - 2
        self.confirm_button.y = self.tile_height - 2
        if self.other_button_visible:
            self.other_button.x = self.confirm_button.x
            self.other_button.x -= self.other_button.width + 2
            self.other_button.y = self.confirm_button.y
            self.other_button.visible = True
        self.cancel_button.x = 2
        self.cancel_button.y = self.tile_height - 2
        # create field buttons so you can click em
        for i in range(self.fields):
            field_button = DialogFieldButton(self)
            field_button.field_number = i
            field_button.width = self.get_field_width(i)
            y = self.get_field_y(i) + 1
            field_button.x = 2
            field_button.y = y
            field_button.never_draw = True
            self.buttons.append(field_button)
        # draw buttons
        UIElement.reset_art(self)
    
    def update_drag(self, mouse_dx, mouse_dy):
        win_w, win_h = self.ui.app.window_width, self.ui.app.window_height
        self.x += (mouse_dx / win_w) * 2
        self.y -= (mouse_dy / win_h) * 2
        self.renderable.x, self.renderable.y = self.x, self.y
    
    def update(self):
        # redraw fields every update for cursor blink
        # (seems a waste, no real perf impact tho)
        self.draw_fields(False)
        # don't allow confirmation if all field input isn't valid
        valid, reason = self.is_input_valid()
        if valid:
            if self.confirm_button.state == 'dimmed':
                self.confirm_button.set_state('normal')
        else:
            # display reason
            # TODO: somewhere better to show this than message line?
            self.ui.message_line.post_line(reason)
            if self.confirm_button.state != 'dimmed':
                self.confirm_button.set_state('dimmed')
        UIElement.update(self)
    
    def get_message(self):
        # if a triple quoted string, split line breaks
        msg = self.message.rstrip().split('\n')
        msg_lines = []
        for line in msg:
            if line != '':
                msg_lines.append(line)
        # TODO: split over multiple lines if too long
        return msg_lines
    
    def get_field_y(self, field_index):
        "returns a Y value for where the given field (caption) should start"
        start_y = 2
        # add # of message lines
        if self.message:
            start_y += len(self.get_message()) + 1
        field_height = 3 if self.draw_field_labels else 2
        return (field_index * field_height) + start_y
    
    def draw_fields(self, with_labels=True):
        for i in range(self.fields):
            y = self.get_field_y(i)
            if with_labels and self.draw_field_labels:
                label = getattr(self, 'field%s_label' % i)
                self.art.write_string(0, 0, 2, y, label, self.fg_color)
            if self.draw_field_labels:
                y += 1
            field_width = self.get_field_width(i)
            field_text = self.get_field_text(i)
            # draw cursor at end if this is the active field
            cursor = ''
            fg, bg = self.inactive_field_fg_color, self.inactive_field_bg_color
            if i == self.active_field:
                fg, bg = self.active_field_fg_color, self.active_field_bg_color
                # blink cursor
                blink_on = int(self.ui.app.get_elapsed_time() / 250) % 2
                if blink_on:
                    cursor = '_'
            field_text = (field_text + cursor).ljust(field_width)
            self.art.write_string(0, 0, 2, y, field_text, fg, bg)
    
    def handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        keystr = sdl2.SDL_GetKeyName(key).decode()
        field_text = self.get_field_text(self.active_field)
        field_type = getattr(self, 'field%s_type' % self.active_field)
        # special case: shortcut 'D' for 3rd button if no field input
        if self.fields == 0 and keystr.lower() == 'd':
            self.other_pressed()
            return
        if keystr == '`' and not shift_pressed:
            self.ui.console.toggle()
            return
        if keystr == 'Return':
            self.confirm_pressed()
        elif keystr == 'Escape':
            self.cancel_pressed()
        elif keystr == 'Tab':
            if self.fields == 0:
                return
            # TODO: if only one field, tab through autocompletes
            if self.fields == 1:
                pass
            # cycle through fields
            if shift_pressed:
                self.active_field -= 1
            else:
                self.active_field += 1
            self.active_field %= self.fields
            return
        elif keystr == 'Backspace':
            if len(field_text) == 0:
                pass
            elif alt_pressed:
                # for file dialogs, delete back to last slash
                last_slash = field_text[:-1].rfind('/')
                # on windows, recognize backslash as well
                if platform.system() == 'Windows':
                    last_backslash = field_text[:-1].rfind('\\')
                    if last_backslash != -1 and last_slash != -1:
                        last_slash = min(last_backslash, last_slash)
                if last_slash == -1:
                    field_text = ''
                else:
                    field_text = field_text[:last_slash+1]
            else:
                field_text = field_text[:-1]
        elif keystr == 'Space':
            field_text += ' '
        elif len(keystr) > 1:
            return
        else:
            if field_type is str:
                if not shift_pressed:
                    keystr = keystr.lower()
                if not keystr.isalpha() and shift_pressed:
                    keystr = shift_map.get(keystr, '')
            elif field_type is int and not keystr.isdigit() and keystr != '-':
                return
            # this doesn't guard against things like 0.00.001
            elif field_type is float and not keystr.isdigit() and keystr != '.' and keystr != '-':
                return
            field_text += keystr
        if len(field_text) < self.get_field_width(self.active_field):
            self.set_field_text(self.active_field, field_text)
        self.draw_fields(False)
    
    def is_input_valid(self):
        "subclasses that want to filter input put logic here"
        return True, None
    
    def get_field_width(self, field_number):
        return getattr(self, 'field%s_width' % field_number)
    
    def get_field_text(self, field_number):
        return getattr(self, 'field%s_text' % field_number)
    
    def set_field_text(self, field_number, new_text):
        #print('s_f_t: setting %s to %s' % (field_number, new_text))
        setattr(self, 'field%s_text' % field_number, new_text)
    
    def dismiss(self):
        # let UI forget about us
        self.ui.active_dialog = None
        self.ui.elements.remove(self)
    
    def confirm_pressed(self):
        # subclasses do more here :]
        self.dismiss()
    
    def cancel_pressed(self):
        self.dismiss()
    
    def other_pressed(self):
        self.dismiss()


class DialogFieldButton(UIButton):
    
    "invisible button that provides clickability for input fields"
    
    caption = ''
    # set by dialog constructor
    field_number = 0
    never_draw = True
    
    def click(self):
        UIButton.click(self)
        self.element.active_field = self.field_number


class NewArtDialog(UIDialog):
    
    title = 'New art'
    fields = 3
    field0_label = 'Filename of new art:'
    field1_label = 'Width:'
    field2_label = 'Height:'
    confirm_caption = 'Create'
    field0_width = 36
    field1_width = field2_width = int(field0_width / 4)
    file_exists_error = 'File by that name already exists.'
    invalid_width_error = 'Invalid width.'
    invalid_height_error = 'Invalid height.'
    
    def __init__(self, ui):
        UIDialog.__init__(self, ui)
        # populate with good defaults
        self.field0_text = 'new%s' % len(ui.app.art_loaded_for_edit)
        self.field1_text = str(ui.app.new_art_width)
        self.field2_text = str(ui.app.new_art_height)
    
    def is_input_valid(self):
        "file can't already exist, dimensions must be >0 and <= max"
        if os.path.exists('%s%s.%s' % (ART_DIR, self.field0_text, ART_FILE_EXTENSION)):
            return False, self.file_exists_error
        if not self.is_valid_dimension(self.field1_text, self.ui.app.max_art_width):
            return False, self.invalid_width_error
        if not self.is_valid_dimension(self.field2_text, self.ui.app.max_art_height):
            return False, self.invalid_height_error
        return True, None
    
    def is_valid_dimension(self, dimension, max_dimension):
        try: dimension = int(dimension)
        except: return False
        return 0 < dimension <= max_dimension
    
    def confirm_pressed(self):
        name = self.get_field_text(0)
        w, h = int(self.get_field_text(1)), int(self.get_field_text(2))
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


class ImportEDSCIIDialog(UIDialog):
    title = 'Import EDSCII (legacy format) art'
    field0_label = 'Filename of EDSCII art to open:'
    fields = 2
    field1_label = 'Width override (leave 0 to guess):'
    field1_type = int
    confirm_caption = 'Import'
    invalid_width_error = 'Invalid width override.'
    
    def __init__(self, ui):
        UIDialog.__init__(self, ui)
        self.field1_text = '0'
    
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


class ConvertImageDialog(UIDialog):
    
    title = 'Convert raster image'
    field0_label = 'Filename of image to convert:'
    fields = 1
    confirm_caption = 'Convert'
    
    def confirm_pressed(self):
        ConvertImageCommand.execute(self.ui.console, [self.field0_text])
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
        if 1 > index or index > self.ui.active_art.frames + 1:
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
        self.ui.active_art.duplicate_frame(self.ui.active_art.active_frame, index, delay)
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
    
    def __init__(self, ui):
        UIDialog.__init__(self, ui)
        self.field2_text = str(256)
    
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

class NewGameDirDialog(UIDialog):
    title = 'New game'
    fields = 1
    field0_label = 'Name of new game directory:'
    confirm_caption = 'Create'
    game_mode_visible = True
    all_modes_visible = True
    
    # TODO: only allow names that don't already exist
    
    def confirm_pressed(self):
        if self.ui.app.gw.create_new_game(self.field0_text):
            self.ui.app.enter_game_mode()
        self.dismiss()

class SetGameDirDialog(UIDialog):
    
    title = 'Open game'
    fields = 1
    field0_label = 'Directory to load game data from:'
    confirm_caption = 'Open'
    game_mode_visible = True
    all_modes_visible = True
    
    # TODO: only allow valid game directory
    
    def confirm_pressed(self):
        SetGameDirCommand.execute(self.ui.console, [self.field0_text])
        self.dismiss()

class LoadGameStateDialog(UIDialog):
    
    title = 'Open game state'
    fields = 1
    field0_label = 'Game state file to open:'
    confirm_caption = 'Open'
    game_mode_visible = True
    all_modes_visible = True
    
    # TODO: only allow valid game state file in current game directory
    
    def confirm_pressed(self):
        LoadGameStateCommand.execute(self.ui.console, [self.field0_text])
        self.dismiss()

class SaveGameStateDialog(UIDialog):
    
    title = 'Save game state'
    fields = 1
    field0_label = 'New filename for game state:'
    confirm_caption = 'Save'
    game_mode_visible = True
    all_modes_visible = True
    
    def confirm_pressed(self):
        SaveGameStateCommand.execute(self.ui.console, [self.field0_text])
        self.dismiss()
