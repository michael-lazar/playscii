from art_export import ArtExporter

class TextExporter(ArtExporter):
    format_name = 'Plain text'
    format_description = """
ASCII art in ordinary text format.
Assumes single frame, single layer document.
Current character set will be used; make sure it supports
any extended characters you want translated.
    """
    file_extension = 'txt'
    def run_export(self, out_filename, options):
        # utf-8 is safest encoding to use here, but non-default on Windows
        outfile = open(out_filename, 'w', encoding='utf-8')
        for y in range(self.art.height):
            for x in range(self.art.width):
                char = self.art.get_char_index_at(0, 0, x, y)
                found_char = False
                for k,v in self.art.charset.char_mapping.items():
                    if v == char:
                        found_char = True
                        outfile.write(k)
                        break
                # if char not found, just write a blank space
                if not found_char:
                    outfile.write(' ')
            outfile.write('\n')
        outfile.close()
        return True
