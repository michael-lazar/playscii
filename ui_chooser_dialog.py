import sdl2

from renderable_sprite import SpriteRenderable
from ui_dialog import UIDialog
from ui_button import UIButton
from art import UV_NORMAL, UV_ROTATE90, UV_ROTATE180, UV_ROTATE270, UV_FLIPX, UV_FLIPY
from ui_colors import UIColors


class ChooserItemButton(UIButton):
    
    "button representing a ChooserItem"
    
    item_data = None
    width = 20
    clear_before_caption_draw = True
    
    def __init__(self, element):
        UIButton.__init__(self, element)
        self.callback = self.pick_item
    
    def pick_item(self):
        if not self.item_data:
            return
        # set item selected and refresh preview
        self.element.selected_item_index = self.item_data.index
        #print('picked %s' % self.element.selected_item_index)
        self.element.reset_art(False)
        self.element.position_preview()


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
        max_scroll = len(self.element.items) - self.element.items_in_view
        if self.up and self.element.scroll_index > 0:
            self.element.scroll_index -= 1
        elif not self.up and self.element.scroll_index < max_scroll:
            self.element.scroll_index += 1
        self.element.reset_art(False)
        self.element.set_preview()
        self.element.position_preview()


class ChooserItem:
    label = 'Chooser item'
    data = None


class ChooserDialog(UIDialog):
    
    title = 'Chooser'
    confirm_caption = 'Set'
    cancel_caption = 'Close'
    message = ''
    draw_field_labels = False
    tile_width, tile_height = 60, 30
    fields = 1
    field0_label = ''
    field0_width = tile_width - 4
    item_start_x, item_start_y = 2, 4
    items_in_view = tile_height - item_start_y - 3
    no_preview_label = 'No preview available!'
    item_button_class = ChooserItemButton
    scrollbar_shade_char = 54
    flip_preview_y = True
    
    def __init__(self, ui):
        self.ui = ui
        self.items = self.get_items()
        self.selected_item_index = self.get_initial_selection()
        # start scroll index higher if initial selection would be offscreen
        self.scroll_index = 0
        if self.selected_item_index >= self.items_in_view:
            self.scroll_index = self.selected_item_index - self.items_in_view + 1
        # for convenience, create another list where 1st item button starts at 0
        self.item_buttons = []
        self.up_arrow_button, self.down_arrow_button = None, None
        # marker for preview drawing
        self.description_end_y = 0
        # UIDialog init runs: reset_art, draw_buttons etc
        UIDialog.__init__(self, ui)
        # UIDialog/UIElement initializes self.buttons, create item buttons after
        self.init_buttons()
        self.reset_art(False)
        # preview SpriteRenderable (loaded on item change?)
        self.preview_renderable = SpriteRenderable(ui.app)
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
        self.up_arrow_button = ScrollArrowButton(self)
        self.up_arrow_button.x = self.item_start_x + ChooserItemButton.width
        self.up_arrow_button.y = self.item_start_y
        self.down_arrow_button = ScrollArrowButton(self)
        self.down_arrow_button.x = self.item_start_x + ChooserItemButton.width
        self.down_arrow_button.y = self.item_start_y + self.items_in_view - 1
        self.down_arrow_button.up = False
        self.buttons += [self.up_arrow_button, self.down_arrow_button]
    
    def get_selected_data(self):
        return self.items[self.selected_item_index].data
    
    def get_initial_selection(self):
        # subclasses return index of initial selection
        return 0
    
    def set_preview(self):
        # subclasses do stuff here to get something on the preview
        pass
    
    def get_items(self):
        # subclasses generate lists of items here
        items = []
        for i in range(10):
            item = ChooserItem()
            item.label += ' %s' % i
            item.data = 'Item %s' % i
            items.append(item)
        return items
    
    def position_preview(self, reset=True):
        if reset: self.set_preview()
        qw, qh = self.art.quad_width, self.art.quad_height
        # determine x position, then width as (dialog width - x)
        x = (ChooserItemButton.width + self.item_start_x + 3) * qw
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
                continue
            item = self.items[self.scroll_index + i]
            button.caption = item.label
            button.item_data = item
            button.never_draw = False
            # highlight selected item
            if i == self.selected_item_index - self.scroll_index:
                button.normal_fg_color = UIButton.clicked_fg_color
                button.normal_bg_color = UIButton.clicked_bg_color
                button.can_hover = False
            else:
                button.normal_fg_color = UIButton.normal_fg_color
                button.normal_bg_color = UIButton.normal_bg_color
                button.can_hover = True
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
    
    def get_selected_description_lines(self):
        "subclasses provide their own logic here"
        lines = ['Description of thing:']
        lines += ['description stuff']
        return lines
    
    def draw_selected_description(self):
        x = self.tile_width - 2
        y = self.item_start_y
        lines = self.get_selected_description_lines()
        for line in lines:
            self.art.write_string(0, 0, x, y, line, None, None, True)
            y += 1
        self.description_end_y = y
    
    def reset_art(self, resize=True):
        self.reset_buttons()
        # UIDialog does: clear window, draw titlebar and confirm/cancel buttons
        # doesn't: draw message or fields
        UIDialog.reset_art(self, resize)
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
        old_idx, old_scroll = self.selected_item_index, self.scroll_index
        if keystr == 'Up':
            if self.selected_item_index == 0:
                pass
            elif self.selected_item_index == self.scroll_index:
                self.selected_item_index -= 1
                self.scroll_index -= 1
            else:
                self.selected_item_index -= 1
        elif keystr == 'Down':
            if self.selected_item_index == len(self.items) - 1:
                pass
            elif self.selected_item_index - self.scroll_index == self.items_in_view - 1:
                self.scroll_index += 1
                self.selected_item_index += 1
            else:
                self.selected_item_index += 1
        if old_idx != self.selected_item_index or old_scroll != self.scroll_index:
            self.reset_art(False)
            self.position_preview()
        UIDialog.handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed)
    
    def render(self):
        UIDialog.render(self)
        self.preview_renderable.render()
