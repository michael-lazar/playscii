
from art_import import ArtImporter

class TextImporter(ArtImporter):
    
    format_name = 'Plain text'
    format_description = """
ASCII art in ordinary text format.
Assumes single frame, single layer document.
Current character set and palette will be used.
    """
    
    def run_import(self, in_filename, options={}):
        lines = open(in_filename).readlines()
        # determine length of longest line
        longest = 0
        for line in lines:
            if len(line) > longest:
                longest = len(line)
        if len(lines) == 0 or longest == 0:
            return False
        self.art.resize(longest, len(lines))
        x, y = 0, 0
        for line in lines:
            for char in line:
                char_index = self.art.charset.char_mapping.get(char, None)
                if char_index:
                    self.art.set_char_index_at(0, 0, x, y, char_index)
                x += 1
            x = 0
            y += 1
        return True
