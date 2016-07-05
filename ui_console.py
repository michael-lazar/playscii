import os
import sdl2
from math import ceil

from ui_element import UIElement
from art import UV_FLIPY
from key_shifts import shift_map

from image_convert import ImageConverter
from palette import PaletteFromFile

from image_export import export_still_image, export_animation

from renderable_sprite import ImagePreviewRenderable
from PIL import Image


CONSOLE_HISTORY_FILENAME = 'console_history'

class ConsoleCommand:
    "parent class for console commands"
    description = '[Enter a description for this command!]'
    def execute(console, args):
        return 'Test command executed.'


class QuitCommand(ConsoleCommand):
    description = 'Quit Playscii.'
    def execute(console, args):
        console.ui.app.should_quit = True


class SaveCommand(ConsoleCommand):
    description = 'Save active art, under new filename if given.'
    def execute(console, args):
        # save currently active file
        art = console.ui.active_art
        # set new filename if given
        if len(args) > 0:
            old_filename = art.filename
            art.set_filename(' '.join(args))
            art.save_to_file()
            console.ui.app.load_art_for_edit(old_filename)
            console.ui.set_active_art_by_filename(art.filename)
        else:
            art.save_to_file()
        console.ui.app.update_window_title()


class OpenCommand(ConsoleCommand):
    description = 'Open art with given filename.'
    def execute(console, args):
        if len(args) == 0:
            return 'Usage: open [art filename]'
        filename = ' '.join(args)
        console.ui.app.load_art_for_edit(filename)

class RevertArtCommand(ConsoleCommand):
    description = 'Revert active art to last saved version.'
    def execute(console, args):
        console.ui.app.revert_active_art()

class LoadPaletteCommand(ConsoleCommand):
    description = 'Set the given color palette as active.'
    def execute(console, args):
        if len(args) == 0:
            return 'Usage: pal [palette filename]'
        filename = ' '.join(args)
        # load AND set
        palette = console.ui.app.load_palette(filename)
        console.ui.active_art.set_palette(palette)
        console.ui.popup.set_active_palette(palette)

class LoadCharSetCommand(ConsoleCommand):
    description = 'Set the given character set as active.'
    def execute(console, args):
        if len(args) == 0:
            return 'Usage: char [character set filename]'
        filename = ' '.join(args)
        charset = console.ui.app.load_charset(filename)
        console.ui.active_art.set_charset(charset)
        console.ui.popup.set_active_charset(charset)

class ImageExportCommand(ConsoleCommand):
    description = 'Export active art as PNG image.'
    def execute(console, args):
        export_still_image(console.ui.app, console.ui.active_art)

class AnimExportCommand(ConsoleCommand):
    description = 'Export active art as animated GIF image.'
    def execute(console, args):
        export_animation(console.ui.app, console.ui.active_art)

class ConvertImageCommand(ConsoleCommand):
    description = 'Convert given bitmap image to current character set + color palette.'
    def execute(console, args):
        if len(args) == 0:
            return 'Usage: conv [image filename]'
        image_filename = ' '.join(args)
        ImageConverter(console.ui.app, image_filename, console.ui.active_art)
        console.ui.app.update_window_title()

class ShowImageCommand(ConsoleCommand):
    description = 'Show given bitmap image on screen. (DEBUG ONLY)'
    def execute(console, args):
        if len(args) == 0:
            return 'Usage: img [image filename]'
        image_filename = ' '.join(args)
        img = Image.open(image_filename).convert('RGB')
        w, h = img.size
        r = ImagePreviewRenderable(console.ui.app, None, img)
        console.ui.app.img_renderables.append(r)
        r.scale_x, r.scale_y = w / 8, h / 8

class ImportCommand(ConsoleCommand):
    description = 'Import file using an ArtImport class'
    def execute(console, args):
        if len(args) < 2:
            return 'Usage: imp [ArtImporter class name] [filename]'
        importers = console.ui.app.get_importers()
        importer_classname, filename = args[0], args[1]
        importer_class = None
        for c in importers:
            if c.__name__ == importer_classname:
                importer_class = c
        if not importer_class:
            console.ui.app.log("Couldn't find importer class %s" % importer_classname)
        if not os.path.exists(filename):
            console.ui.app.log("Couldn't find file %s" % filename)
        importer = importer_class(console.ui.app, filename)

class ExportCommand(ConsoleCommand):
    description = 'Export current art using an ArtExport class'
    def execute(console, args):
        if len(args) < 2:
            return 'Usage: exp [ArtExporter class name] [filename]'
        exporters = console.ui.app.get_exporters()
        exporter_classname, filename = args[0], args[1]
        exporter_class = None
        for c in exporters:
            if c.__name__ == exporter_classname:
                exporter_class = c
        if not exporter_class:
            console.ui.app.log("Couldn't find exporter class %s" % exporter_classname)
        exporter = exporter_class(console.ui.app, filename)

class PaletteFromImageCommand(ConsoleCommand):
    description = 'Convert given image into a palette file.'
    def execute(console, args):
        if len(args) == 0:
            return 'Usage: getpal [image filename]'
        src_filename = ' '.join(args)
        new_pal = PaletteFromFile(console.ui.app, src_filename, src_filename)
        if not new_pal.init_success:
            return
        #console.ui.app.load_palette(new_pal.filename)
        console.ui.app.palettes.append(new_pal)
        console.ui.active_art.set_palette(new_pal)
        console.ui.popup.set_active_palette(new_pal)

class SetGameDirCommand(ConsoleCommand):
    description = 'Load game from the given folder.'
    def execute(console, args):
        if len(args) == 0:
            return 'Usage: setgame [game dir name]'
        game_dir_name = ' '.join(args)
        console.ui.app.gw.set_game_dir(game_dir_name, True)

class LoadGameStateCommand(ConsoleCommand):
    description = 'Load the given game state save file.'
    def execute(console, args):
        if len(args) == 0:
            return 'Usage: game [game state filename]'
        gs_name = ' '.join(args)
        console.ui.app.gw.load_game_state(gs_name)

class SaveGameStateCommand(ConsoleCommand):
    description = 'Save the current game state as the given filename.'
    def execute(console, args):
        "Usage: savegame [game state filename]"
        gs_name = ' '.join(args)
        console.ui.app.gw.save_to_file(gs_name)

class SpawnObjectCommand(ConsoleCommand):
    description = 'Spawn an object of the given class name.'
    def execute(console, args):
        if len(args) == 0:
            return 'Usage: spawn [class name]'
        class_name = ' '.join(args)
        console.ui.app.gw.spawn_object_of_class(class_name)

class CommandListCommand(ConsoleCommand):
    description = 'Show the list of console commands.'
    def execute(console, args):
        # TODO: print a command with usage if available
        console.ui.app.log('Commands:')
        # alphabetize command list
        command_list = list(commands.keys())
        command_list.sort()
        for command in command_list:
            desc = commands[command].description
            console.ui.app.log(' %s - %s' % (command, desc))

class RunArtScriptCommand(ConsoleCommand):
    description = 'Run art script with given filename on active art.'
    def execute(console, args):
        if len(args) == 0:
            return 'Usage: src [art script filename]'
        filename = ' '.join(args)
        console.ui.active_art.run_script(filename)

class RunEveryArtScriptCommand(ConsoleCommand):
    description = 'Run art script with given filename on active art at given rate.'
    def execute(console, args):
        if len(args) < 2:
            return 'Usage: srcev [rate] [art script filename]'
        rate = float(args[0])
        filename = ' '.join(args[1:])
        console.ui.active_art.run_script_every(filename, rate)
        # hide so user can immediately see what script is doing
        console.hide()

class StopArtScriptsCommand(ConsoleCommand):
    description = 'Stop all actively running art scripts.'
    def execute(console, args):
        console.ui.active_art.stop_all_scripts()

# map strings to command classes for ConsoleUI.parse
commands = {
    'exit': QuitCommand,
    'quit': QuitCommand,
    'save': SaveCommand,
    'open': OpenCommand,
    'char': LoadCharSetCommand,
    'pal': LoadPaletteCommand,
    'imgexp': ImageExportCommand,
    'animexport': AnimExportCommand,
    'conv': ConvertImageCommand,
    'getpal': PaletteFromImageCommand,
    'setgame': SetGameDirCommand,
    'game': LoadGameStateCommand,
    'savegame': SaveGameStateCommand,
    'spawn': SpawnObjectCommand,
    'help': CommandListCommand,
    'scr': RunArtScriptCommand,
    'screv': RunEveryArtScriptCommand,
    'scrstop': StopArtScriptsCommand,
    'revert': RevertArtCommand,
    'img': ShowImageCommand,
    'imp': ImportCommand,
    'exp': ExportCommand
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
    all_modes_visible = True
    
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
        self.history_filename = self.ui.app.config_dir + CONSOLE_HISTORY_FILENAME
        if os.path.exists(self.history_filename):
            self.history_file = open(self.history_filename, 'r')
            try:
                self.command_history = self.history_file.readlines()
            except:
                self.command_history = []
            self.history_file = open(self.history_filename, 'a')
        else:
            self.history_file = open(self.history_filename, 'w+')
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
        self.current_line = self.command_history[self.history_index].strip()
    
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
            # if command is same as last, don't repeat it
            if len(self.command_history) > 0 and self.current_line != self.command_history[-1]:
                self.command_history.append(self.current_line)
                self.history_file.write(self.current_line + '\n')
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
            keystr = shift_map.get(keystr, '')
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
                player = app.gw.player
                sel = None if len(app.gw.selected_objects) == 0 else app.gw.selected_objects[0]
                world = app.gw
                hud = app.gw.hud
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
    
    def destroy(self):
        self.history_file.close()


# delimiters - alt-backspace deletes to most recent one of these
delimiters = [' ', '.', ')', ']', ',', '_']
