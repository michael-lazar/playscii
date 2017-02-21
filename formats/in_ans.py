
from art_import import ArtImporter

DEFAULT_FG, DEFAULT_BG = 7, 0
WIDTH = 80
MAX_LINES = 250

class ANSImporter(ArtImporter):
    format_name = 'ANSI'
    format_description = """
Classic scene format using ANSI standard codes.
Assumes 80 columns, DOS character set and EGA palette.
    """
    allowed_file_extensions = ['ans', 'txt']
    
    def get_sequence(self, data):
        "returns a list of ints from given data ending in a letter"
        i = 0
        seq = []
        while not 64 <= data[i] <= 126:
            seq.append(data[i])
            i += 1
        seq.append(data[i])
        return seq
    
    def get_commands_from_sequence(self, seq):
        "returns command type & commands (separated by semicolon) from sequence"
        cmds = []
        new_cmd = ''
        for k in seq[:-1]:
            if k != 59:
                new_cmd += chr(k)
            else:
                cmds.append(new_cmd)
                new_cmd = ''
        # include last command
        cmds.append(new_cmd)
        return chr(seq[-1]), cmds
    
    def run_import(self, in_filename, options={}):
        self.set_art_charset('dos')
        self.set_art_palette('ansi')
        # resize to arbitrary height, crop once we know final line count
        self.resize(WIDTH, MAX_LINES)
        self.art.clear_frame_layer(0, 0, DEFAULT_BG + 1)
        data = open(in_filename, 'rb').read()
        x, y = 0, 0
        # cursor save/restore codes position
        saved_x, saved_y = 0, 0
        # final value of y might be lower than last line touched if
        # cursor up/reset codes used; track highest value
        max_y = 0
        fg, bg = DEFAULT_FG, DEFAULT_BG
        i = 0
        fg_bright, bg_bright = False, False
        while i < len(data):
            if x >= WIDTH:
                x = 0
                y += 1
                if y > max_y: max_y = y
            # how much we will advance through bytes for next iteration
            increment = 1
            # command sequence
            if data[i] == 27 and data[i+1] == 91:
                increment += 1
                # grab full length of sequence
                seq = self.get_sequence(data[i+2:])
                # split sequence into individual commands
                cmd_type, cmds = self.get_commands_from_sequence(seq)
                # display control
                if cmd_type == 'm':
                    # empty command = reset
                    if len(cmds) == 0:
                        fg, bg = DEFAULT_FG, DEFAULT_BG
                        fg_bright, bg_bright = False, False
                    else:
                        for cmd in cmds:
                            code = int(cmd)
                            # reset colors
                            if code == 0:
                                fg, bg = DEFAULT_FG, DEFAULT_BG
                                fg_bright, bg_bright = False, False
                            # "bright" colors
                            elif code == 1:
                                # bump fg color if isn't already bright
                                if not fg_bright:
                                    fg += 8
                                fg_bright = True
                            elif code == 5:
                                if not bg_bright:
                                    bg += 8
                                bg_bright = True
                            # swap fg/bg
                            elif code == 7:
                                fg, bg = bg, fg
                            # change fg color
                            elif 30 <= code <= 37:
                                fg = code - 30
                                if fg_bright: fg += 8
                            # change bg color
                            elif 40 <= code <= 47:
                                bg = code - 40
                                if bg_bright: bg += 8
                            #else: print('unhandled display code %s' % code)
                # cursor up/down/forward/back
                elif cmd_type == 'A':
                    y -= int(cmds[0]) if cmds[0] else 1
                elif cmd_type == 'B':
                    y += int(cmds[0]) if cmds[0] else 1
                    if y > max_y: max_y = y
                elif cmd_type == 'C':
                    x += int(cmds[0]) if cmds[0] else 1
                elif cmd_type == 'D':
                    x -= int(cmds[0]) if cmds[0] else 1
                # break
                elif ord(cmd_type) == 26:
                    break
                # set line wrap (ignore for now)
                elif cmd_type == 'h':
                    pass
                # move cursor to Y,X
                elif cmd_type == 'H' or cmd_type == 'f':
                    if len(cmds) == 0 or len(cmds[0]) == 0:
                        new_y = 0
                    else:
                        new_y = int(cmds[0]) - 1
                    if len(cmds) < 2 or len(cmds[1]) == 0:
                        new_x = 0
                    else:
                        new_x = int(cmds[1]) - 1
                    x, y = new_x, new_y
                    if y > max_y: max_y = y
                # clear line/screen
                elif cmd_type == 'J':
                    cmd = int(cmds[0]) if cmds else 0
                    # 0: clear from cursor to end of screen
                    if cmd == 0:
                        for xi in range(x, WIDTH):
                            self.art.set_char_index_at(0, 0, xi, y, 0)
                    # 1: clear from cursor to beginning of screen
                    elif cmd == 1:
                        for xi in range(x):
                            self.art.set_char_index_at(0, 0, xi, y, 0)
                    # 2: clear entire screen, move cursor to 0,0
                    elif cmd == 2:
                        x, y = 0, 0
                        self.art.clear_frame_layer(0, 0, DEFAULT_BG + 1)
                # save cursor position
                elif cmd_type == 's':
                    saved_x, saved_y = x, y
                # restore cursor position
                elif cmd_type == 'u':
                    x, y = saved_x, saved_y
                #else: print('unhandled escape code %s' % cmd_type)
                increment += len(seq)
            # CR + LF
            elif data[i] == 13 and data[i+1] == 10:
                increment += 1
                x = 0
                y += 1
                if y > max_y: max_y = y
            # LF
            elif data[i] == 10:
                x = 0
                y += 1
                if y > max_y: max_y = y
            # indent
            elif data[i] == 9:
                x += 8
            # regular character
            else:
                char = data[i]
                # account for color 0 (transparent)
                self.art.set_tile_at(0, 0, x, y, char, fg + 1, bg + 1)
                x += 1
            i += increment
        # resize to last line touched
        self.resize(WIDTH, max_y)
        # rare cases where no lines covered
        if self.art.height == 0:
            return False
        return True
