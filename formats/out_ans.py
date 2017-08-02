 
from art_export import ArtExporter

WIDTH = 80
ENCODING = 'cp1252' # old default
ENCODING = 'us-ascii' # DEBUG
ENCODING = 'latin_1' # DEBUG - seems to handle >128 chars ok?

class ANSExporter(ArtExporter):
    format_name = 'ANSI'
    format_description = """
Classic scene format using ANSI standard codes.
Assumes 80 columns, DOS character set and EGA palette.
Exports active layer of active frame.
    """
    file_extension = 'ans'
    
    def get_display_command(self, fg, bg):
        "return a display command sequence string for given colors"
        # reset colors on every tile
        s = chr(27) + chr(91) + '0;'
        if fg >= 8:
            s += '1;'
            fg -= 8
        if bg >= 8:
            s += '5;'
            bg -= 8
        s += '%s;' % (fg + 30)
        s += '%s' % (bg + 40)
        s += 'm'
        return s
    
    def write(self, data):
        self.outfile.write(data.encode(ENCODING))
    
    def run_export(self, out_filename, options):
        # binary file; encoding into ANSI bytes happens just before write
        self.outfile = open(out_filename, 'wb')
        layer = self.art.active_layer
        frame = self.art.active_frame
        for y in range(self.art.height):
            for x in range(WIDTH):
                # cut off tiles beyond supported width
                if x >= self.art.width - 1:
                    continue
                char, fg, bg, xform = self.art.get_tile_at(frame, layer, x, y)
                # offset palette indices so 0 = black not transparent
                fg -= 1
                bg -= 1
                # write a display command every tile
                # works fine, though it's a larger file - any real downside to this?
                self.write(self.get_display_command(fg, bg))
                # write the character for this tile
                if char > 31:
                    self.write(chr(char))
                else:
                    # special (top row) chars won't display in terminal anyway
                    self.write(chr(0))
            # carriage return + line feed
            self.outfile.write(b'\r\n')
        self.outfile.close()
        return True
