import os.path
import sdl2

from ui_element import UIElement
from ui_button import UIButton, TEXT_LEFT, TEXT_CENTER, TEXT_RIGHT
from ui_colors import UIColors
from ui_console import SaveCommand

class ConfirmButton(UIButton):
    caption = 'Confirm'
    caption_justify = TEXT_CENTER
    width = len(caption) + 2

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
    fg_color = UIColors.black
    bg_color = UIColors.white
    title = 'Test Dialog Box'
    # string message not tied to a specific field
    message = None
    other_button_visible = False
    titlebar_fg_color = UIColors.white
    titlebar_bg_color = UIColors.black
    fields = 2
    field_width = 36
    field_fg_color = UIColors.black
    field_bg_color = UIColors.lightgrey
    field0_label = 'Field 1 label:'
    field1_label = 'Field 2 label:'
    field0_width = field1_width = field_width
    # allow subclasses to override confirm caption, eg Save
    confirm_caption = None
    other_caption = None
    
    def __init__(self, ui):
        self.confirm_button = ConfirmButton(self)
        # handle confirm caption override
        if self.confirm_caption and self.confirm_button.caption != self.confirm_caption:
            self.confirm_button.caption = self.confirm_caption
            self.confirm_button.width = len(self.confirm_caption) + 2
        self.other_button = OtherButton(self)
        if self.other_caption and self.other_button.caption != self.other_caption:
            self.other_button.caption = self.other_caption
            self.other_button.width = len(self.other_caption) + 2
        self.cancel_button = CancelButton(self)
        self.confirm_button.callback = self.confirm_pressed
        self.other_button.callback = self.other_pressed
        self.cancel_button.callback = self.cancel_pressed
        self.buttons = [self.confirm_button, self.other_button, self.cancel_button]
        self.field0_text = ''
        self.field1_text = ''
        # field cursor starts on
        self.active_field = 0
        UIElement.__init__(self, ui)
        self.ui.menu_bar.close_active_menu()
    
    def reset_art(self):
        # TODO?: determine size based on contents
        # center in window
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
            msg = self.get_message()
            # TODO: split over multiple lines if too long?
            self.art.write_string(0, 0, 2, 2, msg)
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
        UIElement.reset_art(self)
    
    def get_message(self):
        return self.message
    
    def draw_fields(self, draw_field_labels=True):
        start_y = 2
        if self.message:
            # TODO: add # of message lines
            start_y += 2
        for i in range(self.fields):
            y = (i * 2) + start_y
            if draw_field_labels:
                label = getattr(self, 'field%s_label' % i)
                self.art.write_string(0, 0, 2, y, label, self.fg_color)
            y += 1
            field_width = self.get_field_width(i)
            field_text = self.get_field_text(i)
            # draw cursor at end if this is the active field
            cursor = ''
            if i == self.active_field:
                cursor = '_'
            field_text = (field_text + cursor).ljust(field_width)
            self.art.write_string(0, 0, 2, y, field_text, self.field_fg_color, self.field_bg_color)
    
    def handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        keystr = sdl2.SDL_GetKeyName(key).decode()
        field_text = self.get_field_text(self.active_field)
        if keystr == 'Return':
            self.confirm_pressed()
        elif keystr == 'Escape':
            self.cancel_pressed()
        elif keystr == 'Tab':
            # TODO: cycle through fields
            pass
        elif keystr == 'Backspace':
            if len(field_text) > 0:
                field_text = field_text[:-1]
        elif keystr == 'Space':
            field_text += ' '
        elif len(keystr) > 1:
            return
        else:
            if not shift_pressed:
                keystr = keystr.lower()
            field_text += keystr
        if len(field_text) < self.get_field_width(self.active_field):
            self.set_field_text(self.active_field, field_text)
        self.draw_fields(False)
    
    def get_field_width(self, field_number):
        return getattr(self, 'field%s_width' % field_number)
    
    def get_field_text(self, field_number):
        return getattr(self, 'field%s_text' % field_number)
    
    def set_field_text(self, field_number, new_text):
        setattr(self, 'field%s_text' % field_number, new_text)
    
    def dismiss(self):
        # let UI forget about us
        self.ui.active_dialog = None
        self.ui.elements.remove(self)
    
    def confirm_pressed(self):
        # TODO: prevent from being pressed if field contents aren't valid
        # subclasses do more here :]
        self.dismiss()
    
    def cancel_pressed(self):
        self.dismiss()
    
    def other_pressed(self):
        self.dismiss()


class SaveAsDialog(UIDialog):
    
    title = 'Save art'
    field0_label = 'Enter new name for art:'
    fields = 1
    confirm_caption = 'Save'
    
    def confirm_pressed(self):
        # run console command
        SaveCommand.execute(self.ui.console, [self.field0_text])
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
        return self.message % filename
