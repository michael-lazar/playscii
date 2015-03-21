
import math, os.path, time
import numpy as np

from PIL import Image, ImageChops, ImageStat

from renderable_sprite import ImagePreviewRenderable
from lab_color import rgb_to_lab, lab_color_diff

class ImageConverter:
    
    tiles_per_tick = 1
    
    def __init__(self, app, image_filename, art):
        image_filename = image_filename or 'bird.jpg' ### TEST ###
        if not os.path.exists(image_filename):
            app.log("Couldn't find image file %s" % image_filename)
            return
        self.app = app
        self.app.converter = self
        self.image_filename = image_filename
        self.art = art
        self.src_img = Image.open(self.image_filename).convert('RGB')
        self.start_time = time.time()
        # preserve aspect
        self.char_w, self.char_h = art.charset.char_width, art.charset.char_height
        art_pixel_w, art_pixel_h = self.char_w * art.width, self.char_h * art.height
        w, h = self.src_img.size
        #print('source image is %s x %s' % (w, h))
        ratio = min(art_pixel_h / h, art_pixel_w / w)
        w = math.floor((w * ratio) / self.char_w) * self.char_w
        h = math.floor((h * ratio) / self.char_h) * self.char_h
        #print('target image is %s x %s' % (w, h))
        self.src_img = self.src_img.resize((w, h), resample=Image.NEAREST)
        # convert source image to art's palette
        pal_img = Image.new("P", (1, 1))
        # Image.putpalette needs a flat tuple :/
        colors = []
        # while we're iterating through palette, build table of color diffs
        unique_colors = len(self.art.palette.colors)
        self.color_diffs = np.zeros((unique_colors, unique_colors), dtype=np.uint32)
        for i,color in enumerate(self.art.palette.colors):
            # skip alpha
            for channel in color[:-1]:
                colors.append(channel)
            for j,other_color in enumerate(self.art.palette.colors):
                #self.color_diffs[i][j] = self.get_rgb_color_diff(color, other_color)
                # L*a*b color space conversion for greater accuracy
                self.color_diffs[i][j] = self.get_lab_color_diff(color, other_color)
        # PIL will fill out <256 color palettes with bogus values :/
        while len(colors) < 256 * 3:
            for i in range(3):
                colors.append(0)
        pal_img.putpalette(tuple(colors))
        self.src_img = self.src_img.quantize(palette=pal_img)
        # convert palettized source image to an array for fast comparisons
        self.src_array = np.fromstring(self.src_img.tostring(), dtype=np.uint8)
        src_w, src_h = self.src_img.size
        self.src_array = np.reshape(self.src_array, (src_h, src_w))
        # convert charmap to 1-bit color for fast value swaps during
        # block comparison
        self.char_img = self.art.charset.image_data.copy().convert('RGB')
        self.char_img = self.char_img.transpose(Image.FLIP_TOP_BOTTOM)
        bw_pal_img = Image.new("P", (1, 1))
        bw_pal = [0, 0, 0, 255, 255, 255]
        while len(bw_pal) < 256 * 3:
            bw_pal.append(0)
        bw_pal_img.putpalette(tuple(bw_pal))
        self.char_img = self.char_img.quantize(palette=bw_pal_img)
        self.char_array = np.fromstring(self.char_img.tostring(), dtype=np.uint8)
        self.char_array = np.reshape(self.char_array, (self.art.charset.image_height, self.art.charset.image_width))
        # create, size and position image preview
        self.preview_sprite = ImagePreviewRenderable(self.app, None, self.src_img.convert('RGB'))
        self.preview_sprite.y = -self.art.height * self.art.quad_height
        self.preview_sprite.scale_x = w / self.char_w
        self.preview_sprite.scale_y = h / self.char_h
        self.preview_sprite.z = self.art.layers_z[app.ui.active_layer] - 0.01
        # clear active layer so we can see preview
        self.art.clear_frame_layer(self.app.ui.active_frame, self.app.ui.active_layer, 0)
        # block indices
        self.x, self.y = 0, 0
    
    def get_rgb_color_diff(self, color1, color2):
        r = abs(color1[0] - color2[0])
        g = abs(color1[1] - color2[1])
        b = abs(color1[2] - color2[2])
        a = abs(color1[3] - color2[3])
        return abs(r + g + b + a)
    
    def get_lab_color_diff(self, color1, color2):
        l1, a1, b1 = rgb_to_lab(*color1[:3])
        l2, a2, b2 = rgb_to_lab(*color2[:3])
        return lab_color_diff(l1, a1, b1, l2, a2, b2)
    
    def update(self):
        for i in range(self.tiles_per_tick):
            x_start, y_start = self.x * self.char_w, self.y * self.char_h
            x_end, y_end = x_start + self.char_w, y_start + self.char_h
            block = self.src_array[y_start:y_end, x_start:x_end]
            char, fg, bg = self.get_best_tile_for_block(block)
            self.art.set_tile_at(self.app.ui.active_frame, self.app.ui.active_layer,
                                 self.x, self.y, char, fg, bg)
            #print('set block %s,%s to ch %s fg %s bg %s' % (self.x, self.y, char, fg, bg))
            ### TEST: bail after first item
            #self.finished()
            #break
            self.x += 1
            if self.x >= self.art.width:
                self.x = 0
                self.y += 1
                if self.y >= self.art.height:
                    self.finished()
                    break
    
    def get_best_tile_for_block(self, src_block):
        # get unique colors in source block
        colors, counts = np.unique(src_block, False, False, return_counts=True)
        if len(colors) == 1:
            return (0, 0, colors[0])
        # sort by most to least used colors
        color_counts = []
        for i,color in enumerate(colors):
            color_counts += [(color, counts[i])]
        color_counts.sort(key=lambda item: item[1], reverse=True)
        # build list of unique fg/bg color (index) tuple-pairs
        combos = []
        for color1,count1 in color_counts:
            for color2,count2 in color_counts:
                if color1 == color2:
                    continue
                # fg/bg color swap SHOULD be allowed
                if (color1, color2) in combos:
                    continue
                combos.append((color1, color2))
        #print(combos)
        # compare all combos + chars w/ source block
        char_index = 0
        best_char = 0
        best_diff = 9999999999999
        best_fg, best_bg = 0, 0
        for bg,fg in combos:
            #print('trying fg/bg %s/%s for block:' % (fg, bg))
            #self.print_block(src_block, fg, bg)
            #print('=======================')
            char_array = self.char_array.copy()
            char_array[char_array == 0] = bg
            char_array[char_array == 1] = fg
            for char_y in range(self.art.charset.map_height):
                for char_x in range(self.art.charset.map_width):
                    x0, y0 = char_x * self.char_w, char_y * self.char_h
                    x1, y1 = x0 + self.char_w, y0 + self.char_h
                    char_block = char_array[y0:y1, x0:x1]
                    diff = self.get_block_diff(src_block, char_block)
                    if diff < best_diff:
                        best_diff = diff
                        best_char = char_index
                        best_fg, best_bg = fg, bg
                        #print('%s is new best char index, diff %s:' % (char_index, diff))
                        #self.print_block(char_block, fg, bg)
                    char_index += 1
        # return best (least different to source block) char/fg/bg found
        return (best_char, best_fg, best_bg)
    
    def print_block(self, block, fg, bg):
        w, h = block.shape
        s = ''
        for y in range(h):
            for x in range(w):
                if block[y][x] == fg:
                    s += '#'
                else:
                    s += '.'
            s += '\n'
        print(s)
    
    def get_block_diff(self, block1, block2):
        diff = 0
        diff_array = np.zeros((self.char_h, self.char_w), dtype=np.uint32)
        # TODO: build a numpy array of difference values, sum() it
        for y in range(self.char_h):
            for x in range(self.char_w):
                color1 = block1[y][x]
                color2 = block2[y][x]
                diff_array[y][x] = self.color_diffs[color1][color2]
                #diff += self.color_diffs[color1][color2]
        #return diff
        return diff_array.sum()
    
    def finished(self):
        time_taken = time.time() - self.start_time
        self.app.log('Conversion of image %s finished in %.3f seconds' % (self.image_filename, time_taken))
        self.app.converter = None
        self.preview_sprite = None


"""

ImageConverter: created from given image, current art (+charset/palette); creates and destroys (when finished) preview SpriteRenderable, processes N blocks per tick until image is fully converted
init: create preview SpriteRenderable, ?break source image into blocks?, do any conversins necessary
tick: process N blocks, write to art
done: destroy preview


weird idea:
- precompute difference between every color by palette index (list of dicts? 2D numpy array?)
- keep source and char images palettized, use color indices to look up precomputed difference, sum up differences per char block

for xy in src_block:
    char_color_index = fg if char_block[xy] == 1 else bg
    diffs[xy] = diff_table[src_index, char_color_index]
diff = diffs.sum


general questions:
- only try char blocks with two most common colors in source block? wouldn't give best result if two most common colors are similar and eg 3rd color is a bright accent

search: "block in large image most similar to small image"


two strategies

PIL/Pillow-centric:
- source and char blocks are crops of their larger images: Image.crop(box=None), returns Image, box is tuple (left, upper, right, lower)
- use Image.getcolors to get list of unique colors in source block
? how to generate uniquely colored char blocks?  does it make sense to keep source and chars in palettized mode for easy char block color replacement?  see if ImageChops.difference works on two palettized images (ie it actually compares their colors not just their indices)
- PIL.ImageChops.difference(image1, image2), returns Image
- get aggregate brightness of difference via PIL.ImageStat.Stat(image_or_list, mask=None) where mask is sum
- char block with lowest sum == least difference
docs: http://pillow.readthedocs.org

numpy-centric:
- convert images to numpy arrays with fromstring(image.tostring())
- reshape arrays with shape (width, height, 3)
- use 2D slicing eg array[x_start:x_end, y_start:y_end] to get blocks
? how to get "most used colors" in source block with numpy? possible method: http://stackoverflow.com/questions/12297016/how-to-find-most-frequent-values-in-numpy-ndarray
http://stackoverflow.com/questions/19666626/replace-all-elements-of-python-numpy-array-that-are-greater-than-some-value#19666680
? how to do fast color replacements on char blocks?
-- make main char image 1-bit, use boolean indexing eg a[a == 0] = x
docs: http://docs.scipy.org/doc/numpy/reference/arrays.ndarray.html
"""

def convert_blocks_pil(art, src_img, char_img):
    char_w, char_h = art.charset.char_width, art.charset.char_height
    src_pal = src_img.getpalette()
    #pal = src_img.getpalette()
    # dither charmap to 1-bit color (black and white)
    char_pal = [0, 0, 0, 255, 255, 255]
    char_pal_img = Image.new("P", (1, 1))
    char_pal_img.putpalette(tuple(char_pal))
    char_img = char_img.quantize(palette=char_pal_img)
    #char_img = char_img.transpose(Image.FLIP_TOP_BOTTOM)
    #src_img = src_img.transpose(Image.FLIP_TOP_BOTTOM)
    for y in range(art.height):
        for x in range(art.width):
            left = x * char_w
            upper = y * char_h
            box = (left, upper, left + char_w, upper + char_h)
            src_block = src_img.crop(box)
            block_colors = src_block.getcolors()
            block_colors.sort(key=lambda item: item[0], reverse=True)
            bg = src_pal[block_colors[0][1]]
            # if only 1 color in block, write a blank tile of that color
            if len(block_colors) <= 1:
                art.set_tile_at(art.app.ui.active_frame, art.app.ui.active_layer, x, y, 0, 0, bg)
                continue
            fg = src_pal[block_colors[1][1]]
            #print('fg %s, bg %s' % (fg, bg))
            char_index = 0
            best_char = 0
            best_fg, best_bg = 0, 0
            best_diff = 9999999999999
            #src_block_rgb = src_block.convert('RGB')
            def block_diff(color1, color2, char_block):
                char_block.copy().putpalette((color1, color2))
                #char_block_rgb = char_block.convert('RGB')
                # compare RGB as indexed color difference is only difference in indices?
                #diff_img = ImageChops.difference(src_block_rgb, char_block_rgb)
                diff_img = ImageChops.difference(src_block, char_block)
                return ImageStat.Stat(diff_img).sum[0]
            for char_y in range(art.charset.map_height):
                for char_x in range(art.charset.map_width):
                    char_left = char_x * char_w
                    char_upper = char_y * char_h
                    box = (char_left, char_upper, char_left + char_w, char_upper + char_h)
                    char_block = char_img.crop(box)
                    diff1 = block_diff(bg, fg, char_block)
                    diff2 = block_diff(fg, bg, char_block)
                    if diff1 < best_diff:
                        best_char = char_index
                        best_diff = diff1
                        best_fg = bg
                        best_bg = fg
                    if diff2 < best_diff:
                        best_char = char_index
                        best_diff = diff2
                        best_fg = fg
                        best_bg = bg
                    char_index += 1
            art.set_tile_at(art.app.ui.active_frame, art.app.ui.active_layer, x, y, best_char, best_fg, best_bg)
            print('set tile %s,%s to ch %s fg %s bg %s' % (x, y, best_char, best_fg, best_bg))

def convert_blocks_np(art, src_img, char_img):
    src_img = src_img.convert('RGB')
    w, h = src_img.size
    char_w, char_h = art.charset.char_width, art.charset.char_height
    src_array = np.fromstring(src_img.tostring(), dtype=np.uint8)
    src_array = np.reshape(src_array, (w, h, 3))
    chars = np.fromstring(char_img.tostring(), dtype=np.uint8)
    chars = np.reshape(chars, (art.charset.image_width, art.charset.image_height, 3))
    for y in range(art.height):
        for x in range(art.width):
            src_x_start, src_y_start = x * char_w, y * char_h
            src_x_end, src_y_end = src_x_start + char_w, src_y_start + char_h
            src_block = src_array[src_x_start:src_x_end, src_y_start:src_y_end]
            # TODO: find 1st and 2nd most common colors, make those BG/FG?
            #colors, counts = np.unique(src_block, False, False, return_counts=True)
            char_index = 0
            best_char = 0
            best_diff = 9999999999999
            for char_y in range(art.charset.map_height):
                #print('char_y: %s' % char_y)
                for char_x in range(art.charset.map_width):
                    #print('char_x: %s' % char_x)
                    char_x_start, char_y_start = char_x * char_w, char_y * char_h
                    char_x_end, char_y_end = char_x_start + char_w, char_y_start + char_h
                    char_block = chars[char_x_start:char_x_end, char_y_start:char_y_end]
                    if char_block.shape != src_block.shape:
                        #print('end of charset?')
                        break
                    block_diff = (char_block - src_block).sum()
                    if block_diff < best_diff:
                        best_char = char_index
                        best_diff = block_diff
                    char_index += 1
                    if char_index == art.charset.last_index:
                        #print('end of charset?')
                        break
            #print('best character found: %s' % best_char)
            art.set_tile_at(art.app.ui.active_frame, art.app.ui.active_layer, x, y, best_char, 2, 0)


def convert_image(app, image_filename=None):
    image_filename = image_filename or 'bird.jpg' ### TEST ###
    if not os.path.exists(image_filename):
        app.log("Couldn't find image file %s" % image_filename)
        return
    art = app.ui.active_art
    # read source image, resize it for current art
    src_img = Image.open(image_filename)
    src_img = src_img.convert('RGB')
    char_w, char_h = art.charset.char_width, art.charset.char_height
    # preserve aspect
    art_pixel_w, art_pixel_h = char_w * art.width, char_h * art.height
    w, h = src_img.size
    print('source image is %s x %s' % (w, h))
    ratio = min(art_pixel_h / h, art_pixel_w / w)
    w = math.floor((w * ratio) / char_w) * char_w
    h = math.floor((h * ratio) / char_h) * char_h
    print('target image is %s x %s' % (w, h))
    src_img = src_img.resize((w, h), resample=Image.NEAREST)
    # create palette to dither source image to
    pal_img = Image.new("P", (1, 1))
    # Image.putpalette needs a flat tuple :/
    colors = []
    for color in art.palette.colors:
        r,g,b,a = color[0], color[1], color[2], color[3]
        colors.append(r)
        colors.append(g)
        colors.append(b)
        #colors.append(a)
    pal_img.putpalette(tuple(colors))
    src_img = src_img.quantize(palette=pal_img)
    #src_img = src_img.convert('RGB')
    # create sprite renderable for preview while conversion happens
    preview = ImagePreviewRenderable(app, None, src_img)
    preview.y = -art.height * art.quad_height
    preview.scale_x = w / char_w
    preview.scale_y = h / char_h
    preview.z = art.layers_z[app.ui.active_layer] - 0.01
    app.convert_renderable = preview
    # clear active layer so we can see preview
    art.clear_frame_layer(app.ui.active_frame, app.ui.active_layer, 0)
    char_img = art.charset.image_data.copy()
    char_img = char_img.convert('RGB')
    # 
    convert_blocks_np(art, src_img, char_img)
    #convert_blocks_pil(art, src_img, char_img)
