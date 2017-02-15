import os
from OpenGL import GL
from PIL import Image, ImageChops, GifImagePlugin

from framebuffer import ExportFramebuffer, ExportFramebufferNoCRT

def get_frame_image(app, art, frame, allow_crt=True, scale=1, bg_color=(0, 0, 0, 0)):
    "returns a PIL image of given frame of given art"
    post_fb_class = ExportFramebuffer if allow_crt else ExportFramebufferNoCRT
    # determine art's native size in pixels
    w = art.charset.char_width * art.width
    h = art.charset.char_height * art.height
    w, h = int(w * scale), int(h * scale)
    # create CRT framebuffer
    post_fb = post_fb_class(app, w, h)
    # create render target and target framebuffer that will become image
    export_fb = GL.glGenFramebuffers(1)
    render_buffer = GL.glGenRenderbuffers(1)
    GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, render_buffer)
    GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_RGBA8, w, h)
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, export_fb)
    GL.glFramebufferRenderbuffer(GL.GL_DRAW_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0,
                                 GL.GL_RENDERBUFFER, render_buffer)
    GL.glViewport(0, 0, w, h)
    # do render
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, post_fb.framebuffer)
    GL.glClearColor(*bg_color)
    GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
    # render to it
    art.renderables[0].render_frame_for_export(frame)
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, export_fb)
    post_fb.render()
    GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT0)
    # read pixels from it
    pixels = GL.glReadPixels(0, 0, w, h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
                             outputType=None)
    # cleanup / deinit of GL stuff
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
    GL.glViewport(0, 0, app.window_width, app.window_height)
    GL.glDeleteFramebuffers(1, [export_fb])
    GL.glDeleteRenderbuffers(1, [render_buffer])
    post_fb.destroy()
    # GL pixel data as numpy array -> bytes for PIL image export
    pixel_bytes = pixels.flatten().tobytes()
    src_img = Image.frombytes(mode='RGBA', size=(w, h), data=pixel_bytes)
    src_img = src_img.transpose(Image.FLIP_TOP_BOTTOM)
    return src_img

def export_animation(app, art, out_filename):
    # get list of rendered frame images
    frames = []
    # use arbitrary color for transparency
    i_transp = art.palette.get_random_non_palette_color()
    # GL wants floats
    f_transp = (i_transp[0]/255, i_transp[1]/255, i_transp[2]/255, 1.)
    for frame in range(art.frames):
        frame_img = get_frame_image(app, art, frame, allow_crt=False,
                                    scale=1, bg_color=f_transp)
        frame_img = art.palette.get_palettized_image(frame_img, i_transp[:3])
        frames.append(frame_img)
    # compile frames into animated GIF with proper frame delays
    # technique thanks to:
    # https://github.com/python-pillow/Pillow/blob/master/Scripts/gifmaker.py
    output_img = open(out_filename, 'wb')
    for i,img in enumerate(frames):
        delay = art.frame_delays[i] * 1000
        if i == 0:
            data = GifImagePlugin.getheader(img)[0]
            # PIL only wants to write GIF87a for some reason...
            # welcome to 1989 B]
            data[0] = data[0].replace(b'7', b'9')
            # TODO: loop doesn't work
            data += GifImagePlugin.getdata(img, duration=delay, transparency=0,
                                           loop=0)
            for b in data:
                output_img.write(b)
            continue
        delta = ImageChops.subtract_modulo(img, frames[i-1])
        # Image.getbbox() rather unhelpfully returns None if no delta
        dw, dh = delta.size
        bbox = delta.getbbox() or (0, 0, dw, dh)
        for b in GifImagePlugin.getdata(img.crop(bbox), offset=bbox[:2],
                                        duration=delay, transparency=0,
                                        loop=0):
            output_img.write(b)
    output_img.write(b';')
    output_img.close()
    output_format = 'Animated GIF'
    #app.log('%s exported (%s)' % (out_filename, output_format))


def export_still_image(app, art, out_filename, crt=True, scale=1):
    # respect "disable CRT entirely" setting for slow GPUs
    crt = False if app.fb.disable_crt else crt
    # just write RGBA if palette has more than one color with <1 alpha
    if crt or not art.palette.all_colors_opaque():
        src_img = get_frame_image(app, art, art.active_frame, True, scale)
        src_img.save(out_filename, 'PNG')
        output_format = '32-bit w/ alpha'
    else:
        # else convert to current palette.
        # as with aniGIF export, use arbitrary color for transparency
        i_transp = art.palette.get_random_non_palette_color()
        f_transp = (i_transp[0]/255, i_transp[1]/255, i_transp[2]/255, 1.)
        src_img = get_frame_image(app, art, art.active_frame, False, scale, f_transp)
        output_img = art.palette.get_palettized_image(src_img, i_transp[:3])
        output_img.save(out_filename, 'PNG', transparency=0)
        output_format = '8-bit palettized w/ transparency'
    #app.log('%s exported (%s)' % (out_filename, output_format))


def write_thumbnail(app, art_filename, thumb_filename):
    "write thumbnail. assume art is not loaded, tear down everything when done."
    art = app.load_art(art_filename, False)
    renderable = None
    if len(art.renderables) == 0:
        renderable = app.thumbnail_renderable_class(app, art)
        art.renderables.append(renderable)
    img = get_frame_image(app, art, 0, allow_crt=False)
    img.save(thumb_filename, 'PNG')
    if renderable:
        renderable.destroy()
