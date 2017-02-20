
from art_import import ArtImporter

DEFAULT_FG, DEFAULT_BG = 7, 0
MAX_LINES = 250

class ANSImporter(ArtImporter):
    format_name = 'ANS'
    format_description = """
ANS format.
    """
    
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
        cmds.append(new_cmd)
        return seq[-1], cmds
    
    def run_import(self, in_filename, options={}):
        self.set_art_charset('dos')
        self.set_art_palette('ansi')
        # resize to arbitrary height, crop once we know final line count
        self.resize(80, MAX_LINES)
        self.art.clear_frame_layer(0, 0, DEFAULT_BG + 1)
        data = open(in_filename, 'rb').read()
        x, y = 0, 0
        saved_x, saved_y = 0, 0
        fg, bg = DEFAULT_FG, DEFAULT_BG
        i = 0
        fg_bright, bg_bright = False, False
        while i < len(data):
            if x >= 80:
                x = 0
                y += 1
            # how much we will advance through bytes for next iteration
            increment = 1
            # escape sequence
            if data[i] == 27 and data[i+1] == 91:
                increment += 1
                # grab full length of sequence
                seq = self.get_sequence(data[i+2:])
                # split sequence into individual commands
                cmd_type, cmds = self.get_commands_from_sequence(seq)
                #print('sequence found at %s:' % i)
                #print('  %s' % seq)
                #print('  %s: %s' % (cmd_type, cmds))
                # display control
                if chr(cmd_type) == 'm':
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
                                fg_bright = True
                            elif code == 5:
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
                elif chr(cmd_type) == 'A':
                    y -= int(cmds[0]) if cmds[0] else 1
                elif chr(cmd_type) == 'B':
                    y += int(cmds[0]) if cmds[0] else 1
                elif chr(cmd_type) == 'C':
                    spaces = int(cmds[0]) if cmds else 1
                    #print('%s spaces starting at %s,%s' % (spaces, x, y))
                    # paint bg while moving cursor?
                    # TODO: figure out why "Pablodraw v.3.0" bar doesn't show up
                    #for xi in range(spaces):
                    #    self.art.set_tile_at(0, 0, x + xi, y, 0, fg + 1, bg + 1)
                    x += spaces
                elif cmd_type == 68:
                    x -= int(cmds[0]) if cmds[0] else 1
                # break
                elif cmd_type == 26:
                    break
                # set line wrap (ignore for now)
                elif cmd_type == 104:
                    pass
                # move cursor to X,Y
                elif cmd_type == 72:
                    if len(cmds) == 2:
                        x, y = cmds[0], cmds[1]
                # save cursor position
                elif cmd_type == 115:
                    saved_x, saved_y = x, y
                # restore cursor position
                elif cmd_type == 117:
                    x, y = saved_x, saved_y
                #else: print('unhandled escape code %s' % cmd_type)
                increment += len(seq)
            # CR + LF
            elif data[i] == 13 and data[i+1] == 10:
                increment += 1
                x = 0
                y += 1
            # LF
            elif data[i] == 10:
                x = 0
                y += 1
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
        # TODO: current value of y might be lower than last line touched if
        # cursor up/reset codes used - see if this comes up in .ANS samples
        self.resize(80, y)
        return True
