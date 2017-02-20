
from art_import import ArtImporter

DEFAULT_FG, DEFAULT_BG = 7, 0
MAX_LINES = 200

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
        new_cmd = []
        for k in seq[:-1]:
            if k != 59:
                new_cmd.append(k)
            else:
                cmds.append(new_cmd[:])
                new_cmd = []
        return seq[-1], cmds
    
    def run_import(self, in_filename, options={}):
        self.set_art_charset('dos')
        self.set_art_palette('ansi')
        # resize to arbitrary height, crop once we know final line count
        self.resize(80, MAX_LINES)
        data = open(in_filename, 'rb').read()
        x, y = 0, 0
        fg, bg = DEFAULT_FG, DEFAULT_BG
        i = 0
        while i < len(data):
            if x == 80:
                x = 0
                y += 1
            # how much we will advance through bytes for next iteration
            increment = 1
            # escape sequence
            if data[i] == 27 and data[i+1] == 91:
                increment += 2
                # grab full length of sequence
                seq = self.get_sequence(data[i+2:])
                # split sequence into individual commands
                cmd_type, cmds = self.get_commands_from_sequence(seq)
                # display control
                if cmd_type == 109:
                    # empty command = reset
                    if len(cmds) == 0:
                        fg, bg = DEFAULT_FG, DEFAULT_BG
                    else:
                        for cmd in cmds:
                            code = ''
                            for byte in cmd:
                                code += chr(byte)
                            code = int(code)
                            if code == 0:
                                fg, bg = DEFAULT_FG, DEFAULT_BG
                            elif code == 1:
                                fg += 8
                                fg %= 16
                            elif code == 7:
                                fg, bg = bg, fg
                            elif 30 <= code <= 37:
                                fg = code - 30
                            elif 40 <= code <= 47:
                                bg = code - 40
                # cursor up/down/forward/back
                elif cmd_type == 65:
                    y -= cmds[0] if len(cmds) > 0 else 1
                elif cmd_type == 66:
                    y += cmds[0] if len(cmds) > 0 else 1
                elif cmd_type == 67:
                    x += cmds[0] if len(cmds) > 0 else 1
                elif cmd_type == 68:
                    x -= cmds[0] if len(cmds) > 0 else 1
                # break
                elif cmd_type == 26:
                    break
                increment += len(seq) - 1
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
        # TODO: current value of y might be lower than last line touched
        self.resize(80, y)
        return True
