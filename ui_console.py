import sdl2
from math import ceil

from ui_element import UIElement


class ConsoleCommand:
    "parent class for console commands"
    def execute(console, args):
        return 'Test command executed.'


class QuitCommand(ConsoleCommand):
    def execute(console, args):
        console.ui.app.should_quit = True
        return 'exited!'


class SaveCommand(ConsoleCommand):
    def execute(console, args):
        # TODO: once MDI exists, save currently active file
        art = console.ui.app.art_loaded[0]
        if len(args) > 1:
            # TODO: create Art.set_filename to append extension, dir, etc
            art.filename = args[1]
        art.save_to_file()
        #return "saved file '%s'" % ' '.join(args)
        # don't return any text, save command does its own
        return


class OpenCommand(ConsoleCommand):
    def execute(console, args):
        filename = ' '.join(args)
        console.ui.app.load_art(filename)


# map strings to command classes for ConsoleUI.parse
commands = {
    'exit': QuitCommand,
    'quit': QuitCommand,
    'save': SaveCommand,
    'open': OpenCommand
}


class ConsoleUI(UIElement):
    
    visible = False
    snap_top = True
    snap_left = True
    # how far down the screen the console reaches when visible
    height_screen_pct = 0.75
    # how long (seconds) to shift/fade into view when invoked
    show_anim_time = 0.75
    bg_alpha = 0.5
    bg_color_index = 7 # dark grey
    highlight_color = 6 # yellow
    prompt = '>'
    
    def __init__(self, ui):
        UIElement.__init__(self, ui)
        # state stuff for console move/fade
        self.alpha = 0
        self.target_alpha = 0
        self.target_y = 2
        # start off top of screen
        self.renderable.y = self.y = 2
        self.last_lines = []
        # junk data in last user line so it changes on first update
        self.last_user_line = 'test'
    
    def reset_art(self):
        self.width = ceil(self.ui.width_tiles)
        # % of screen must take aspect into account
        inv_aspect = self.ui.app.window_height / self.ui.app.window_width
        self.height = int(self.ui.height_tiles * self.height_screen_pct * inv_aspect)
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
        # empty log lines so they refresh from app
        self.log_lines = []
        self.art.geo_changed = True
    
    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()
    
    def show(self):
        self.visible = True
        self.target_alpha = 1
        self.target_y = 1
    
    def hide(self):
        self.target_alpha = 0
        self.target_y = 2
    
    def update_loc(self):
        # TODO: this lerp is super awful, simpler way based on dt?
        # TODO: use self.show_anim_time instead of this garbage!
        speed = 0.25
        
        if self.y > self.target_y:
            self.y -= speed
        elif self.y < self.target_y:
            self.y += speed
        if abs(self.y - self.target_y) < speed:
            self.y = self.target_y
        
        if self.alpha > self.target_alpha:
            self.alpha -= speed / 2
        elif self.alpha < self.target_alpha:
            self.alpha += speed / 2
        if abs(self.alpha - self.target_alpha) < speed:
            self.alpha = self.target_alpha
        if self.alpha == 0:
            self.visible = False
        
        self.renderable.y = self.y
        self.renderable.alpha = self.alpha
    
    def clear(self):
        self.art.clear_frame_layer(0, 0, self.bg_color_index)
        # line -1 is always a line of ____________
        text = '_' * self.width
        self.art.write_string(0, 0, 0, -1, text, self.text_color)
    
    def update_user_line(self):
        "draw current user input on second to last line, with >_ prompt"
        # clear entire user line first
        self.art.write_string(0, 0, 0, -2, ' ' * self.width, self.text_color)
        self.art.write_string(0, 0, 0, -2, '%s ' % self.prompt, self.text_color)
        # if first item of line is a valid command, change its color
        items = self.current_line.split()
        if len(items) > 0 and items[0] in commands:
            self.art.write_string(0, 0, 2, -2, items[0], self.highlight_color)
            offset = 2 + len(items[0]) + 1
            args = ' '.join(items[1:])
            self.art.write_string(0, 0, offset, -2, args, self.text_color)
        else:
            self.art.write_string(0, 0, 2, -2, self.current_line, self.text_color)
        # draw underscore for cursor at end of input string
        x = len(self.prompt) + len(self.current_line) + 1
        i = self.ui.charset.get_char_index('_')
        self.art.set_char_index_at(0, 0, x, -2, i)
    
    def update_log_lines(self):
        "update art from log lines"
        log_index = -1
        # max line length = width of console minus prompt + _
        max_line_length = int(self.art.width) - 3
        for y in range(self.height - 3, -1, -1):
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
    
    def update(self):
        "update our Art with the current console log lines + user input"
        self.update_loc()
        if not self.visible:
            return
        # check for various early out scenarios, updating all chars every frame
        # gets expensive
        user_input_changed = self.last_user_line != self.current_line
        log_changed = self.last_lines != self.ui.app.log_lines
        if not user_input_changed and not log_changed:
            return
        # if log lines changed, clear all tiles to shift in new text
        if log_changed:
            self.clear()
            self.update_log_lines()
        # update user line independently of log, it changes at a different rate
        if user_input_changed:
            self.update_user_line()
        # remember current log and user lines, bail early next update if no change
        self.last_lines = self.ui.app.log_lines[:]
        self.last_user_line = self.current_line
    
    def handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        "handles a key from Application.input"
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
        # is line in a list of know commands? if so, handle it.
        items = line.split()
        if items[0] in commands:
            cmd = commands[items[0]]
            output = cmd.execute(self, items[1:])
        else:
            # if not, try python eval, give useful error if it fails
            try:
                output = str(eval(line))
            except:
                # TODO: actually useful error text from interpreter
                output = 'error'
        # commands CAN return None, so only log if there's something
        if output:
            self.ui.app.log(output)


# TODO: this probably breaks for non-US english KB layouts, find a better way!
shifts = {
    '1': '!', '2': '@', '3': '#', '4': '$', '5': '%', '6': '^', '7': '&', '8': '*',
    '9': '(', '0': ')', '-': '_', '=': '+', '`': '~', '[': '{', ']': '}', '\\': '|',
    ';': ':', "'": '"', ',': '<', '.': '>', '/': '?'
}
