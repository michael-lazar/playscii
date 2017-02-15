
from art_import import ArtImporter

class EndDoomImporter(ArtImporter):
    format_name = 'ENDOOM'
    format_description = """
ENDOOM lump file format for Doom engine games.
80x25 DOS ASCII with EGA palette.
Background colors can only be EGA colors 0-8.
    """
    
    def run_import(self, in_filename, options={}):
        """
        from http://doomwiki.org/wiki/ENDOOM:
        80x25 tiles, dos charset, ega palette
        each tile is 2 bytes:
        first byte = ASCII (code page 437) char index
        second byte = color:
        bits 0-3 = fg color, bits 4-6 = bg color, bit 7 = blink
        """
        self.set_art_charset('dos')
        self.set_art_palette('ega')
        self.art.resize(80, 25)
        data = open(in_filename, 'rb').read(4000)
        x, y = 0, 0
        for i,byte in enumerate(data):
            if i % 2 != 0:
                continue
            color_byte = data[i+1]
            bits = bin(color_byte)[2:]
            bits = bits.rjust(7, '0')
            bg_bits = bits[:3]
            fg_bits = bits[3:]
            offset = 1
            fg = int(fg_bits, 2) + offset
            bg = int(bg_bits, 2) + offset
            self.art.set_tile_at(0, 0, x, y, byte, fg, bg)
            x += 1
            if x >= self.art.width:
                x = 0
                y += 1
        return True
