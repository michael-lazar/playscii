import math, time
import numpy as np

from ui_element import UIElement, UIArt, UIRenderable
from renderable_line import LineRenderable, SwatchSelectionBoxRenderable, UIRenderableX

class UISwatch(UIElement):
    
    def __init__(self, ui, popup):
        self.ui = ui
        self.popup = popup
        self.reset()
    
    def reset(self):
        self.tile_width, self.tile_height = self.get_size()
        art = self.ui.active_art
        # generate a unique name for debug purposes
        art_name = '%s_%s' % (int(time.time()), self.__class__.__name__)
        self.art = UIArt(art_name, self.ui.app, art.charset, art.palette, self.tile_width, self.tile_height)
        # tear down existing renderables if any
        if not self.renderables:
            self.renderables = []
        else:
            for r in self.renderables:
                r.destroy()
            self.renderables = []
        self.renderable = UIRenderable(self.ui.app, self.art)
        self.renderable.ui = self.ui
        self.renderable.grain_strength = 0
        self.renderables.append(self.renderable)
        self.reset_art()
    
    def reset_art(self):
        pass
    
    def get_size(self):
        return 1, 1
    
    def set_cursor_loc_from_mouse(self, cursor, mouse_x, mouse_y):
        # get location within char map
        w, h = self.art.quad_width, self.art.quad_height
        tile_x = (mouse_x - self.x) / w
        tile_y = (mouse_y - self.y) / h
        self.set_cursor_loc(cursor, tile_x, tile_y)
    
    def set_cursor_loc(self, cursor, tile_x, tile_y):
        """
        common, generalized code for both character and palette swatches:
        set cursor's screen location, tile location, and quad size.
        """
        w, h = self.art.quad_width, self.art.quad_height
        # snap to tile
        tile_x = int(math.floor(tile_x / w) * w)
        tile_y = int(math.ceil(tile_y / h) * h)
        # back to screen coords
        x = tile_x * w + self.x
        y = (tile_y - 1) * h + self.y
        tile_index = (abs(tile_y) * self.art.width) + tile_x
        # if a valid character isn't hovered, bail
        if not self.is_selection_index_valid(tile_index):
            self.set_cursor_selection_index(-1)
            return
        # cool, set cursor location & size
        self.set_cursor_selection_index(tile_index)
        cursor.quad_size_ref = self.art
        cursor.tile_x, cursor.tile_y = tile_x, tile_y
        cursor.x, cursor.y = x, y
    
    def is_selection_index_valid(self, index):
        "returns True if given index is valid for choices this swatch offers"
        return False
    
    def set_cursor_selection_index(self, index):
        "another set_cursor_loc support method, overriden by subclasses"
        self.popup.blah = index
    
    def render(self):
        self.renderable.render()


class CharacterSetSwatch(UISwatch):
    
    # scale the character set will be drawn at
    char_scale = 2
    min_scale = 1
    max_scale = 5
    scale_increment = 0.25
    
    def increase_scale(self):
        if self.char_scale <= self.max_scale - self.scale_increment:
            self.char_scale += self.scale_increment
    
    def decrease_scale(self):
        if self.char_scale >= self.min_scale + self.scale_increment:
            self.char_scale -= self.scale_increment
    
    def reset(self):
        UISwatch.reset(self)
        self.selection_box = SwatchSelectionBoxRenderable(self.ui.app, self.art)
        self.grid = CharacterGridRenderable(self.ui.app, self.art)
        self.renderables += self.selection_box, self.grid
    
    def get_size(self):
        art = self.ui.active_art
        return art.charset.map_width, art.charset.map_height
    
    def reset_art(self):
        # MAYBE-TODO: using screen resolution, try to set quad size to an even
        # multiple of screen so the sampling doesn't get chunky
        aspect = self.ui.app.window_width / self.ui.app.window_height
        charset = self.art.charset
        self.art.quad_width = UIArt.quad_width * self.char_scale
        self.art.quad_height = self.art.quad_width * (charset.char_height / charset.char_width) * aspect
        # only need to populate characters on reset_art, but update
        # colors every update()
        self.art.clear_frame_layer(0, 0, 0)
        i = 0
        for y in range(charset.map_height):
            for x in range(charset.map_width):
                self.art.set_char_index_at(0, 0, x, y, i)
                i += 1
        self.art.geo_changed = True
    
    def reset_loc(self):
        self.x = self.popup.x + self.popup.swatch_margin
        self.y = self.popup.y
        self.y -= self.popup.art.quad_height * (self.popup.tab_height + 4)
        self.renderable.x, self.renderable.y = self.x, self.y
        self.grid.x, self.grid.y = self.x, self.y
        self.grid.y -= self.art.quad_height
    
    def set_xform(self, new_xform):
        for y in range(self.art.height):
            for x in range(self.art.width):
                self.art.set_char_transform_at(0, 0, x, y, new_xform)
    
    def is_selection_index_valid(self, index):
        return index < self.art.charset.last_index
    
    def set_cursor_selection_index(self, index):
        self.popup.cursor_char = index
        self.popup.cursor_color = -1
    
    def move_cursor(self, cursor, dx, dy):
        "moves cursor by specified amount in selection grid"
        # determine new cursor tile X/Y
        tile_x = cursor.tile_x + dx
        tile_y = cursor.tile_y + dy
        tile_index = (abs(tile_y) * self.art.width) + tile_x
        if tile_x < 0 or tile_x >= self.art.width:
            return
        elif tile_y > 0:
            return
        elif tile_y <= -self.art.height:
            # TODO: handle "jump" to palette swatch, and back
            #cursor.tile_y = 0
            #self.popup.palette_swatch.move_cursor(cursor, 0, 0)
            return
        elif tile_index >= self.art.charset.last_index:
            return
        self.set_cursor_loc(cursor, tile_x, tile_y)
    
    def update(self):
        charset = self.ui.active_art.charset
        fg, bg = self.ui.selected_fg_color, self.ui.selected_bg_color
        # repopulate colors every update
        for y in range(charset.map_height):
            for x in range(charset.map_width):
                self.art.set_tile_at(0, 0, x, y, None, fg, bg)
        self.art.update()
        # selection box color
        elapsed_time = self.ui.app.elapsed_time
        color = 0.75 + (math.sin(elapsed_time / 100) / 2)
        self.selection_box.color = (color, color) * 2
        # set cursor color here rather than doin sin(time) again in popup update
        self.popup.cursor_box.color = (color, color) * 2
        # position
        self.selection_box.x = self.renderable.x
        selection_x = self.ui.selected_char % charset.map_width
        self.selection_box.x += selection_x * self.art.quad_width
        self.selection_box.y = self.renderable.y
        selection_y = (self.ui.selected_char - selection_x) / charset.map_width
        self.selection_box.y -= (selection_y + 1) * self.art.quad_height
    
    def render(self):
        if not self.popup.visible:
            return
        UISwatch.render(self)
        self.grid.render()
        self.selection_box.render()


class PaletteSwatch(UISwatch):
    
    def reset(self):
        UISwatch.reset(self)
        self.transparent_x = UIRenderableX(self.ui.app, self.art)
        self.fg_selection_box = SwatchSelectionBoxRenderable(self.ui.app, self.art)
        self.bg_selection_box = SwatchSelectionBoxRenderable(self.ui.app, self.art)
        # F label for FG color selection
        self.f_art = ColorSelectionLabelArt(self.ui, 'F')
        # make character dark
        self.f_art.set_color_at(0, 0, 0, 0, self.f_art.palette.darkest_index, True)
        self.f_renderable = ColorSelectionLabelRenderable(self.ui.app, self.f_art)
        self.f_renderable.ui = self.ui
        # B label for BG color seletion
        self.b_art = ColorSelectionLabelArt(self.ui, 'B')
        self.b_renderable = ColorSelectionLabelRenderable(self.ui.app, self.b_art)
        self.b_renderable.ui = self.ui
        self.renderables += self.transparent_x, self.fg_selection_box, self.bg_selection_box, self.f_renderable, self.b_renderable
    
    def get_size(self):
        # balance rows/columns according to character set swatch width
        charmap_width = self.popup.charset_swatch.art.charset.map_width
        colors = len(self.popup.charset_swatch.art.palette.colors)
        rows = math.ceil(colors / charmap_width)
        columns = math.ceil(colors / rows)
        return columns, rows
    
    def reset_art(self):
        # base our quad size on charset's
        cqw, cqh = self.popup.charset_swatch.art.quad_width, self.popup.charset_swatch.art.quad_height
        # maximize item size based on row/column determined in get_size()
        self.art.quad_width = (self.art.charset.map_width / self.art.width) * cqw
        self.art.quad_height = (self.art.charset.map_width / self.art.width) * cqh
        self.art.clear_frame_layer(0, 0, 0)
        palette = self.ui.active_art.palette
        i = 0
        for y in range(self.tile_height):
            for x in range(self.tile_width):
                if i >= len(palette.colors):
                    break
                self.art.set_color_at(0, 0, x, y, i, False)
                i += 1
        self.art.geo_changed = True
    
    def reset_loc(self):
        self.x = self.popup.x + self.popup.swatch_margin
        self.y = self.popup.charset_swatch.renderable.y
        # adjust Y for charset
        self.y -= self.popup.charset_swatch.art.quad_height * self.ui.active_art.charset.map_height
        # adjust Y for palette caption and character scale
        self.y -= self.popup.art.quad_height * 2
        self.renderable.x, self.renderable.y = self.x, self.y
        # first color in palette (top left) always transparent
        self.transparent_x.x = self.renderable.x
        self.transparent_x.y = self.renderable.y - self.art.quad_height
        # set f/b_art's quad size
        self.f_art.quad_width, self.f_art.quad_height = self.b_art.quad_width, self.b_art.quad_height = self.popup.art.quad_width, self.popup.art.quad_height
        self.f_art.geo_changed = True
        self.b_art.geo_changed = True
    
    def is_selection_index_valid(self, index):
        return index < len(self.art.palette.colors)
    
    def set_cursor_selection_index(self, index):
        self.popup.cursor_color = index
        self.popup.cursor_char = -1
    
    def move_cursor(self, cursor, dx, dy):
        # similar enough to charset swatch's move_cursor, different enough to
        # merit this small bit of duplicate code
        pass
    
    def update(self):
        self.art.update()
        self.f_art.update()
        self.b_art.update()
        # color selection boxes
        elapsed_time = self.ui.app.elapsed_time
        color = 0.75 + (math.sin(elapsed_time / 100) / 2)
        self.fg_selection_box.color = (color, color) * 2
        self.bg_selection_box.color = (color, color) * 2
        # fg selection box position
        self.fg_selection_box.x = self.renderable.x
        self.fg_selection_box.x += self.art.quad_width * (self.ui.selected_fg_color % self.art.width)
        self.fg_selection_box.y = self.renderable.y
        self.fg_selection_box.y -= self.art.quad_height * math.ceil((self.ui.selected_fg_color + 1) / self.art.width)
        # bg box position
        self.bg_selection_box.x = self.renderable.x
        self.bg_selection_box.x += self.art.quad_width * (self.ui.selected_bg_color % self.art.width)
        self.bg_selection_box.y = self.renderable.y
        self.bg_selection_box.y -= self.art.quad_height * math.ceil((self.ui.selected_bg_color + 1) / self.art.width)
        # FG label position
        self.f_renderable.alpha = 1 - color
        self.f_renderable.x = self.fg_selection_box.x
        self.f_renderable.y = self.fg_selection_box.y + self.art.quad_height
        # center F in box
        x_offset = (self.art.quad_width - self.popup.art.quad_width) / 2
        y_offset = (self.art.quad_height - self.popup.art.quad_height) / 2
        self.f_renderable.x += x_offset
        self.f_renderable.y -= y_offset
        # BG label position
        self.b_renderable.alpha = 1 - color
        self.b_renderable.x = self.bg_selection_box.x
        self.b_renderable.y = self.bg_selection_box.y + self.art.quad_height
        self.b_renderable.x += x_offset
        self.b_renderable.y -= y_offset
    
    def render(self):
        if not self.popup.visible:
            return
        UISwatch.render(self)
        self.transparent_x.render()
        self.fg_selection_box.render()
        self.bg_selection_box.render()
        self.f_renderable.render()
        self.b_renderable.render()


class ColorSelectionLabelArt(UIArt):
    def __init__(self, ui, letter):
        letter_index = ui.charset.get_char_index(letter)
        art_name = '%s_%s' % (int(time.time()), self.__class__.__name__)
        UIArt.__init__(self, art_name, ui.app, ui.charset, ui.palette, 1, 1)
        label_color = ui.colors.white
        label_bg_color = 0
        self.set_tile_at(0, 0, 0, 0, letter_index, label_color, label_bg_color)


class ColorSelectionLabelRenderable(UIRenderable):
    # transparent background so we can see the swatch color behind it
    bg_alpha = 0


class CharacterGridRenderable(LineRenderable):
    
    color = (0.5, 0.5, 0.5, 0.25)
    
    def build_geo(self):
        w, h = self.quad_size_ref.width, self.quad_size_ref.height
        v = []
        e = []
        c = self.color * 4 * w * h
        index = 0
        for x in range(1, w):
            v += [(x, -h+1), (x, 1)]
            e += [index, index+1]
            index += 2
        for y in range(h-1):
            v += [(w, -y), (0, -y)]
            e += [index, index+1]
            index += 2
        self.vert_array = np.array(v, dtype=np.float32)
        self.elem_array = np.array(e, dtype=np.uint32)
        self.color_array = np.array(c, dtype=np.float32)
