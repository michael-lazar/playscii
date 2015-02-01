 
from ui_element import UIElement, UIArt, UIRenderable
from ui_button import UIButton, TEXT_LEFT, TEXT_CENTER, TEXT_RIGHT
from ui_swatch import CharacterSetSwatch, PaletteSwatch
from ui_colors import UIColors
from renderable_line import LineRenderable, SelectionBoxRenderable

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

class CharSetScaleUpButton(UIButton):
    width, height = 3, 1
    x, y = -width, ToolTabButton.height + 1
    caption = '+'
    caption_justify = TEXT_CENTER

class CharSetScaleDownButton(UIButton):
    width, height = 3, 1
    x, y = -width + CharSetScaleUpButton.x, ToolTabButton.height + 1
    caption = '-'
    caption_justify = TEXT_CENTER

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
    charset_label = 'Character Set:'
    palette_label = 'Color Palette:'
    tool_settings_label = 'Tool Settings:'
    brush_size_label = 'Brush size:'
    affects_heading_label = 'Affects:'
    affects_char_label = 'Character'
    affects_fg_label = 'Foreground Color'
    affects_bg_label = 'Background Color'
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
    }
    tool_tab_button_names = {
        BrushSizeUpButton: 'brush_size_up',
        BrushSizeDownButton: 'brush_size_down',
        AffectCharToggleButton: 'toggle_affect_char',
        AffectFgToggleButton: 'toggle_affect_fg',
        AffectBgToggleButton: 'toggle_affect_bg',
    }
    
    def __init__(self, ui):
        self.ui = ui
        self.charset_swatch = CharacterSetSwatch(ui, self)
        self.palette_swatch = PaletteSwatch(ui, self)
        self.cursor_box = SelectionBoxRenderable(ui.app, self.charset_swatch.art)
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
        self.ui.selected_tool.increase_brush_size()
        self.draw_tool_tab()
        self.draw_buttons()
    
    def brush_size_down_button_pressed(self):
        self.ui.selected_tool.decrease_brush_size()
        self.draw_tool_tab()
        self.draw_buttons()
    
    def toggle_affect_char_button_pressed(self):
        self.ui.selected_tool.affects_char = not self.ui.selected_tool.affects_char
        self.draw_tool_tab()
        self.draw_buttons()
    
    def toggle_affect_fg_button_pressed(self):
        self.ui.selected_tool.affects_fg_color = not self.ui.selected_tool.affects_fg_color
        self.draw_tool_tab()
        self.draw_buttons()
    
    def toggle_affect_bg_button_pressed(self):
        self.ui.selected_tool.affects_bg_color = not self.ui.selected_tool.affects_bg_color
        self.draw_tool_tab()
        self.draw_buttons()
    
    def pencil_tool_button_pressed(self):
        self.ui.set_selected_tool(self.ui.pencil_tool)
    
    def erase_tool_button_pressed(self):
        self.ui.set_selected_tool(self.ui.erase_tool)
    
    def grab_tool_button_pressed(self):
        self.ui.set_selected_tool(self.ui.grab_tool)
    
    def draw_char_color_tab(self):
        "draw non-button bits of this tab"
        # charset renderable location will be set in update()
        # charset label
        charset = self.ui.active_art.charset
        palette = self.ui.active_art.palette
        cqw, cqh = self.charset_swatch.art.quad_width, self.charset_swatch.art.quad_height
        self.art.clear_frame_layer(0, 0, self.bg_color, self.fg_color)
        y = self.tab_height + 1
        label = '%s %s' % (self.charset_label, charset.name)
        self.art.write_string(0, 0, 2, y, label)
        # charset scale
        charset_scale = '%.2fx' % self.charset_swatch.char_scale
        x = -self.scale_charset_up_button.width * 2
        self.art.write_string(0, 0, x, y, charset_scale, None, None, True)
        # palette label
        pal_caption_y = (cqh * charset.map_height) / self.art.quad_height
        pal_caption_y += self.tab_height + 3
        label = '%s %s' % (self.palette_label, palette.name)
        self.art.write_string(0, 0, 2, int(pal_caption_y), label)
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
        # brush size
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
            self.brush_size_down_button.visible = False
            self.brush_size_up_button.visible = False
        # affects char/fg/bg settings
        y += 2
        self.art.write_string(0, 0, x, y, self.affects_heading_label)
        y += 1
        # set affects-* button labels AND captions
        def get_affects_char(affects):
            return [0, self.check_char_index][affects]
        w = self.toggle_affect_char_button.width
        for label,toggle in [(self.affects_char_label, self.ui.selected_tool.affects_char), (self.affects_fg_label, self.ui.selected_tool.affects_fg_color), (self.affects_bg_label, self.ui.selected_tool.affects_bg_color)]:
            self.art.write_string(0, 0, x+w+1, y, '%s' % label)
            #self.art.set_tile_at(0, 0, x, y, get_affects_char(toggle), 4, 2)
            self.art.set_char_index_at(0, 0, x+1, y, get_affects_char(toggle))
            y += 1
    
    def reset_art(self):
        self.charset_swatch.reset_art()
        self.palette_swatch.reset_art()
        # set panel size based on charset size
        margin = self.swatch_margin * 2
        charset = self.ui.active_art.charset
        cqw, cqh = self.charset_swatch.art.quad_width, self.charset_swatch.art.quad_height
        old_width, old_height = self.tile_width, self.tile_height
        self.tile_width = (cqw * charset.map_width + margin) / UIArt.quad_width
        # tile height = height of charset + distance from top of popup
        self.tile_height = (cqh * charset.map_height) / UIArt.quad_height + margin
        # account for popup info lines etc: charset name + palette name + 1 padding each
        extra_lines = 5
        # account for size of palette + bottom margin
        palette_height = ((self.palette_swatch.art.height * self.palette_swatch.art.quad_height) + self.swatch_margin) / UIArt.quad_height
        self.tile_height += self.tab_height + palette_height + extra_lines
        if old_width != self.tile_width or old_height != self.tile_height:
            self.art.resize(int(self.tile_width), int(self.tile_height), self.bg_color)
        # panel text - position different elements based on selected tab
        if self.active_tab == TAB_CHAR_COLOR:
            self.draw_char_color_tab()
        elif self.active_tab == TAB_TOOLS:
            self.draw_tool_tab()
        # draw button captions
        UIElement.reset_art(self)
    
    def show(self):
        # if already visible, bail - key repeat probably triggered this
        if self.visible:
            return
        self.visible = True
        self.reset_loc()
    
    def reset_loc(self):
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
    
    def set_active_charset(self, new_charset):
        self.charset_swatch.art.charset = new_charset
        self.palette_swatch.art.charset = new_charset
        # make sure selected char isn't out of bounds w/ new set
        self.ui.selected_char %= new_charset.last_index
        self.ui.status_bar.set_active_charset(new_charset)
        self.charset_swatch.reset()
        self.reset_art()
        self.ui.active_art.set_charset(new_charset)
    
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
        if self.active_tab == TAB_CHAR_COLOR:
            if self in self.ui.hovered_elements:
                x, y = self.ui.get_screen_coords(self.ui.app.mouse_x, self.ui.app.mouse_y)
                for e in [self.charset_swatch, self.palette_swatch]:
                    if e.is_inside(x, y):
                        e.set_cursor_loc(self.cursor_box, x, y)
                        break
            # note: self.cursor_box updates in charset_swatch.update
            self.charset_swatch.update()
            self.palette_swatch.update()
    
    def clicked(self, button):
        UIElement.clicked(self, button)
        # if cursor is over a char or color, make it the ui's selected one
        if self.cursor_char != -1:
            self.ui.selected_char = self.cursor_char
        elif self.cursor_color != -1:
            if button == 1:
                self.ui.selected_fg_color = self.cursor_color
            elif button == 3:
                self.ui.selected_bg_color = self.cursor_color
    
    def render(self, elapsed_time):
        UIElement.render(self, elapsed_time)
        if self.active_tab == TAB_CHAR_COLOR:
            self.charset_swatch.render(elapsed_time)
            self.palette_swatch.render(elapsed_time)
            if self.cursor_char != -1 or self.cursor_color != -1:
                self.cursor_box.render(elapsed_time)
