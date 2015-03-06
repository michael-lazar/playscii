
import os.path
import numpy as np

from PIL import Image

from renderable_sprite import ImagePreviewRenderable

def convert_image(app, image_filename):
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
    w = int(w * ratio)
    h = int(h * ratio)
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
    # create sprite renderable for preview while conversion happens
    preview = ImagePreviewRenderable(app, None, src_img)
    preview.y = -art.height * art.quad_height
    preview.scale_x = w / char_w
    preview.scale_y = h / char_h
    app.convert_renderable = preview
    # clear active layer so we can see preview
    art.clear_frame_layer(app.ui.active_frame, app.ui.active_layer, 0)
    src_array = np.fromstring(src_img.tostring(), dtype=np.uint8)
    return
    src_array = np.reshape(src_array, (w, h, 3))
    chars = np.fromstring(art.charset.image_data.tostring(), dtype=np.uint8)
    chars = np.reshape(chars, (art.charset.image_width, art.charset_image_height, 3))
    for y in range(art.height):
        for x in range(art.width):
            src_block = src_array[x:x+char_w, y:y+char_h]
            char_index = 0
            best_char = 0
            best_diff = 9999999999999
            for char_y in range(art.charset.map_height):
                for char_x in range(art.charset.map_width):
                    char_block = chars[char_x:char_x+char_w, char_y:char_y+char_h]
                    block_diff = (char_block - src_block).sum()
                    if block_diff < best_diff:
                        best_char = char_index
                    char_index += 1
            art.set_char_index_at(app.ui.active_frame, app.ui.active_layer, x, y, best_char)
