
import math, os.path
import numpy as np

from PIL import Image

from renderable_sprite import ImagePreviewRenderable


"""
general questions:
- only try char blocks with two most common colors in source block? wouldn't give best result if two most common colors are similar and eg 3rd color is a bright accent

two strategies

PIL/Pillow-centric:
- source and char blocks are crops of their larger images: Image.crop(box=None), returns Image, box is tuple (left, upper, right, lower)
- use Image.getcolors to get list of unique colors in source block
- how to generate uniquely colored char blocks?  does it make sense to keep source and chars in palettized mode for easy char block color replacement?  see if ImageChops.difference works on two palettized images (ie it actually compares their colors not just their indices)
- PIL.ImageChops.difference(image1, image2), returns Image
- get aggregate brightness of difference via PIL.ImageStat.Stat(image_or_list, mask=None) where mask is sum
- char block with lowest sum == least difference
docs: http://pillow.readthedocs.org


numpy-centric:
- convert images to numpy arrays with fromstring(image.tostring())
- reshape arrays with shape (width, height, 3)
- use 2D slicing eg array[x_start:x_end, y_start:y_end] to get blocks
- how to get "most used colors" in source block with numpy? possible method: http://stackoverflow.com/questions/12297016/how-to-find-most-frequent-values-in-numpy-ndarray
http://stackoverflow.com/questions/19666626/replace-all-elements-of-python-numpy-array-that-are-greater-than-some-value#19666680
- how to do fast color replacements on char blocks?
-- make main char image 1-bit, use boolean indexing eg a[a == 0] = x
docs: http://docs.scipy.org/doc/numpy/reference/arrays.ndarray.html


"""

def convert_image(app, image_filename=None):
    # TEST
    image_filename = image_filename or 'bird.jpg'
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
    src_img = src_img.convert('RGB')
    # create sprite renderable for preview while conversion happens
    preview = ImagePreviewRenderable(app, None, src_img)
    preview.y = -art.height * art.quad_height
    preview.scale_x = w / char_w
    preview.scale_y = h / char_h
    preview.z = art.layers_z[app.ui.active_layer] - 0.01
    app.convert_renderable = preview
    # clear active layer so we can see preview
    art.clear_frame_layer(app.ui.active_frame, app.ui.active_layer, 0)
    # 
    src_array = np.fromstring(src_img.tostring(), dtype=np.uint8)
    src_array = np.reshape(src_array, (w, h, 3))
    #
    char_img = art.charset.image_data.copy()
    char_img = char_img.convert('RGB')
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
                        print('end of charset?')
                        break
                    block_diff = (char_block - src_block).sum()
                    if block_diff < best_diff:
                        best_char = char_index
                        best_diff = block_diff
                    char_index += 1
                    if char_index == art.charset.last_index:
                        print('end of charset?')
                        break
            #print('best character found: %s' % best_char)
            art.set_tile_at(app.ui.active_frame, app.ui.active_layer, x, y, best_char, 2, 0)
