
from art_import import ArtImporter

class EDSCIIImporter(ArtImporter):
    format_name = 'EDSCII'
    format_description = """
Binary format for EDSCII, Playscii's predecessor.
Assumes single frame, single layer document.
Default character set and palette will be used.
    """
    def run_import(self, in_filename):
        data = open(in_filename, 'rb').read()
        # document width = find longest stretch before a \n
        longest_line = 0
        for line in data.splitlines():
            if len(line) > longest_line:
                longest_line = len(line)
        # TODO: support width_override in new importer system
        #width = width_override or int(longest_line / 3)
        width = int(longest_line / 3)
        # derive height from width
        # 2-byte line breaks might produce non-int result, cast erases this
        height = int(len(data) / width / 3)
        self.art.resize(width, height)
        # populate char/color arrays by scanning width-long chunks of file
        def chunks(l, n):
            for i in range(0, len(l), n):
                yield l[i:i+n]
        # 3 bytes per tile, +1 for line ending
        # BUT: files saved in windows may have 2 byte line breaks, try to detect
        lb_length = 1
        lines = chunks(data, (width * 3) + lb_length)
        for line in lines:
            if line[-2] == ord('\r') and line[-1] == ord('\n'):
                #self.app.log('EDSCIIImporter: windows-style line breaks detected')
                lb_length = 2
                break
        # recreate generator after first use
        lines = chunks(data, (width * 3) + lb_length)
        x, y = 0, 0
        for line in lines:
            index = 0
            while index < len(line) - lb_length:
                char = line[index]
                # +1 to color indices; playscii color index 0 = transparent
                fg = line[index+1] + 1
                bg = line[index+2] + 1
                self.art.set_tile_at(0, 0, x, y, char, fg, bg)
                index += 3
                x += 1
                if x >= width:
                    x = 0
                    y += 1
        return True
