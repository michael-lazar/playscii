 
from ui_element import UIElement, UIArt, UIRenderable
from ui_button import UIButton, TEXT_LEFT, TEXT_CENTER, TEXT_RIGHT
from ui_swatch import CharacterSetSwatch, PaletteSwatch, MIN_CHARSET_WIDTH
from ui_colors import UIColors
from renderable_line import LineRenderable, SwatchSelectionBoxRenderable
from art import UV_NORMAL, UV_ROTATE90, UV_ROTATE180, UV_ROTATE270, UV_FLIPX, UV_FLIPY
from ui_file_chooser_dialog import CharSetChooserDialog, PaletteChooserDialog

TOOL_PANE_WIDTH = 10

class ToolTabButton(UIButton):
    x, y = 0, 0
    caption_y = 1
    # width is set on the fly by popup size in reset_art
    height = 3
    caption_justify = TEXT_CENTER
    caption = 'Tools'

class CharColorTabButton(UIButton):
    caption_y = 1
    height = ToolTabButton.height
    caption_justify = TEXT_CENTER
    caption = 'Chars/Colors'

# charset view scale up/down buttons

class CharSetScaleUpButton(UIButton):
    width, height = 3, 1
    x, y = -width, ToolTabButton.height + 1
    caption = '+'
    caption_justify = TEXT_CENTER

class CharSetScaleDownButton(CharSetScaleUpButton):
    x = -CharSetScaleUpButton.width + CharSetScaleUpButton.x
    caption = '-'

# charset flip / rotate buttons

class CharXformButton(UIButton):
    hovered_fg_color = UIColors.white
    hovered_bg_color = UIColors.medgrey

class CharFlipNoButton(CharXformButton):
    x = 3 + len('Flip:') + 1
    y = CharSetScaleUpButton.y + 1
    caption = 'None'
    width = len(caption) + 2
    caption_justify = TEXT_CENTER

class CharFlipXButton(CharFlipNoButton):
    x = CharFlipNoButton.x + CharFlipNoButton.width + 1
    width = 3
    caption = 'X'

class CharFlipYButton(CharFlipXButton):
    x = CharFlipXButton.x + CharFlipXButton.width + 1
    caption = 'Y'

class CharRot0Button(CharXformButton):
    x = 3 + len('Rotation:') + 1
    y = CharFlipNoButton.y + 1
    width = 3
    caption = '0'
    caption_justify = TEXT_CENTER

class CharRot90Button(CharRot0Button):
    x = CharRot0Button.x + CharRot0Button.width + 1
    width = 4
    caption = '90'

class CharRot180Button(CharRot0Button):
    x = CharRot90Button.x + CharRot90Button.width + 1
    width = 5
    caption = '180'

class CharRot270Button(CharRot0Button):
    x = CharRot180Button.x + CharRot180Button.width + 1
    width = 5
    caption = '270'

# tool and tool settings buttons

class ToolButton(UIButton):
    "a tool entry in the tool tab's left hand pane. populated from UI.tools"
    width = TOOL_PANE_WIDTH
    caption = 'TOOLZ'
    y = ToolTabButton.height + 2

class BrushSizeUpButton(UIButton):
    width = 3
    y = ToolTabButton.height + 3
    caption = '+'
    caption_justify = TEXT_CENTER
    normal_fg_color = UIColors.white
    normal_bg_color = UIColors.medgrey

class BrushSizeDownButton(BrushSizeUpButton):
    caption = '-'

class AffectCharToggleButton(UIButton):
    width = 3
    x = TOOL_PANE_WIDTH + 2
    y = BrushSizeUpButton.y + 3
    # don't paint caption from string
    should_draw_caption = False
    normal_fg_color = UIColors.white
    normal_bg_color = UIColors.medgrey

class AffectFgToggleButton(AffectCharToggleButton):
    y = AffectCharToggleButton.y + 1

class AffectBgToggleButton(AffectCharToggleButton):
    y = AffectCharToggleButton.y + 2

class AffectXformToggleButton(AffectCharToggleButton):
    y = AffectCharToggleButton.y + 3

# charset / palette chooser buttons

class CharSetChooserButton(UIButton):
    caption = 'Set:'
    x = 1
    normal_fg_color = UIColors.black
    normal_bg_color = UIColors.white
    hovered_fg_color = UIColors.white
    hovered_bg_color = UIColors.medgrey

class PaletteChooserButton(CharSetChooserButton):
    caption = 'Palette:'


TAB_TOOLS = 0
TAB_CHAR_COLOR = 1


class ToolPopup(UIElement):
    
    visible = False
    # actual width will be based on character set + palette size and scale
    tile_width, tile_height = 20, 15
    tab_height = ToolTabButton.height
    swatch_margin = 0.05
    fg_color = UIColors.black
    bg_color = UIColors.lightgrey
    highlight_color = UIColors.white
    tool_settings_label = 'Tool Settings:'
    brush_size_label = 'Brush size:'
    affects_heading_label = 'Affects:'
    affects_char_label = 'Character'
    affects_fg_label = 'Foreground Color'
    affects_bg_label = 'Background Color'
    affects_xform_label = 'Rotation/Flip'
    flip_label = 'Flip:'
    rotation_label = 'Rotation:'
    # index of check mark character in UI charset
    check_char_index = 131
    # map classes to member names / callbacks
    button_names = {
        ToolTabButton: 'tool_tab',
        CharColorTabButton: 'char_color_tab',
    }
    char_color_tab_button_names = {
        CharSetScaleUpButton: 'scale_charset_up',
        CharSetScaleDownButton: 'scale_charset_down',
        CharSetChooserButton: 'choose_charset',
        CharFlipNoButton: 'xform_normal',
        CharFlipXButton: 'xform_flipX',
        CharFlipYButton: 'xform_flipY',
        CharRot0Button: 'xform_0',
        CharRot90Button: 'xform_90',
        CharRot180Button: 'xform_180',
        CharRot270Button: 'xform_270',
        PaletteChooserButton: 'choose_palette',
    }
    tool_tab_button_names = {
        BrushSizeUpButton: 'brush_size_up',
        BrushSizeDownButton: 'brush_size_down',
        AffectCharToggleButton: 'toggle_affect_char',
        AffectFgToggleButton: 'toggle_affect_fg',
        AffectBgToggleButton: 'toggle_affect_bg',
        AffectXformToggleButton: 'toggle_affect_xform',
    }
    
    def __init__(self, ui):
        self.ui = ui
        self.charset_swatch = CharacterSetSwatch(ui, self)
        self.palette_swatch = PaletteSwatch(ui, self)
        self.cursor_box = SwatchSelectionBoxRenderable(ui.app, self.charset_swatch.art)
        self.renderables = [self.cursor_box]
        # set by swatch.set_cursor_loc based on selection validity
        self.cursor_char = -1
        self.cursor_color = -1
        self.active_tab = TAB_CHAR_COLOR
        # create buttons from button:name map, button & callback names generated
        # group these into lists that can be combined into self.buttons
        self.common_buttons = self.create_buttons_from_map(self.button_names)
        self.char_color_tab_buttons = self.create_buttons_from_map(self.char_color_tab_button_names)
        self.tool_tab_buttons = self.create_buttons_from_map(self.tool_tab_button_names)
        # populate more tool tab buttons from UI's list of tools
        # similar to create_buttons_from_map, but class name isn't known
        # MAYBE-TODO: is there a way to unify this?
        for tool in self.ui.tools:
            tool_button = ToolButton(self)
            # caption: 1-space padding from left
            tool_button.caption = ' %s' % tool.button_caption
            tool_button_name = '%s_tool_button' % tool.name
            setattr(self, tool_button_name, tool_button)
            cb_name = '%s_pressed' % tool_button_name
            tool_button.callback = getattr(self, cb_name)
            # set a special property UI can refer to
            tool_button.tool_name = tool.name
            self.tool_tab_buttons.append(tool_button)
        UIElement.__init__(self, ui)
        # set initial tab state
        self.char_color_tab_button_pressed()
        self.xform_0_button.normal_bg_color = self.xform_normal_button.normal_bg_color = self.highlight_color
    
    def create_buttons_from_map(self, button_dict):
        buttons = []
        for button_class in button_dict:
            button = button_class(self)
            button_name = '%s_button' % button_dict[button_class]
            setattr(self, button_name, button)
            cb_name = '%s_pressed' % button_name
            button.callback = getattr(self, cb_name)
            buttons.append(button)
        return buttons
    
    def tool_tab_button_pressed(self):
        self.active_tab = TAB_TOOLS
        self.char_color_tab_button.can_hover = True
        self.char_color_tab_button.dimmed = True
        self.tool_tab_button.can_hover = False
        self.tool_tab_button.dimmed = False
        self.buttons = self.common_buttons + self.tool_tab_buttons
        self.draw_tool_tab()
        self.draw_buttons()
    
    def char_color_tab_button_pressed(self):
        self.active_tab = TAB_CHAR_COLOR
        self.tool_tab_button.can_hover = True
        self.tool_tab_button.dimmed = True
        self.char_color_tab_button.can_hover = False
        self.char_color_tab_button.dimmed = False
        self.buttons = self.common_buttons + self.char_color_tab_buttons
        self.draw_char_color_tab()
        self.draw_buttons()
    
    def scale_charset_up_button_pressed(self):
        self.charset_swatch.increase_scale()
        self.reset_art()
        self.charset_swatch.reset_loc()
        self.palette_swatch.reset_loc()
    
    def scale_charset_down_button_pressed(self):
        self.charset_swatch.decrease_scale()
        self.reset_art()
        self.charset_swatch.reset_loc()
        self.palette_swatch.reset_loc()
    
    def brush_size_up_button_pressed(self):
        # any changes to tool's setting will force redraw of settings tab
        self.ui.selected_tool.increase_brush_size()
    
    def brush_size_down_button_pressed(self):
        self.ui.selected_tool.decrease_brush_size()
    
    def toggle_affect_char_button_pressed(self):
        self.ui.selected_tool.toggle_affects_char()
    
    def toggle_affect_fg_button_pressed(self):
        self.ui.selected_tool.toggle_affects_fg()
    
    def toggle_affect_bg_button_pressed(self):
        self.ui.selected_tool.toggle_affects_bg()
    
    def toggle_affect_xform_button_pressed(self):
        self.ui.selected_tool.toggle_affects_xform()
    
    def pencil_tool_button_pressed(self):
        self.ui.set_selected_tool(self.ui.pencil_tool)
    
    def erase_tool_button_pressed(self):
        self.ui.set_selected_tool(self.ui.erase_tool)
    
    def grab_tool_button_pressed(self):
        self.ui.set_selected_tool(self.ui.grab_tool)
    
    def rotate_tool_button_pressed(self):
        self.ui.set_selected_tool(self.ui.rotate_tool)
    
    def text_tool_button_pressed(self):
        self.ui.set_selected_tool(self.ui.text_tool)
    
    def select_tool_button_pressed(self):
        self.ui.set_selected_tool(self.ui.select_tool)
    
    def paste_tool_button_pressed(self):
        self.ui.set_selected_tool(self.ui.paste_tool)
    
    def set_xform(self, new_xform):
        "tells UI elements to respect new xform"
        self.charset_swatch.set_xform(new_xform)
        self.update_xform_buttons()
    
    def update_xform_buttons(self):
        # light up button for current selected option
        button_map = {
            UV_NORMAL: self.xform_normal_button,
            UV_ROTATE90: self.xform_90_button,
            UV_ROTATE180: self.xform_180_button,
            UV_ROTATE270: self.xform_270_button,
            UV_FLIPX: self.xform_flipX_button,
            UV_FLIPY: self.xform_flipY_button
        }
        for b in button_map:
            if b == self.ui.selected_xform:
                button_map[b].normal_bg_color = self.highlight_color
            else:
                button_map[b].normal_bg_color = self.bg_color
        self.xform_0_button.normal_bg_color = self.xform_normal_button.normal_bg_color
        self.draw_buttons()
    
    def xform_normal_button_pressed(self):
        self.ui.set_selected_xform(UV_NORMAL)
    
    def xform_flipX_button_pressed(self):
        self.ui.set_selected_xform(UV_FLIPX)
    
    def xform_flipY_button_pressed(self):
        self.ui.set_selected_xform(UV_FLIPY)
    
    def xform_0_button_pressed(self):
        self.ui.set_selected_xform(UV_NORMAL)
    
    def xform_90_button_pressed(self):
        self.ui.set_selected_xform(UV_ROTATE90)
    
    def xform_180_button_pressed(self):
        self.ui.set_selected_xform(UV_ROTATE180)
    
    def xform_270_button_pressed(self):
        self.ui.set_selected_xform(UV_ROTATE270)
    
    def choose_charset_button_pressed(self):
        self.hide()
        self.ui.open_dialog(CharSetChooserDialog)
    
    def choose_palette_button_pressed(self):
        self.hide()
        self.ui.open_dialog(PaletteChooserDialog)
    
    def draw_char_color_tab(self):
        "draw non-button bits of this tab"
        # charset renderable location will be set in update()
        charset = self.ui.active_art.charset
        palette = self.ui.active_art.palette
        cqw, cqh = self.charset_swatch.art.quad_width, self.charset_swatch.art.quad_height
        self.art.clear_frame_layer(0, 0, self.bg_color, self.fg_color)
        # position & caption charset button
        y = self.tab_height + 1
        self.choose_charset_button.y = y
        self.choose_charset_button.caption = ' %s %s ' % (CharSetChooserButton.caption, charset.name)
        self.choose_charset_button.width = len(self.choose_charset_button.caption)
        # charset scale
        charset_scale = '%.2fx' % self.charset_swatch.char_scale
        x = -self.scale_charset_up_button.width * 2
        self.art.write_string(0, 0, x, y, charset_scale, None, None, True)
        # transform labels and buttons, eg
        # Transform: [Normal] [Flip X] [Flip Y]
        # Rotation: [ 0 ] [ 90] [180] [270]
        x = 3
        y += 1
        self.art.write_string(0, 0, x, y, self.flip_label)
        y += 1
        self.art.write_string(0, 0, x, y, self.rotation_label)
        # position & caption palette button
        pal_caption_y = (cqh * charset.map_height) / self.art.quad_height
        pal_caption_y += self.tab_height + 5
        self.choose_palette_button.y = int(pal_caption_y)
        self.choose_palette_button.caption = ' %s %s ' % (PaletteChooserButton.caption, palette.name)
        self.choose_palette_button.width = len(self.choose_palette_button.caption)
        # set button states so captions draw properly
        tab_width = int(self.tile_width / 2)
        self.tool_tab_button.width = tab_width
        self.char_color_tab_button.width = int(self.tile_width) - tab_width
        self.char_color_tab_button.x = tab_width
    
    def draw_tool_tab(self):
        self.art.clear_frame_layer(0, 0, self.bg_color, self.fg_color)
        # fill tool bar with dimmer color, highlight selected tool
        for y in range(self.art.height):
            for x in range(TOOL_PANE_WIDTH):
                self.art.set_color_at(0, 0, x, y, self.ui.colors.medgrey, False)
        # set selected tool BG lighter
        y = self.tab_height + 1
        for i,tool in enumerate(self.ui.tools):
            tool_button = None
            for button in self.tool_tab_buttons:
                try:
                    if button.tool_name == tool.name:
                        tool_button = button
                except:
                    pass
            tool_button.y = y+i
            if tool == self.ui.selected_tool:
                tool_button.normal_bg_color = self.ui.colors.lightgrey
            else:
                tool_button.normal_bg_color = self.ui.colors.medgrey
        # draw current tool settings
        x = TOOL_PANE_WIDTH + 1
        y = self.tab_height + 1
        label = '%s %s' % (self.ui.selected_tool.button_caption, self.tool_settings_label)
        self.art.write_string(0, 0, x, y, label)
        x += 1
        y += 2
        # brush size (if applicable)
        if self.ui.selected_tool.brush_size:
            self.brush_size_down_button.visible = True
            self.brush_size_up_button.visible = True
            label = self.brush_size_label
            # calculate X of + and - buttons based on size string
            self.brush_size_down_button.x = TOOL_PANE_WIDTH + len(label) + 2
            label += ' ' * (self.brush_size_down_button.width + 1)
            label += '%s' % self.ui.selected_tool.brush_size
            self.brush_size_up_button.x = TOOL_PANE_WIDTH + len(label) + 3
            self.art.write_string(0, 0, x, y, label)
        else:
            # if inapplicable, hide those controls
            self.brush_size_down_button.visible = False
            self.brush_size_up_button.visible = False
        if self.ui.selected_tool.affects_masks:
            # affects char/fg/bg settings
            self.toggle_affect_char_button.visible = True
            self.toggle_affect_fg_button.visible = True
            self.toggle_affect_bg_button.visible = True
            self.toggle_affect_xform_button.visible = True
            y += 2
            self.art.write_string(0, 0, x, y, self.affects_heading_label)
            y += 1
            # set affects-* button labels AND captions
            def get_affects_char(affects):
                return [0, self.check_char_index][affects]
            w = self.toggle_affect_char_button.width
            label_toggle_pairs = []
            label_toggle_pairs += [(self.affects_char_label, self.ui.selected_tool.affects_char)]
            label_toggle_pairs += [(self.affects_fg_label, self.ui.selected_tool.affects_fg_color)]
            label_toggle_pairs += [(self.affects_bg_label, self.ui.selected_tool.affects_bg_color)]
            label_toggle_pairs += [(self.affects_xform_label, self.ui.selected_tool.affects_xform)]
            for label,toggle in label_toggle_pairs:
                self.art.write_string(0, 0, x+w+1, y, '%s' % label)
                #self.art.set_tile_at(0, 0, x, y, get_affects_char(toggle), 4, 2)
                self.art.set_char_index_at(0, 0, x+1, y, get_affects_char(toggle))
                y += 1
        else:
            self.toggle_affect_char_button.visible = False
            self.toggle_affect_fg_button.visible = False
            self.toggle_affect_bg_button.visible = False
            self.toggle_affect_xform_button.visible = False
    
    def reset_art(self):
        if not self.ui.active_art:
            return
        self.charset_swatch.reset_art()
        self.palette_swatch.reset_art()
        # set panel size based on charset size
        margin = self.swatch_margin * 2
        charset = self.ui.active_art.charset
        cqw, cqh = self.charset_swatch.art.quad_width, self.charset_swatch.art.quad_height
        old_width, old_height = self.tile_width, self.tile_height
        # min width in case of tiny charsets
        charset_tile_width = max(charset.map_width, MIN_CHARSET_WIDTH)
        self.tile_width = (cqw * charset_tile_width + margin) / UIArt.quad_width
        # tile height = height of charset + distance from top of popup
        self.tile_height = (cqh * charset.map_height) / UIArt.quad_height + margin
        # account for popup info lines etc: charset name + palette name + 1 padding each
        extra_lines = 7
        # account for size of palette + bottom margin
        palette_height = ((self.palette_swatch.art.height * self.palette_swatch.art.quad_height) + self.swatch_margin) / UIArt.quad_height
        self.tile_height += self.tab_height + palette_height + extra_lines
        if old_width != self.tile_width or old_height != self.tile_height:
            self.art.resize(int(self.tile_width), int(self.tile_height))
        # panel text - position different elements based on selected tab
        if self.active_tab == TAB_CHAR_COLOR:
            self.draw_char_color_tab()
        elif self.active_tab == TAB_TOOLS:
            self.draw_tool_tab()
        self.update_xform_buttons()
        # draw button captions
        UIElement.reset_art(self)
    
    def show(self):
        # if already visible, bail - key repeat probably triggered this
        if self.visible:
            return
        if self.ui.active_dialog:
            return
        self.visible = True
        # visible, grab keyboard focus
        self.ui.keyboard_focus_element = self
        # set cursor as starting point for keyboard navigation
        self.charset_swatch.set_cursor_selection_index(self.ui.selected_char)
        if self.ui.pulldown.visible:
            self.ui.menu_bar.close_active_menu()
        self.reset_loc()
    
    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()
    
    def reset_loc(self):
        if not self.ui.active_art:
            return
        x, y = self.ui.get_screen_coords(self.ui.app.mouse_x, self.ui.app.mouse_y)
        # center on mouse
        w, h = self.tile_width * self.art.quad_width, self.tile_height * self.art.quad_height
        x -= w / 2
        y += h / 2
        # clamp to edges of screen
        self.x = max(-1, min(1 - w, x))
        self.y = min(1, max(-1 + h, y))
        # set location for sub elements
        self.renderable.x, self.renderable.y = self.x, self.y
        self.charset_swatch.reset_loc()
        self.palette_swatch.reset_loc()
    
    def hide(self):
        self.visible = False
        self.ui.keyboard_focus_element = None
        self.ui.refocus_keyboard()
    
    def set_active_charset(self, new_charset):
        self.charset_swatch.art.charset = new_charset
        self.palette_swatch.art.charset = new_charset
        # make sure selected char isn't out of bounds w/ new set
        self.ui.selected_char %= new_charset.last_index
        self.ui.status_bar.set_active_charset(new_charset)
        self.charset_swatch.reset()
        # charset width drives palette swatch width
        self.palette_swatch.reset()
        self.reset_art()
    
    def set_active_palette(self, new_palette):
        self.charset_swatch.art.palette = new_palette
        self.palette_swatch.art.palette = new_palette
        # make sure selected colors aren't out of bounds w/ new palette
        self.ui.selected_fg_color %= len(new_palette.colors) - 1
        self.ui.selected_bg_color %= len(new_palette.colors) - 1
        self.ui.status_bar.set_active_palette(new_palette)
        self.palette_swatch.reset()
        self.reset_art()
    
    def update(self):
        UIElement.update(self)
        if not self.ui.active_art:
            return
        if self.active_tab == TAB_CHAR_COLOR:
            # bail if mouse didn't move, but also respect keyboard editing
            mouse_moved = self.ui.app.mouse_dx != 0 or self.ui.app.mouse_dy != 0
            if self.ui.app.keyboard_editing:
                self.cursor_box.visible = True
            elif mouse_moved and self in self.ui.hovered_elements:
                self.cursor_box.visible = False
                x, y = self.ui.get_screen_coords(self.ui.app.mouse_x, self.ui.app.mouse_y)
                for e in [self.charset_swatch, self.palette_swatch]:
                    if e.is_inside(x, y):
                        self.cursor_box.visible = True
                        e.set_cursor_loc_from_mouse(self.cursor_box, x, y)
                        break
            # note: self.cursor_box updates in charset_swatch.update
            self.charset_swatch.update()
            self.palette_swatch.update()
        elif self.active_tab == TAB_TOOLS and self.ui.tool_settings_changed:
            self.draw_tool_tab()
            self.draw_buttons()
    
    def keyboard_navigate(self, dx, dy):
        active_swatch = self.charset_swatch if self.cursor_char != -1 else self.palette_swatch
        # TODO: can't handle cross-swatch navigation properly, restrict to chars
        active_swatch = self.charset_swatch
        # reverse up/down direction
        active_swatch.move_cursor(self.cursor_box, dx, -dy)
    
    def keyboard_select_item(self):
        # called as ui.keyboard_focus_element
        # simulate left/right click in popup to select stuff
        self.select_key_pressed(self.ui.app.il.shift_pressed)
    
    def select_key_pressed(self, mod_pressed):
        mouse_button = [1, 3][mod_pressed]
        self.clicked(mouse_button)
    
    def clicked(self, mouse_button):
        handled = UIElement.clicked(self, mouse_button)
        if handled:
            return
        # if cursor is over a char or color, make it the ui's selected one
        if self.cursor_char != -1:
            self.ui.selected_char = self.cursor_char
            # update cursor, eg keyboard select when cursor isn't beneath popup
            self.ui.app.cursor.undo_preview_edits()
            self.ui.app.cursor.update_cursor_preview()
        elif self.cursor_color != -1:
            if mouse_button == 1:
                self.ui.selected_fg_color = self.cursor_color
            elif mouse_button == 3:
                self.ui.selected_bg_color = self.cursor_color
        return True
    
    def render(self):
        if not self.visible:
            return
        UIElement.render(self)
        if self.active_tab == TAB_CHAR_COLOR:
            self.charset_swatch.render()
            self.palette_swatch.render()
            if self.cursor_char != -1 or self.cursor_color != -1:
                self.cursor_box.render()
