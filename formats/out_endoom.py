
from art_export import ArtExporter

WIDTH, HEIGHT = 80, 25

class EndDoomExporter(ArtExporter):
    format_name = 'ENDOOM'
    format_description = """
ENDOOM lump file format for Doom engine games.
80x25 DOS ASCII with EGA palette.
Background colors can only be EGA colors 0-8.
    """
    def run_export(self, out_filename, options):
        if self.art.width < WIDTH or self.art.height < HEIGHT:
            self.app.log("ENDOOM export: Art isn't big enough!")
            return False
        outfile = open(out_filename, 'wb')
        for y in range(HEIGHT):
            for x in range(WIDTH):
                char, fg, bg, xform = self.art.get_tile_at(0, 0, x, y)
                # decrement color for EGA, index 0 is transparent in playscii
                fg -= 1
                bg -= 1
                # colors can't be negative
                fg = max(0, fg)
                bg = max(0, bg)
                char_byte = bytes([char])
                outfile.write(char_byte)
                fg_bits = bin(fg)[2:].rjust(4, '0')
                # BG color can't be above 8
                bg %= 8
                bg_bits = bin(bg)[2:].rjust(3, '0')
                color_bits = '0' + bg_bits + fg_bits
                color_byte = int(color_bits, 2)
                color_byte = bytes([color_byte])
                outfile.write(color_byte)
        outfile.close()
        return True
