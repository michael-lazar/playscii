import os.path, time
from math import ceil

from ui_element import UIElement, UIArt, UIRenderable
from ui_button import UIButton, TEXT_LEFT, TEXT_CENTER, TEXT_RIGHT
from ui_colors import UIColors
from renderable_line import UIRenderableX
from art import uv_names

# buttons to toggle "affects" status / cycle through choices, respectively

class StatusBarToggleButton(UIButton):
    caption_justify = TEXT_RIGHT

class StatusBarCycleButton(UIButton):
    # do different stuff for left vs right click
    pass_mouse_button = True
    should_draw_caption = False
    width = 3

class CharToggleButton(StatusBarToggleButton):
    x = 0
    caption = 'ch:'
    width = len(caption) + 1

class CharCycleButton(StatusBarCycleButton):
    x = CharToggleButton.width

class FGToggleButton(StatusBarToggleButton):
    x = CharCycleButton.x + CharCycleButton.width
    caption = 'fg:'
    width = len(caption) + 1

class FGCycleButton(StatusBarCycleButton):
    x = FGToggleButton.x + FGToggleButton.width

class BGToggleButton(StatusBarToggleButton):
    x = FGCycleButton.x + FGCycleButton.width
    caption = 'bg:'
    width = len(caption) + 1

class BGCycleButton(StatusBarCycleButton):
    x = BGToggleButton.x + BGToggleButton.width

class XformToggleButton(StatusBarToggleButton):
    x = BGCycleButton.x + BGCycleButton.width
    caption = 'xform:'
    width = len(caption) + 1

# class for things like xform and tool whose captions you can cycle through
class StatusBarTextCycleButton(StatusBarCycleButton):
    should_draw_caption = True
    caption_justify = TEXT_CENTER
    normal_fg_color = UIColors.lightgrey
    normal_bg_color = UIColors.black
    hovered_fg_color = UIColors.lightgrey
    hovered_bg_color = UIColors.black
    clicked_fg_color = UIColors.black
    clicked_bg_color = UIColors.white

class XformCycleButton(StatusBarTextCycleButton):
    x = XformToggleButton.x + XformToggleButton.width
    width = len('Rotate 180')
    caption = uv_names[0]

class ToolCycleButton(StatusBarTextCycleButton):
    x = XformCycleButton.x + XformCycleButton.width + len('tool:') + 1
    # width and caption are set during status bar init after button is created

class FileCycleButton(StatusBarTextCycleButton):
    caption = '[nothing]'

class LayerCycleButton(StatusBarTextCycleButton):
    caption = 'X/Y'
    width = len(caption)

class FrameCycleButton(StatusBarTextCycleButton):
    caption = 'X/Y'
    width = len(caption)

class ZoomSetButton(StatusBarTextCycleButton):
    caption = '100.0'
    width = len(caption)

class StatusBarUI(UIElement):
    
    snap_bottom = True
    snap_left = True
    always_consume_input = True
    dim_color = 12
    swatch_width = 3
    char_swatch_x = CharCycleButton.x
    fg_swatch_x = FGCycleButton.x
    bg_swatch_x = BGCycleButton.x
    tool_label = 'tool:'
    tool_label_x = XformCycleButton.x + XformCycleButton.width + 1
    tile_label = 'tile:'
    layer_label = 'layer:'
    frame_label = 'frame:'
    zoom_label = '%'
    right_items_width = len(tile_label) + len(layer_label) + len(frame_label) + (len('X/Y') + 2) * 2 + len('XX/YY') + 2 + len(zoom_label) + 10
    button_names = {
        CharToggleButton: 'char_toggle',
        CharCycleButton: 'char_cycle',
        FGToggleButton: 'fg_toggle',
        FGCycleButton: 'fg_cycle',
        BGToggleButton: 'bg_toggle',
        BGCycleButton: 'bg_cycle',
        XformToggleButton: 'xform_toggle',
        XformCycleButton: 'xform_cycle',
        ToolCycleButton: 'tool_cycle',
        FileCycleButton: 'file_cycle',
        LayerCycleButton: 'layer_cycle',
        FrameCycleButton: 'frame_cycle',
        ZoomSetButton: 'zoom_set'
    }
    
    def __init__(self, ui):
        art = ui.active_art
        self.ui = ui
        # create 3 custom Arts w/ source charset and palette, renderables for each
        art_name = '%s_%s' % (int(time.time()), self.__class__.__name__)
        self.char_art = UIArt(art_name, ui.app, art.charset, art.palette, self.swatch_width, 1)
        self.char_renderable = UIRenderable(ui.app, self.char_art)
        self.fg_art = UIArt(art_name, ui.app, art.charset, art.palette, self.swatch_width, 1)
        self.fg_renderable = UIRenderable(ui.app, self.fg_art)
        self.bg_art = UIArt(art_name, ui.app, art.charset, art.palette, self.swatch_width, 1)
        self.bg_renderable = UIRenderable(ui.app, self.bg_art)
        # "dimmed out" box
        self.dim_art = UIArt(art_name, ui.app, ui.charset, ui.palette, self.swatch_width + self.char_swatch_x, 1)
        self.dim_renderable = UIRenderable(ui.app, self.dim_art)
        self.dim_renderable.alpha = 0.75
        # separate dimmed out box for xform, easier this way
        xform_width = XformToggleButton.width + XformCycleButton.width
        self.dim_xform_art = UIArt(art_name, ui.app, ui.charset, ui.palette, xform_width, 1)
        self.dim_xform_renderable = UIRenderable(ui.app, self.dim_xform_art)
        self.dim_xform_renderable.alpha = 0.75
        # create clickable buttons
        self.buttons = []
        for button_class, button_name in self.button_names.items():
            button = button_class(self)
            setattr(self, button_name + '_button', button)
            cb_name = '%s_button_pressed' % button_name
            button.callback = getattr(self, cb_name)
            self.buttons.append(button)
            # some button captions, widths, locations will be set in reset_art
        # determine total width of left-justified items
        self.left_items_width = self.tool_cycle_button.x + self.tool_cycle_button.width + 15
        # set some properties in bulk
        self.renderables = []
        for r in [self.char_renderable, self.fg_renderable, self.bg_renderable,
                  self.dim_renderable, self.dim_xform_renderable]:
            r.ui = ui
            r.grain_strength = 0
            # add to list of renderables to manage eg destroyed on quit
            self.renderables.append(r)
        # red X for transparent colors
        self.x_renderable = UIRenderableX(ui.app, self.char_art)
        # give it a special reference to this element
        self.x_renderable.status_bar = self
        self.renderables.append(self.x_renderable)
        UIElement.__init__(self, ui)
    
    # button callbacks
    
    def char_toggle_button_pressed(self):
        if self.ui.active_dialog: return
        self.ui.selected_tool.toggle_affects_char()
    
    def char_cycle_button_pressed(self, mouse_button):
        if self.ui.active_dialog: return
        if mouse_button == 1:
            self.ui.select_char(self.ui.selected_char + 1)
        elif mouse_button == 3:
            self.ui.select_char(self.ui.selected_char - 1)
    
    def fg_toggle_button_pressed(self):
        if self.ui.active_dialog: return
        self.ui.selected_tool.toggle_affects_fg()
    
    def fg_cycle_button_pressed(self, mouse_button):
        if self.ui.active_dialog: return
        if mouse_button == 1:
            self.ui.select_fg(self.ui.selected_fg_color + 1)
        elif mouse_button == 3:
            self.ui.select_fg(self.ui.selected_fg_color - 1)
    
    def bg_toggle_button_pressed(self):
        if self.ui.active_dialog: return
        self.ui.selected_tool.toggle_affects_bg()
    
    def bg_cycle_button_pressed(self, mouse_button):
        if self.ui.active_dialog: return
        if mouse_button == 1:
            self.ui.select_bg(self.ui.selected_bg_color + 1)
        elif mouse_button == 3:
            self.ui.select_bg(self.ui.selected_bg_color - 1)
    
    def xform_toggle_button_pressed(self):
        if self.ui.active_dialog: return
        self.ui.selected_tool.toggle_affects_xform()
    
    def xform_cycle_button_pressed(self, mouse_button):
        if self.ui.active_dialog: return
        if mouse_button == 1:
            self.ui.cycle_selected_xform()
        elif mouse_button == 3:
            self.ui.cycle_selected_xform(True)
        # update caption with new xform
        self.xform_cycle_button.caption = uv_names[self.ui.selected_xform]
    
    def tool_cycle_button_pressed(self, mouse_button):
        if self.ui.active_dialog: return
        if mouse_button == 1:
            self.ui.cycle_selected_tool()
        elif mouse_button == 3:
            self.ui.cycle_selected_tool(True)
        self.tool_cycle_button.caption = self.ui.selected_tool.button_caption
    
    def file_cycle_button_pressed(self, mouse_button):
        if not self.ui.active_art: return
        if self.ui.active_dialog: return
        if mouse_button == 1:
            self.ui.next_active_art()
        elif mouse_button == 3:
            self.ui.previous_active_art()
    
    def layer_cycle_button_pressed(self, mouse_button):
        if not self.ui.active_art: return
        if self.ui.active_dialog: return
        if mouse_button == 1:
            self.ui.set_active_layer(self.ui.active_art.active_layer + 1)
        elif mouse_button == 3:
            self.ui.set_active_layer(self.ui.active_art.active_layer - 1)
    
    def frame_cycle_button_pressed(self, mouse_button):
        if not self.ui.active_art: return
        if self.ui.active_dialog: return
        if mouse_button == 1:
            self.ui.set_active_frame(self.ui.active_art.active_frame + 1)
        elif mouse_button == 3:
            self.ui.set_active_frame(self.ui.active_art.active_frame - 1)
    
    def zoom_set_button_pressed(self, mouse_button):
        if not self.ui.active_art: return
        if self.ui.active_dialog: return
        if mouse_button == 1:
            self.ui.app.camera.zoom_proportional(1)
        elif mouse_button == 3:
            self.ui.app.camera.zoom_proportional(-1)
    
    def reset_art(self):
        UIElement.reset_art(self)
        self.tile_width = ceil(self.ui.width_tiles * self.ui.scale)
        # must resize here, as window width will vary
        self.art.resize(self.tile_width, self.tile_height)
        # write chars/colors to the art
        self.rewrite_art()
        self.x_renderable.scale_x = self.char_art.width
        self.x_renderable.scale_y = -self.char_art.height
        # dim box
        self.dim_art.clear_frame_layer(0, 0, self.ui.colors.white)
        self.dim_art.update()
        self.dim_xform_art.clear_frame_layer(0, 0, self.ui.colors.white)
        self.dim_xform_art.update()
        # rebuild geo, elements may be new dimensions
        self.dim_art.geo_changed = True
        self.dim_xform_art.geo_changed = True
        self.char_art.geo_changed = True
        self.fg_art.geo_changed = True
        self.bg_art.geo_changed = True
    
    def rewrite_art(self):
        bg = self.ui.colors.white
        self.art.clear_frame_layer(0, 0, bg)
        # if user is making window reeeeally skinny, bail
        if self.tile_width < self.left_items_width:
            return
        # draw tool label
        self.art.write_string(0, 0, self.tool_label_x, 0, self.tool_label,
                              self.ui.palette.darkest_index)
        # only draw right side info if the window is wide enough
        if self.art.width > self.left_items_width + self.right_items_width:
            self.file_cycle_button.visible = True
            self.layer_cycle_button.visible = True
            self.frame_cycle_button.visible = True
            self.zoom_set_button.visible = True
            self.write_right_elements()
        else:
            self.file_cycle_button.visible = False
            self.layer_cycle_button.visible = False
            self.frame_cycle_button.visible = False
            self.zoom_set_button.visible = False
    
    def set_active_charset(self, new_charset):
        self.char_art.charset = self.fg_art.charset = self.bg_art.charset = new_charset
        self.reset_art()
    
    def set_active_palette(self, new_palette):
        self.char_art.palette = self.fg_art.palette = self.bg_art.palette = new_palette
        self.reset_art()
    
    def update_button_captions(self):
        "set captions for buttons that change from selections"
        art = self.ui.active_art
        self.xform_cycle_button.caption = uv_names[self.ui.selected_xform]
        self.tool_cycle_button.caption = self.ui.selected_tool.button_caption
        self.tool_cycle_button.width = len(self.tool_cycle_button.caption) + 2
        # right edge elements
        self.file_cycle_button.caption = os.path.basename(art.filename) if art else FileCycleButton.caption
        self.file_cycle_button.width = len(self.file_cycle_button.caption) + 2
        # NOTE: button X offsets will be set in write_right_elements
        null = '---'
        layers = art.layers if art else 0
        layer = '%s/%s' % (art.active_layer + 1, layers) if art else null
        self.layer_cycle_button.caption = layer
        self.layer_cycle_button.width = len(self.layer_cycle_button.caption)
        frames = art.frames if art else 0
        frame = '%s/%s' % (art.active_frame + 1, frames) if art else null
        self.frame_cycle_button.caption = frame
        self.frame_cycle_button.width = len(self.frame_cycle_button.caption)
        # zoom %
        zoom = '%.1f' % self.ui.app.camera.get_current_zoom_pct() if art else null
        self.zoom_set_button.caption = zoom[:5] # maintain size
    
    def update(self):
        if not self.ui.active_art:
            return
        # update buttons
        UIElement.update(self)
        # set color swatches
        for i in range(self.swatch_width):
            self.char_art.set_color_at(0, 0, i, 0, self.ui.selected_bg_color, False)
            self.fg_art.set_color_at(0, 0, i, 0, self.ui.selected_fg_color, False)
            self.bg_art.set_color_at(0, 0, i, 0, self.ui.selected_bg_color, False)
        # set char w/ correct FG color and xform
        self.char_art.set_char_index_at(0, 0, 1, 0, self.ui.selected_char)
        self.char_art.set_color_at(0, 0, 1, 0, self.ui.selected_fg_color, True)
        self.char_art.set_char_transform_at(0, 0, 1, 0, self.ui.selected_xform)
        # position elements
        self.position_swatch(self.char_renderable, self.char_swatch_x)
        self.position_swatch(self.fg_renderable, self.fg_swatch_x)
        self.position_swatch(self.bg_renderable, self.bg_swatch_x)
        # update buttons before redrawing art (ie non-interactive bits)
        self.update_button_captions()
        for art in [self.char_art, self.fg_art, self.bg_art]:
            art.update()
        self.rewrite_art()
        self.draw_buttons()
    
    def position_swatch(self, renderable, x_offset):
        renderable.x = (self.char_art.quad_width * x_offset) - 1
        renderable.y = self.char_art.quad_height - 1
    
    def reset_loc(self):
        UIElement.reset_loc(self)
    
    def write_right_elements(self):
        """
        fills in right-justified parts of status bar, eg current
        frame/layer/tile labels (buttons positioned but drawn separately)
        """
        dark = self.ui.colors.black
        light = self.ui.colors.white
        art = self.ui.active_art
        padding = 2
        # position file button
        x = self.tile_width - (self.file_cycle_button.width + 1)
        self.file_cycle_button.x = x
        x -= padding
        # zoom
        self.art.write_string(0, 0, x, 0, self.zoom_label, dark, light, True)
        x -= len(self.zoom_label) + self.zoom_set_button.width
        self.zoom_set_button.x = x
        x -= padding
        # tile
        tile = 'X/Y'
        color = light
        if self.ui.app.cursor and art:
            tile_x, tile_y = self.ui.app.cursor.get_tile()
            tile_y = int(tile_y)
            # user-facing coordinates are always base 1
            tile_x += 1
            tile_y += 1
            if tile_x <= 0 or tile_x > art.width:
                color = self.dim_color
            if tile_y <= 0 or tile_y > art.height:
                color = self.dim_color
            tile_x = str(tile_x).rjust(3)
            tile_y = str(tile_y).rjust(3)
            tile = '%s,%s' % (tile_x, tile_y)
        self.art.write_string(0, 0, x, 0, tile, color, dark, True)
        # tile label
        x -= len(tile)
        self.art.write_string(0, 0, x, 0, self.tile_label, dark, light, True)
        # position layer button
        x -= (padding + len(self.tile_label) + self.layer_cycle_button.width)
        self.layer_cycle_button.x = x
        # layer label
        self.art.write_string(0, 0, x, 0, self.layer_label, dark, light, True)
        # position frame button
        x -= (padding + len(self.layer_label) + self.frame_cycle_button.width)
        self.frame_cycle_button.x = x
        # frame label
        self.art.write_string(0, 0, x, 0, self.frame_label, dark, light, True)
    
    def render(self):
        if not self.ui.active_art:
            return
        UIElement.render(self)
        # draw wireframe red X /behind/ char if BG transparent
        if self.ui.selected_bg_color == 0:
            self.x_renderable.x = self.char_renderable.x
            self.x_renderable.y = self.char_renderable.y
            self.x_renderable.render()
        self.char_renderable.render()
        self.fg_renderable.render()
        self.bg_renderable.render()
        # draw red X for transparent FG or BG
        if self.ui.selected_fg_color == 0:
            self.x_renderable.x = self.fg_renderable.x
            self.x_renderable.y = self.fg_renderable.y
            self.x_renderable.render()
        if self.ui.selected_bg_color == 0:
            self.x_renderable.x = self.bg_renderable.x
            self.x_renderable.y = self.bg_renderable.y
            self.x_renderable.render()
        # dim out items if brush is set to not affect them
        self.dim_renderable.y = self.char_renderable.y
        swatch_width = self.art.quad_width * StatusBarCycleButton.width
        if not self.ui.selected_tool.affects_char:
            self.dim_renderable.x = self.char_renderable.x - swatch_width
            self.dim_renderable.render()
        if not self.ui.selected_tool.affects_fg_color:
            self.dim_renderable.x = self.fg_renderable.x - swatch_width
            self.dim_renderable.render()
        if not self.ui.selected_tool.affects_bg_color:
            self.dim_renderable.x = self.bg_renderable.x - swatch_width
            self.dim_renderable.render()
        if not self.ui.selected_tool.affects_xform:
            # separate dimmer renderable for xform's wider size
            self.dim_xform_renderable.y = self.char_renderable.y
            self.dim_xform_renderable.x = XformToggleButton.x * self.art.quad_width - 1
            self.dim_xform_renderable.render()
