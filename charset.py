import os.path, string, time
from PIL import Image

from texture import Texture

CHARSET_DIR = 'charsets/'
CHARSET_FILE_EXTENSION = 'char'


class CharacterSetLord:
    
    # time in ms between checks for hot reload
    hot_reload_check_interval = 2 * 1000
    
    def __init__(self, app):
        self.app = app
        self.last_check = 0
    
    def check_hot_reload(self):
        if self.app.get_elapsed_time() - self.last_check < self.hot_reload_check_interval:
            return
        self.last_check = self.app.get_elapsed_time()
        changed = None
        for charset in self.app.charsets:
            if charset.has_updated():
                changed = charset.filename
                # reload data and image even if only one changed
                try:
                    success = charset.load_char_data()
                    if success:
                        self.app.log('CharacterSetLord: success reloading %s' % charset.filename)
                    else:
                        self.app.log('CharacterSetLord: failed reloading %s' % charset.filename, True)
                except:
                    self.app.log('CharacterSetLord: failed reloading %s' % charset.filename, True)


class CharacterSet:
    
    transparent_color = (0, 0, 0)
    
    def __init__(self, app, src_filename, log):
        self.init_success = False
        self.app = app
        self.filename = self.app.find_filename_path(src_filename, CHARSET_DIR,
                                                    CHARSET_FILE_EXTENSION)
        if not self.filename:
            self.app.log("Couldn't find character set data %s" % self.filename)
            return
        self.name = os.path.basename(self.filename)
        self.name = os.path.splitext(self.name)[0]
        # image filename discovered by character data load process
        self.image_filename = None
        # remember last modified times for data and image files
        self.last_data_change = os.path.getmtime(self.filename)
        self.last_image_change = 0
        # do most stuff in load_char_data so we can hot reload
        if not self.load_char_data():
            return
        # report
        if log and not self.app.game_mode:
            self.app.log("loaded charmap '%s' from %s:" % (self.name, self.filename))
            self.report()
        self.init_success = True
    
    def load_char_data(self):
        "carries out majority of CharacterSet init, including loading image"
        char_data_src = open(self.filename, encoding='utf-8').readlines()
        # allow comments: discard any line in char data starting with //
        # (make sure this doesn't muck up legit mapping data)
        char_data = []
        for line in char_data_src:
            if not line.startswith('//'):
                char_data.append(line)
        # first line = image file
        # hold off assigning to self.image_filename til we know it's valid
        img_filename = self.app.find_filename_path(char_data.pop(0).strip(), CHARSET_DIR, 'png')
        if not img_filename:
            self.app.log("Couldn't find character set image %s" % self.image_filename)
            return False
        self.image_filename = img_filename
        # now that we know the image file's name, store its last modified time
        self.last_image_change = os.path.getmtime(self.image_filename)
        # second line = character set dimensions
        second_line = char_data.pop(0).strip().split(',')
        self.map_width, self.map_height = int(second_line[0]), int(second_line[1])
        self.char_mapping = {}
        index = 0
        for line in char_data:
            # strip newlines from mapping
            for char in line.strip('\r\n'):
                if not char in self.char_mapping:
                    self.char_mapping[char] = index
                index += 1
            if index >= self.map_width * self.map_height:
                break
        # if no lower case included, map upper to lower & vice versa
        has_upper, has_lower = False, False
        for line in char_data:
            for char in line:
                if char.isupper():
                    has_upper = True
                elif char.islower():
                    has_lower = True
        if has_upper and not has_lower:
            for char in string.ascii_lowercase:
                # set may not have all letters
                if not char.upper() in self.char_mapping:
                    continue
                self.char_mapping[char] = self.char_mapping[char.upper()]
        elif has_lower and not has_upper:
            for char in string.ascii_uppercase:
                if not char.lower() in self.char_mapping:
                    continue
                self.char_mapping[char] = self.char_mapping[char.lower()]
        # last valid index a character can be
        self.last_index = self.map_width * self.map_height
        # load image
        self.load_image_data()
        self.set_char_dimensions()
        # store base filename for easy comparisons with not-yet-loaded sets
        self.base_filename = os.path.splitext(os.path.basename(self.filename))[0]
        return True
    
    def load_image_data(self):
        # load and process image
        img = Image.open(self.image_filename)
        img = img.convert('RGBA')
        # flip for openGL
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        self.image_width, self.image_height = img.size
        # any pixel that is "transparent color" will be made fully transparent
        # any pixel that isn't will be opaque + tinted FG color
        for y in range(self.image_height):
            for x in range(self.image_width):
                # TODO: PIL pixel access shows up in profiler, use numpy array
                # assignment instead
                color = img.getpixel((x, y))
                if color[:3] == self.transparent_color[:3]:
                    # MAYBE-TODO: does keeping non-alpha color improve sampling?
                    img.putpixel((x, y), (color[0], color[1], color[2], 0))
        self.texture = Texture(img.tobytes(), self.image_width, self.image_height)
        # flip image data back and save it for later, eg image conversion
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        self.image_data = img
    
    def set_char_dimensions(self):
        # store character dimensions and UV size
        self.char_width = int(self.image_width / self.map_width)
        self.char_height = int(self.image_height / self.map_height)
        self.u_width = self.char_width / self.image_width
        self.v_height = self.char_height / self.image_height
    
    def report(self):
        self.app.log('  source texture %s is %s x %s pixels' % (self.image_filename, self.image_width, self.image_height))
        self.app.log('  char pixel width/height is %s x %s' % (self.char_width, self.char_height))
        self.app.log('  char map width/height is %s x %s' % (self.map_width, self.map_height))
        self.app.log('  last character index: %s' % self.last_index)
    
    def has_updated(self):
        "return True if source image file has changed since last check"
        # tolerate bad filenames in data, don't check stamps on nonexistent ones
        if not self.image_filename or not os.path.exists(self.filename) or \
           not os.path.exists(self.image_filename):
            return False
        data_changed = os.path.getmtime(self.filename) > self.last_data_change
        img_changed = os.path.getmtime(self.image_filename) > self.last_image_change
        if data_changed:
            self.last_data_change = time.time()
        if img_changed:
            self.last_image_change = time.time()
        return data_changed or img_changed
    
    def get_char_index(self, char):
        return self.char_mapping.get(char, 0)
    
    def get_solid_pixels_in_char(self, char_index):
        "Returns # of solid pixels in character at given index"
        tile_x = int(char_index % self.map_width)
        tile_y = int(char_index / self.map_width)
        x_start = self.char_width * tile_x
        x_end = x_start + self.char_width
        y_start = self.char_height * tile_y
        y_end = y_start + self.char_height
        pixels = 0
        for x in range(x_start, x_end):
            for y in range(y_start, y_end):
                color = self.image_data.getpixel((x, y))
                if color[3] > 0:
                    pixels += 1
        return pixels
