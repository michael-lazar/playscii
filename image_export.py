import os
from OpenGL import GL
from PIL import Image

def export_animation(app, art):
    # TODO
    pass

def export_still_image(app, art):
    output_filename = '%s.png' % os.path.splitext(art.filename)[0]
    # determine art's native size in pixels
    w = art.charset.char_width * art.width
    h = art.charset.char_height * art.height
    # TODO: if CRT is on, use that shader for output w/ a scale factor!
    scale = 2 if app.fb.crt and not app.fb.disable_crt else 1
    # create render target
    framebuffer = GL.glGenFramebuffers(1)
    render_buffer = GL.glGenRenderbuffers(1)
    GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, render_buffer)
    GL.glRenderbufferStorage(GL.GL_RENDERBUFFER, GL.GL_RGBA8, w, h)
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, framebuffer)
    GL.glFramebufferRenderbuffer(GL.GL_DRAW_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0,
                                 GL.GL_RENDERBUFFER, render_buffer)
    GL.glViewport(0, 0, w, h)
    GL.glClearColor(0, 0, 0, 0)
    GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
    # render to it
    art.renderables[0].render_for_export()
    #export_fb.render(app.elapsed_time)
    GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT0)
    # read pixels from it
    pixels = GL.glReadPixels(0, 0, w, h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
                             outputType=None)
    # cleanup / deinit of GL stuff
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
    GL.glViewport(0, 0, app.window_width, app.window_height)
    GL.glDeleteFramebuffers(1, [framebuffer])
    GL.glDeleteRenderbuffers(1, [render_buffer])
    # GL pixel data as numpy array -> bytes for PIL image export
    pixel_bytes = pixels.flatten().tobytes()
    src_img = Image.frombytes(mode='RGBA', size=(w, h), data=pixel_bytes)
    src_img = src_img.transpose(Image.FLIP_TOP_BOTTOM)
    # just write RGBA if palette has more than one color with <1 alpha
    if not art.palette.all_colors_opaque():
        src_img.save(output_filename, 'PNG')
        output_format = '32-bit w/ alpha'
    # else convert to current palette
    else:
        output_img = art.palette.get_palettized_image(src_img)
        output_img.save(output_filename, 'PNG', transparency=0)
        output_format = '8-bit palettized w/ transparency'
    app.log('%s exported (%s)' % (output_filename, output_format))
