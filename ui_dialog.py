import platform
import sdl2
from collections import namedtuple

from ui_element import UIElement
from ui_button import UIButton, TEXT_LEFT, TEXT_CENTER, TEXT_RIGHT
from ui_colors import UIColors

from key_shifts import shift_map


Field = namedtuple('Field', ['label', # text label for field
                             'type', # supported: str int float bool
                             'width', # width in tiles of the field
                             'oneline']) # label and field drawn on same line


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
    fields = []
    # list of tuples of field #s for linked radio button options
    radio_groups = []
    default_field_width = 36
    active_field_fg_color = UIColors.white
    active_field_bg_color = UIColors.darkgrey
    inactive_field_fg_color = UIColors.black
    inactive_field_bg_color = UIColors.lightgrey
    # allow subclasses to override confirm caption, eg Save
    confirm_caption = None
    other_caption = None
    cancel_caption = None
    # center in window vs use tile_x/y to place
    center_in_window = True
    # checkbox char index (UI charset)
    checkbox_char_index = 131
    # radio buttons, filled and unfilled
    radio_true_char_index = 127
    radio_false_char_index = 126
    # field text set for bool fields with True value
    true_field_text = 'x'
    
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
        self.field_texts = []
        for i,field in enumerate(self.fields):
            text = self.get_initial_field_text(i)
            print('field %s: %s' % (i, text))
            self.field_texts.append(text)
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
        # determine height of each field from self.fields
        for field in self.fields:
            if field.oneline or field.type is bool:
                h += 2
            else:
                h += 3
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
        for i,field in enumerate(self.fields):
            field_button = DialogFieldButton(self)
            field_button.field_number = i
            field_button.width = field.width if field.type is not bool else 1
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
            # how about: transparent, red, beneath dialog bottom edge?
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
    
    def get_field_colors(self, index):
        "return FG and BG colors for field with given index"
        fg, bg = self.inactive_field_fg_color, self.inactive_field_bg_color
        # only highlight active field if we have kb focus
        if self is self.ui.keyboard_focus_element and index == self.active_field:
            fg, bg = self.active_field_fg_color, self.active_field_bg_color
        return fg, bg
    
    def draw_fields(self, with_labels=True):
        y = 2
        if self.message:
            y += len(self.get_message()) + 1
        for i,field in enumerate(self.fields):
            x = 2
            # bool values: checkbox or radio button, always draw label to right
            if field.type is bool:
                # if field index is in any radio group, it's a radio button
                is_radio = False
                for group in self.radio_groups:
                    if i in group:
                        is_radio = True
                        break
                # true/false ~ field text is 'x'
                field_true = self.field_texts[i] == self.true_field_text
                if is_radio:
                    char = self.radio_true_char_index if field_true else self.radio_false_char_index
                else:
                    char = self.checkbox_char_index if field_true else 0
                fg, bg = self.get_field_colors(i)
                self.art.set_tile_at(0, 0, x, y, char, fg, bg)
                x += 2
            # draw label
            if field.label:
                if with_labels:
                    self.art.write_string(0, 0, x, y, field.label, self.fg_color)
                if field.type is bool:
                    pass
                elif field.oneline:
                    x += len(field.label) + 1
                else:
                    y += 1
            # draw field contents
            if field.type is not bool:
                fg, bg = self.get_field_colors(i)
                text = self.field_texts[i]
                # caret for active field
                if i == self.active_field:
                    blink_on = int(self.ui.app.get_elapsed_time() / 250) % 2
                    if blink_on:
                        text += '_'
                # pad with spaces to full width of field
                text = text.ljust(field.width)
                self.art.write_string(0, 0, x, y, text, fg, bg)
            y += 2
    
    def get_field_y(self, field_index):
        "returns a Y value for where the given field (caption) should start"
        y = 2
        # add # of message lines
        if self.message:
            y += len(self.get_message()) + 1
        for i in range(field_index):
            if self.fields[i].oneline or self.fields[i].type is bool:
                y += 2
            else:
                y += 3
        return y
    
    def handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        keystr = sdl2.SDL_GetKeyName(key).decode()
        field = self.fields[self.active_field]
        field_text = self.field_texts[self.active_field]
        # special case: shortcut 'D' for 3rd button if no field input
        if len(self.fields) == 0 and keystr.lower() == 'd':
            self.other_pressed()
            return
        if keystr == '`' and not shift_pressed:
            self.ui.console.toggle()
            return
        if keystr == 'Return':
            self.confirm_pressed()
        elif keystr == 'Escape':
            self.cancel_pressed()
        # cycle through fields with up/down
        elif keystr == 'Up':
            if len(self.fields) > 1:
                self.active_field -= 1
                self.active_field %= len(self.fields)
            return
        elif keystr == 'Down':
            if len(self.fields) > 1:
                self.active_field += 1
                self.active_field %= len(self.fields)
            return
        elif keystr == 'Tab':
            # if list panel is visible, switch keyboard focus
            if self.ui.edit_list_panel.is_visible():
                self.ui.keyboard_focus_element = self.ui.edit_list_panel
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
            # TODO: if field.type is bool, toggle value
            field_text += ' '
        elif len(keystr) > 1:
            return
        else:
            if field.type is str:
                if not shift_pressed:
                    keystr = keystr.lower()
                if not keystr.isalpha() and shift_pressed:
                    keystr = shift_map.get(keystr, '')
            elif field.type is int and not keystr.isdigit() and keystr != '-':
                return
            # this doesn't guard against things like 0.00.001
            elif field.type is float and not keystr.isdigit() and keystr != '.' and keystr != '-':
                return
            field_text += keystr
        if len(field_text) < field.width:
            self.field_texts[self.active_field] = field_text
        self.draw_fields(False)
    
    def is_input_valid(self):
        "subclasses that want to filter input put logic here"
        return True, None
    
    def dismiss(self):
        # let UI forget about us
        self.ui.active_dialog = None
        if self is self.ui.keyboard_focus_element:
            self.ui.keyboard_focus_element = None
            self.ui.refocus_keyboard()
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
