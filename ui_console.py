import sdl2
from math import ceil

from ui_element import UIElement
from art import UV_FLIPY
from key_shifts import shift_map

from image_convert import convert_image


class ConsoleCommand:
    "parent class for console commands"
    def execute(console, args):
        return 'Test command executed.'


class QuitCommand(ConsoleCommand):
    def execute(console, args):
        console.ui.app.should_quit = True


class SaveCommand(ConsoleCommand):
    def execute(console, args):
        # save currently active file
        art = console.ui.active_art
        # set new filename if given
        if len(args) > 0:
            art.set_filename(' '.join(args))
        art.save_to_file()
        console.ui.app.update_window_title()


class OpenCommand(ConsoleCommand):
    def execute(console, args):
        filename = ' '.join(args)
        console.ui.app.load_art_for_edit(filename)


class LoadPaletteCommand(ConsoleCommand):
    def execute(console, args):
        filename = ' '.join(args)
        # load AND set
        palette = console.ui.app.load_palette(filename)
        console.ui.active_art.set_palette(palette)
        console.ui.popup.set_active_palette(palette)


class LoadCharSetCommand(ConsoleCommand):
    def execute(console, args):
        filename = ' '.join(args)
        charset = console.ui.app.load_charset(filename)
        console.ui.active_art.set_charset(charset)
        console.ui.popup.set_active_charset(charset)


class ImageExportCommand(ConsoleCommand):
    def execute(console, args):
        console.ui.app.export_image(console.ui.active_art)


class ConvertImageCommand(ConsoleCommand):
    def execute(console, args):
        image_filename = ' '.join(args)
        convert_image(console.ui.app, image_filename)


# map strings to command classes for ConsoleUI.parse
commands = {
    'exit': QuitCommand,
    'quit': QuitCommand,
    'save': SaveCommand,
    'open': OpenCommand,
    'char': LoadCharSetCommand,
    'pal': LoadPaletteCommand,
    'export': ImageExportCommand,
    'conv': ConvertImageCommand
}


class ConsoleUI(UIElement):
    
    visible = False
    snap_top = True
    snap_left = True
    # how far down the screen the console reaches when visible
    height_screen_pct = 0.75
    # how long (seconds) to shift/fade into view when invoked
    show_anim_time = 0.75
    bg_alpha = 0.75
    prompt = '>'
    # _ ish char
    bottom_line_char_index = 76
    right_margin = 3
    # transient, but must be set here b/c UIElement.init calls reset_art
    current_line = ''
    game_mode_visible = True
    
    def __init__(self, ui):
        self.bg_color_index = ui.colors.darkgrey
        self.highlight_color = 8 # yellow
        UIElement.__init__(self, ui)
        # state stuff for console move/fade
        self.alpha = 0
        self.target_alpha = 0
        self.target_y = 2
        # start off top of screen
        self.renderable.y = self.y = 2
        # user input and log
        self.last_lines = []
        self.command_history = []
        self.history_index = 0
        # junk data in last user line so it changes on first update
        self.last_user_line = 'test'
        # max line length = width of console minus prompt + _
        self.max_line_length = int(self.art.width) - self.right_margin
    
    def reset_art(self):
        self.width = ceil(self.ui.width_tiles * self.ui.scale)
        # % of screen must take aspect into account
        inv_aspect = self.ui.app.window_height / self.ui.app.window_width
        self.height = int(self.ui.height_tiles * self.height_screen_pct * inv_aspect * self.ui.scale)
        # dim background
        self.renderable.bg_alpha = self.bg_alpha
        # must resize here, as window width will vary
        self.art.resize(self.width, self.height)
        self.max_line_length = int(self.width) - self.right_margin
        self.text_color = self.ui.palette.lightest_index
        self.clear()
        # truncate current user line if it's too long for new width
        self.current_line = self.current_line[:self.max_line_length]
        #self.update_user_line()
        # empty log lines so they refresh from app
        self.last_user_line = 'XXtestXX'
        self.last_lines = []
    
    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()
    
    def show(self):
        self.visible = True
        self.target_alpha = 1
        self.target_y = 1
        self.ui.menu_bar.visible = False
        self.ui.pulldown.visible = False
    
    def hide(self):
        self.target_alpha = 0
        self.target_y = 2
        self.ui.menu_bar.visible = True
    
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
        for x in range(self.width):
            self.art.set_tile_at(0, 0, x, -1, self.bottom_line_char_index, self.text_color, None, UV_FLIPY)
    
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
        # draw underscore for caret at end of input string
        x = len(self.prompt) + len(self.current_line) + 1
        i = self.ui.charset.get_char_index('_')
        self.art.set_char_index_at(0, 0, x, -2, i)
    
    def update_log_lines(self):
        "update art from log lines"
        log_index = -1
        for y in range(self.height - 3, -1, -1):
            try:
                line = self.ui.app.log_lines[log_index]
            except IndexError:
                break
            # trim line to width of console
            if len(line) >= self.max_line_length:
                line = line[:self.max_line_length]
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
        # remember log & user lines, bail early next update if no change
        self.last_lines = self.ui.app.log_lines[:]
        self.last_user_line = self.current_line
        if not user_input_changed and not log_changed:
            return
        # if log lines changed, clear all tiles to shift in new text
        if log_changed:
            self.clear()
            self.update_log_lines()
        # update user line independently of log, it changes at a different rate
        if user_input_changed:
            self.update_user_line()
    
    def visit_command_history(self, index):
        if len(self.command_history) == 0:
            return
        self.history_index = index
        self.history_index %= len(self.command_history)
        self.current_line = self.command_history[self.history_index]
    
    def handle_input(self, key, shift_pressed, alt_pressed, ctrl_pressed):
        "handles a key from Application.input"
        keystr = sdl2.SDL_GetKeyName(key).decode()
        # TODO: get console bound key from InputLord, detect that instead of
        # hard-coded backquote
        if keystr == '`':
            self.toggle()
            return
        elif keystr == 'Return':
            line = '%s %s' % (self.prompt, self.current_line)
            self.ui.app.log(line)
            self.command_history.append(self.current_line)
            self.parse(self.current_line)
            self.current_line = ''
            self.history_index = 0
        elif keystr == 'Tab':
            # TODO: autocomplete (commands, filenames)
            pass
        elif keystr == 'Up':
            # page back through command history
            self.visit_command_history(self.history_index - 1)
        elif keystr == 'Down':
            # page forward through command history
            self.visit_command_history(self.history_index + 1)
        elif keystr == 'Backspace' and len(self.current_line) > 0:
            # alt-backspace: delete to last delimiter, eg periods
            if alt_pressed:
                # "index to delete to"
                delete_index = -1
                for delimiter in delimiters:
                    this_delimiter_index = self.current_line.rfind(delimiter)
                    if this_delimiter_index > delete_index:
                        delete_index = this_delimiter_index
                if delete_index > -1:
                    self.current_line = self.current_line[:delete_index]
                else:
                    self.current_line = ''
                    # user is bailing on whatever they were typing,
                    # reset position in cmd history
                    self.history_index = 0
            else:
                self.current_line = self.current_line[:-1]
                if len(self.current_line) == 0:
                    # same as above: reset position in cmd history
                    self.history_index = 0
        elif keystr == 'Space':
            keystr = ' '
        # ignore any other non-character keys
        if len(keystr) > 1:
            return
        if keystr.isalpha() and not shift_pressed:
            keystr = keystr.lower()
        elif not keystr.isalpha() and shift_pressed:
            keystr = shift_map[keystr]
        if len(self.current_line) < self.max_line_length:
            self.current_line += keystr
    
    def parse(self, line):
        # is line in a list of know commands? if so, handle it.
        items = line.split()
        output = None
        if len(items) == 0:
            pass
        elif items[0] in commands:
            cmd = commands[items[0]]
            output = cmd.execute(self, items[1:])
        else:
            # if not, try python eval, give useful error if it fails
            try:
                # set some locals for easy access from eval
                ui = self.ui
                app = ui.app
                camera = app.camera
                art = ui.active_art
                # special handling of assignment statements, eg x = 3:
                # detect strings that pattern-match, send them to exec(),
                # send all other strings to eval()
                eq_index = line.find('=')
                is_assignment = eq_index != -1 and line[eq_index+1] != '='
                if is_assignment:
                    exec(line)
                else:
                    output = str(eval(line))
            except Exception as e:
                # try to output useful error text
                output = '%s: %s' % (e.__class__.__name__, str(e))
        # commands CAN return None, so only log if there's something
        if output and output != 'None':
            self.ui.app.log(output)


# delimiters - alt-backspace deletes to most recent one of these
delimiters = [' ', '.', ')', ']', ',', '_']
