import sdl2
from math import ceil
from art import Art
from renderable import Renderable

class UIElement:
    
    # size, in tiles
    width, height = 1, 1
    snap_top, snap_bottom, snap_left, snap_right = False, False, False, False
    x, y = 0, 0
    visible = True
    
    def __init__(self, ui):
        self.ui = ui
        self.art = UIArt(None, self.ui.app, self.ui.charset, self.ui.palette, self.width, self.height)
        self.renderable = UIRenderable(self.ui.app, self.art)
        self.renderable.ui = self.ui
        self.init_art()
        self.reset_loc()
    
    def init_art(self):
        "runs as init is finishing"
        pass
    
    def reset_loc(self):
        inv_aspect = self.ui.app.window_width / self.ui.app.window_height
        if self.snap_top:
            self.y = 1
        elif self.snap_bottom:
            self.y = self.art.quad_height * self.height - 1
        if self.snap_left:
            self.x = -inv_aspect
        elif self.snap_right:
            self.x = inv_aspect - (self.art.quad_width * self.width)
        self.renderable.x, self.renderable.y = self.x, self.y
    
    def update(self):
        "runs every frame"
        pass


class UIArt(Art):
    recalc_quad_height = False
    log_creation = False


class UIRenderable(Renderable):
    
    grain_strength = 0.2
    
    def get_projection_matrix(self):
        return self.ui.projection_matrix
    
    def get_view_matrix(self):
        return self.ui.view_matrix


class StatusBarUI(UIElement):
    
    snap_bottom = True
    snap_left = True
    
    def init_art(self):
        self.width = ceil(self.ui.width_tiles)
        # must resize here, as window width will vary
        self.art.resize(self.width, self.height)
        bg = self.ui.palette.lightest_index
        self.art.clear_frame_layer(0, 0, bg)
        text = 'test status bar text...'
        color = self.ui.palette.darkest_index
        self.art.write_string(0, 0, 1, 0, text, color)
        self.art.geo_changed = True
    
    def update(self):
        pass


class FPSCounterUI(UIElement):
    
    width, height = 10, 2
    snap_top = True
    snap_right = True
    
    def update(self):
        bg = 0
        self.art.clear_frame_layer(0, 0, bg)
        color = self.ui.palette.lightest_index
        # yellow or red if framerate dips
        if self.ui.app.fps < 30:
            color = 6
        if self.ui.app.fps < 10:
            color = 2
        text = '%.1f fps' % self.ui.app.fps
        x = self.width - len(text)
        self.art.write_string(0, 0, x, 0, text, color)
        text = '%.1f ms ' % self.ui.app.frame_time
        x = self.width - len(text)
        self.art.write_string(0, 0, x, 1, text, color)


class ConsoleUI(UIElement):
    
    visible = False
    height_screen_pct = 0.5
    snap_top = True
    snap_left = True
    bg_alpha = 0.5
    bg_color_index = 7
    prompt = '>'
    
    def init_art(self):
        self.width = ceil(self.ui.width_tiles)
        self.height = int(self.ui.height_tiles * self.height_screen_pct)
        # dim background
        self.renderable.bg_alpha = self.bg_alpha
        # must resize here, as window width will vary
        self.art.resize(self.width, self.height)
        self.text_color = self.ui.palette.lightest_index
        self.clear()
        self.current_line = ''
        self.art.write_string(0, 0, 1, -2, self.prompt, self.text_color)
        text = 'test console text'
        self.art.write_string(0, 0, 1, -3, text, self.text_color)
        self.art.geo_changed = True
    
    def clear(self):
        self.art.clear_frame_layer(0, 0, self.bg_color_index)
        # line -1 is always a line of ____________
        text = '_' * self.width
        self.art.write_string(0, 0, 0, -1, text, self.text_color)
    
    def update(self):
        self.clear()
        # draw current user input on line -2
        line = '%s %s_' % (self.prompt, self.current_line)
        self.art.write_string(0, 0, 0, -2, line, self.text_color)
        # update art from log lines
        log_index = -1
        # max line length = width of console minus prompt + _
        max_line_length = self.ui.width_tiles - 3
        for y in range(self.height - 3, 0, -1):
            try:
                line = self.ui.app.log_lines[log_index]
            except IndexError:
                break
            # trim to width of console
            # TODO: this doesn't seem to work, fix char screen size issues first
            if len(line) > max_line_length:
                line = line[:max_line_length]
            self.art.write_string(0, 0, 1, y, line, self.text_color)
            log_index -= 1
        # TODO: save out current log lines, bail early next update if no change
    
    def handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        keystr = sdl2.SDL_GetKeyName(key).decode()
        if keystr == 'Return':
            # TODO: parse!
            line = '%s %s' % (self.prompt, self.current_line)
            self.ui.app.log(line)
            self.parse(self.current_line)
            # TODO: add to command history
            self.current_line = ''
        elif keystr == 'Tab':
            # TODO: autocomplete
            pass
        elif keystr == 'Up':
            # TODO: command history
            pass
        elif keystr == 'Backspace' and len(self.current_line) > 0:
            # alt-backspace: delete to start of line
            # TODO: delete to last delimiter, eg periods
            if alt_pressed:
                self.current_line = ''
            else:
                self.current_line = self.current_line[:-1]
        elif keystr == 'Space':
            keystr = ' '
        # ignore any other non-character keys
        if len(keystr) > 1:
            return
        if keystr.isalpha() and not shift_pressed:
            keystr = keystr.lower()
        elif not keystr.isalpha() and shift_pressed:
            keystr = shifts[keystr]
        self.current_line += keystr
    
    def parse(self, line):
        # TODO: compare line against a list of known commands, if it matches one
        # have that command handle it. if not, try to eval n give useful error if fail
        try:
            output = str(eval(line))
        except:
            # TODO: more useful error text from interpreter
            output = 'error'
        self.ui.app.log(output)


# TODO: this probably breaks for non-US english KB layouts, find a better way!
shifts = {
    '1': '!', '2': '@', '3': '#', '4': '$', '5': '%', '6': '^', '7': '&', '8': '*',
    '9': '(', '0': ')', '-': '_', '=': '+', '`': '~', '[': '{', ']': '}', '\\': '|',
    ';': ':', "'": '"', ',': '<', '.': '>', '/': '?'
}
