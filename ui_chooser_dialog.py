# coding=utf-8

import os
import sdl2

from renderable_sprite import UISpriteRenderable
from ui_dialog import UIDialog, Field
from ui_button import UIButton
from art import UV_NORMAL, UV_ROTATE90, UV_ROTATE180, UV_ROTATE270, UV_FLIPX, UV_FLIPY
from ui_colors import UIColors


class ChooserItemButton(UIButton):
    
    "button representing a ChooserItem"
    
    item = None
    width = 20
    big_width = 30
    clear_before_caption_draw = True
    
    def __init__(self, element):
        # more room for list items if screen is wide enough
        if element.ui.width_tiles - 20 > element.big_width:
            self.width = self.big_width
        UIButton.__init__(self, element)
        self.callback = self.pick_item
    
    def pick_item(self):
        if not self.item:
            return
        self.item.picked(self.element)


class ScrollArrowButton(UIButton):
    
    "button that scrolls up or down in a chooser item view"
    
    arrow_char = 129
    up = True
    normal_bg_color = UIDialog.bg_color
    dimmed_fg_color = UIColors.medgrey
    dimmed_bg_color = UIDialog.bg_color
    
    def draw_caption(self):
        xform = [UV_FLIPY, UV_NORMAL][self.up]
        self.element.art.set_tile_at(0, 0, self.x, self.y + self.caption_y,
                                     self.arrow_char, None, None, xform)
    
    def callback(self):
        if self.up and self.element.scroll_index > 0:
            self.element.scroll_index -= 1
        elif not self.up and self.element.scroll_index < self.element.get_max_scroll():
            self.element.scroll_index += 1
        self.element.load_selected_item()
        self.element.reset_art(False)
        self.element.set_preview()
        self.element.position_preview()


class ChooserItem:
    
    label = 'Chooser item'
    
    def __init__(self, index, name):
        self.index = index
        # item's unique name, eg a filename
        self.name = name
        self.label = self.get_label()
        # validity flag lets ChooserItem subclasses exclude themselves
        self.valid = True
    
    def get_label(self): return self.name
    
    def get_description_lines(self): return []
    
    def get_preview_texture(self): return None
    
    def load(self, app): pass
    
    def picked(self, element):
        # set item selected and refresh preview
        element.set_selected_item_index(self.index)


class ChooserDialog(UIDialog):
    
    title = 'Chooser'
    confirm_caption = 'Set'
    cancel_caption = 'Close'
    message = ''
    # if True, chooser shows files; show filename on first line of description
    show_filenames = False
    directory_aware = False
    tile_width, tile_height = 60, 20
    # use these if screen is big enough
    big_width, big_height = 80, 30
    fields = [
        Field(label='', type=str, width=tile_width - 4, oneline=True)
    ]
    item_start_x, item_start_y = 2, 4
    no_preview_label = 'No preview available!'
    show_preview_image = True
    item_button_class = ChooserItemButton
    chooser_item_class = ChooserItem
    scrollbar_shade_char = 54
    flip_preview_y = True
    
    def __init__(self, ui, options):
        self.ui = ui
        # semikludge: track whether user has selected anything in a new dir,
        # so double click behavior is consistent even on initial selections
        self.first_selection_made = False
        if self.ui.width_tiles - 20 > self.big_width:
            self.tile_width = self.big_width
            self.fields[0] = Field(label='', type=str,
                                   width=self.tile_width - 4, oneline=True)
        if self.ui.height_tiles - 30 > self.big_height:
            self.tile_height = self.big_height
        self.items_in_view = self.tile_height - self.item_start_y - 3
        self.field_texts = ['']
        # set active field earlier than UIDialog.init so set_initial_dir
        # can change its text
        self.active_field = 0
        if self.directory_aware:
            self.set_initial_dir()
        self.selected_item_index = 0
        # scroll index - how far into items list current screen view begins
        self.scroll_index = 0
        self.items = self.get_items()
        self.set_selected_item_index(self.get_initial_selection(), True, False)
        self.load_selected_item()
        # start scroll index higher if initial selection would be offscreen
        if self.selected_item_index >= self.items_in_view:
            self.scroll_index = self.selected_item_index - self.items_in_view + 1
        # for convenience, create another list where 1st item button starts at 0
        self.item_buttons = []
        self.up_arrow_button, self.down_arrow_button = None, None
        # marker for preview drawing
        self.description_end_y = 0
        # UIDialog init runs: reset_art, draw_buttons etc
        UIDialog.__init__(self, ui, options)
        # UIDialog/UIElement initializes self.buttons, create item buttons after
        self.init_buttons()
        self.reset_art(False)
        # preview SpriteRenderable (loaded on item change?)
        self.preview_renderable = UISpriteRenderable(ui.app)
        # don't blend preview images, eg charsets
        self.preview_renderable.blend = False
        # offset into items list view provided by buttons starts from
        self.position_preview()
    
    def init_buttons(self):
        for i in range(self.items_in_view):
            button = self.item_button_class(self)
            button.x = self.item_start_x
            button.y = i + self.item_start_y
            self.buttons.append(button)
            self.item_buttons.append(button)
        # create scrollbar buttons
        self.item_button_width = self.item_buttons[0].width
        self.up_arrow_button = ScrollArrowButton(self)
        self.up_arrow_button.x = self.item_start_x + self.item_button_width
        self.up_arrow_button.y = self.item_start_y
        self.down_arrow_button = ScrollArrowButton(self)
        self.down_arrow_button.x = self.item_start_x + self.item_button_width
        self.down_arrow_button.y = self.item_start_y + self.items_in_view - 1
        self.down_arrow_button.up = False
        self.buttons += [self.up_arrow_button, self.down_arrow_button]
    
    def set_initial_dir(self):
        # for directory-aware dialogs, subclasses specify here where to start
        self.current_dir = '.'
    
    def change_current_dir(self, new_dir):
        # check permissions:
        # os.access(new_dir, os.R_OK) seems to always return True,
        # so try/catch listdir instead
        try:
            l = os.listdir(new_dir)
        except PermissionError as e:
            line = 'No permission to access %s!' % os.path.abspath(new_dir)
            self.ui.message_line.post_line(line, error=True)
            return False
        self.current_dir = new_dir
        if not self.current_dir.endswith('/'):
            self.current_dir += '/'
        # redo items and redraw
        self.selected_item_index = 0
        self.scroll_index = 0
        self.field_texts[self.active_field] = self.current_dir
        self.items = self.get_items()
        self.reset_art(False)
        return True
    
    def set_selected_item_index(self, new_index, set_field_text=True,
                                update_view=True):
        """
        set the view's selected item to specified index
        perform usually-necessary refresh functions for convenience
        """
        move_dir = new_index - self.selected_item_index
        self.selected_item_index = new_index
        can_scroll = len(self.items) > self.items_in_view
        should_scroll = self.selected_item_index >= self.scroll_index + self.items_in_view or self.selected_item_index < self.scroll_index
        if not can_scroll:
            self.scroll_index = 0
        elif should_scroll:
            # keep selection in bounds
            self.selected_item_index = min(self.selected_item_index, len(self.items)-1)
            # scrolling up
            if move_dir <= 0:
                self.scroll_index = self.selected_item_index
            # scrolling down
            elif move_dir > 0 and self.selected_item_index - self.scroll_index == self.items_in_view:
                self.scroll_index = self.selected_item_index - self.items_in_view + 1
            # keep scroll in bounds
            self.scroll_index = min(self.scroll_index, self.get_max_scroll())
        # don't select/load null items
        if set_field_text:
            item = self.get_selected_item()
            if item:
                self.field_texts[self.active_field] = item.name
        if update_view:
            self.load_selected_item()
            self.reset_art(False)
            self.position_preview()
    
    def get_max_scroll(self):
        return len(self.items) - self.items_in_view
    
    def get_selected_item(self):
        # return None if out of bounds
        return self.items[self.selected_item_index] if self.selected_item_index < len(self.items) else None
    
    def load_selected_item(self):
        item = self.get_selected_item()
        item.load(self.ui.app)
    
    def get_initial_selection(self):
        # subclasses return index of initial selection
        return 0
    
    def set_preview(self):
        item = self.get_selected_item()
        if self.show_preview_image:
            self.preview_renderable.texture = item.get_preview_texture(self.ui.app)
    
    def get_items(self):
        # subclasses generate lists of items here
        return []
    
    def position_preview(self, reset=True):
        if reset:
            self.set_preview()
        if not self.preview_renderable.texture:
            return
        qw, qh = self.art.quad_width, self.art.quad_height
        # determine x position, then width as (dialog width - x)
        x = (self.item_button_width + self.item_start_x + 3) * qw
        self.preview_renderable.x = self.x + x
        self.preview_renderable.scale_x = (self.tile_width - 2) * qw - x
        # determine height based on width, then y position
        img_inv_aspect = self.preview_renderable.texture.height / self.preview_renderable.texture.width
        screen_aspect = self.ui.app.window_width / self.ui.app.window_height
        self.preview_renderable.scale_y = self.preview_renderable.scale_x * img_inv_aspect * screen_aspect
        y = (self.description_end_y + 1) * qh
        # if preview height is above max allotted size, set height to fill size
        # and scale down width
        max_y = (self.tile_height - 3) * qh
        if self.preview_renderable.scale_y > max_y - y:
            self.preview_renderable.scale_y = max_y - y
            self.preview_renderable.scale_x = self.preview_renderable.scale_y * (1 / img_inv_aspect) * (1 / screen_aspect)
        # flip in Y for some (palettes) but not for others (charsets)
        if self.flip_preview_y:
            self.preview_renderable.scale_y = -self.preview_renderable.scale_y
        else:
            y += self.preview_renderable.scale_y
        self.preview_renderable.y = self.y - y
    
    def get_height(self, msg_lines):
        return self.tile_height
    
    def reset_buttons(self):
        # (re)generate buttons from contents of self.items
        for i,button in enumerate(self.item_buttons):
            # ??? each button's callback loads charset/palette/whatev
            if i >= len(self.items):
                button.never_draw = True
                # clear item, might be left over from a previous dir view!
                button.item = None
                continue
            item = self.items[self.scroll_index + i]
            button.caption = item.label
            button.item = item
            button.never_draw = False
            # highlight selected item
            if i == self.selected_item_index - self.scroll_index:
                button.normal_fg_color = UIButton.clicked_fg_color
                button.normal_bg_color = UIButton.clicked_bg_color
                # still allow hover and click
                button.hovered_fg_color = UIButton.clicked_fg_color
                button.hovered_bg_color = UIButton.clicked_bg_color
            else:
                button.normal_fg_color = UIButton.normal_fg_color
                button.normal_bg_color = UIButton.normal_bg_color
                button.hovered_fg_color = UIButton.hovered_fg_color
                button.hovered_bg_color = UIButton.hovered_bg_color
        # init_buttons has not yet run on first reset_art
        if not self.up_arrow_button:
            return
        # dim scroll buttons if we don't have enough items to scroll
        state, hover = 'normal', True
        if len(self.items) <= self.items_in_view:
            state = 'dimmed'
            hover = False
        for button in [self.up_arrow_button, self.down_arrow_button]:
            button.set_state(state)
            button.can_hover = hover
    
    def get_description_filename(self, item):
        "returns a description-appropriate filename for given item"
        # truncate from start to fit in description area if needed
        max_width = self.tile_width
        max_width -= self.item_start_x + self.item_button_width + 5
        if len(item.name) > max_width - 1:
            return '…' + item.name[-max_width:]
        return item.name
    
    def get_selected_description_lines(self):
        item = self.get_selected_item()
        lines = []
        if self.show_filenames:
            lines += [self.get_description_filename(item)]
        lines += item.get_description_lines() or []
        return lines
    
    def draw_selected_description(self):
        x = self.tile_width - 2
        y = self.item_start_y
        lines = self.get_selected_description_lines()
        for line in lines:
            # trim line if it's too long
            max_width = self.tile_width - self.item_button_width - 7
            line = line[:max_width]
            self.art.write_string(0, 0, x, y, line, None, None,
                                  right_justify=True)
            y += 1
        self.description_end_y = y
    
    def reset_art(self, resize=True):
        self.reset_buttons()
        # UIDialog does: clear window, draw titlebar and confirm/cancel buttons
        # doesn't: draw message or fields
        UIDialog.reset_art(self, resize, clear_buttons=False)
        # init_buttons hasn't run yet on first call to reset_art
        if not self.up_arrow_button:
            return
        self.draw_selected_description()
        # draw scrollbar shading
        # dim if no scrolling
        fg = self.up_arrow_button.normal_fg_color
        if len(self.items) <= self.items_in_view:
            fg = self.up_arrow_button.dimmed_fg_color
        for y in range(self.up_arrow_button.y + 1, self.down_arrow_button.y):
            self.art.set_tile_at(0, 0, self.up_arrow_button.x, y,
                                 self.scrollbar_shade_char, fg)
    
    def update_drag(self, mouse_dx, mouse_dy):
        UIDialog.update_drag(self, mouse_dx, mouse_dy)
        # update thumbnail renderable's position too
        self.position_preview(False)
    
    def handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        keystr = sdl2.SDL_GetKeyName(key).decode()
        # up/down keys navigate list
        new_index = self.selected_item_index
        navigated = False
        if keystr == 'Return':
            # if handle_enter returns True, bail before rest of input handling -
            # make sure any changes to handle_enter are safe for this!
            if self.handle_enter(shift_pressed, alt_pressed, ctrl_pressed):
                return
        elif keystr == 'Up':
            navigated = True
            if self.selected_item_index > 0:
                new_index -= 1
        elif keystr == 'Down':
            navigated = True
            if self.selected_item_index < len(self.items) - 1:
                new_index += 1
        elif keystr == 'PageUp':
            navigated = True
            page_size = int(self.items_in_view / 2)
            new_index -= page_size
            new_index = max(0, new_index)
            # scroll follows selection jumps
            self.scroll_index -= page_size
            self.scroll_index = max(0, self.scroll_index)
        elif keystr == 'PageDown':
            navigated = True
            page_size = int(self.items_in_view / 2)
            new_index += page_size
            new_index = min(new_index, len(self.items) - 1)
            self.scroll_index += page_size
            self.scroll_index = min(self.scroll_index, self.get_max_scroll())
        # home/end: beginning/end of list, respectively
        elif keystr == 'Home':
            navigated = True
            new_index = 0
            self.scroll_index = 0
        elif keystr == 'End':
            navigated = True
            new_index = len(self.items) - 1
            self.scroll_index = len(self.items) - self.items_in_view
        self.set_selected_item_index(new_index, set_field_text=navigated)
        # handle alphanumeric input etc
        UIDialog.handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed)
        # if we didn't navigate, seek based on new alphanumeric input
        if not navigated:
            self.text_input_seek()
    
    def text_input_seek(self):
        field_text = self.field_texts[self.active_field]
        if field_text.strip() == '':
            return
        # seek should be case-insensitive
        field_text = field_text.lower()
        # field text may be a full path; only care about the base
        field_text = os.path.basename(field_text)
        for i,item in enumerate(self.items):
            # match to base item name within dir
            # (if it's a dir, snip last / for match)
            item_base = item.name.lower()
            if item_base.endswith('/'):
                item_base = item_base[:-1]
            item_base = os.path.basename(item_base)
            item_base = os.path.splitext(item_base)[0]
            if item_base.startswith(field_text):
                self.set_selected_item_index(i, set_field_text=False)
                break
    
    def handle_enter(self, shift_pressed, alt_pressed, ctrl_pressed):
        "handle Enter key, return False if rest of handle_input should continue"
        # if selected item is already in text field, pick it
        field_text = self.field_texts[self.active_field]
        selected_item = self.get_selected_item()
        if field_text.strip() == '':
            self.field_texts[self.active_field] = field_text = selected_item.name
            return True
        if field_text == selected_item.name:
            # this (and similar following cases) should count as having
            # made a selection
            self.first_selection_made = True
            selected_item.picked(self)
            return True
        # else navigate to directory or file if it's real
        if not os.path.exists(field_text):
            self.field_texts[self.active_field] = selected_item.name
            return True
        # special case for parent dir ..
        if self.directory_aware and field_text == self.current_dir and selected_item.name == '..':
            self.first_selection_made = True
            return self.change_current_dir('..')
        if self.directory_aware and os.path.isdir(field_text):
            self.first_selection_made = True
            return self.change_current_dir(field_text)
        if os.path.isfile(field_text):
            file_dir_name = os.path.dirname(field_text)
            # if a file, change to its dir and select it
            if self.directory_aware and file_dir_name != self.current_dir:
                if self.change_current_dir(file_dir_name):
                    for i,item in enumerate(self.items):
                        if item.name == field_text:
                            self.set_selected_item_index(i)
                            item.picked(self)
                    return True
        return False
    
    def render(self):
        UIDialog.render(self)
        if self.show_preview_image and self.preview_renderable.texture:
            self.preview_renderable.render()
