import sys, os.path, time

from random import random

# obnoxious PyOpenGL workaround for py2exe
import platform
if platform.system() == 'Windows':
    import os
    # set env variable so pysdl2 can find sdl2.dll
    os.environ['PYSDL2_DLL_PATH'] = '.'
    sys.path += ['.']

# app imports
import ctypes
import sdl2
import sdl2.ext
from sdl2 import video
from OpenGL import GL
from PIL import Image

# submodules - set here so cfg file can modify them all easily
from shader import ShaderLord
from camera import Camera
from charset import CharacterSet
from palette import Palette
from art import Art, ArtFromDisk, ArtFromEDSCII
from renderable import TileRenderable
from framebuffer import Framebuffer
from art import ART_DIR, ART_FILE_EXTENSION
from ui import UI, SCALE_INCREMENT
from cursor import Cursor
from grid import Grid
# some classes are imported only so the cfg file can modify their defaults
from renderable_line import LineRenderable
from ui_swatch import CharacterSetSwatch

CONFIG_FILENAME = 'playscii.cfg'
LOG_FILENAME = 'console.log'
LOGO_FILENAME = 'ui/logo.png'

VERSION = '0.3.0'

class Application:
    
    window_width, window_height = 800, 600
    fullscreen = False
    # framerate: uncapped if -1
    framerate = 60
    base_title = 'Playscii'
    # force to run even if we can't get an OpenGL 2.1 context
    run_if_opengl_incompatible = False
    # starting document defaults
    starting_charset = 'c64'
    starting_palette = 'c64'
    starting_width, starting_height = 8, 8
    # use capslock as another ctrl key - SDL2 doesn't seem to respect OS setting
    capslock_is_ctrl = False
    bg_color = (0.1, 0.1, 0.1, 1)
    # if True, ignore camera loc saved in .psci files
    override_saved_camera = False
    # debug test stuff
    test_mutate_each_frame = False
    test_life_each_frame = False
    test_art = False
    auto_save = False
    
    def __init__(self, log_file, log_lines, art_filename):
        self.init_success = False
        # log fed in from __main__, might already have stuff in it
        self.log_file = log_file
        self.log_lines = log_lines
        self.elapsed_time = 0
        self.should_quit = False
        self.mouse_x, self.mouse_y = 0, 0
        sdl2.ext.init()
        flags = sdl2.SDL_WINDOW_OPENGL | sdl2.SDL_WINDOW_RESIZABLE | sdl2.SDL_WINDOW_ALLOW_HIGHDPI
        if self.fullscreen:
            flags = flags | sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP
        self.window = sdl2.SDL_CreateWindow(bytes(self.base_title, 'utf-8'), sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED, self.window_width, self.window_height, flags)
        # force GL2.1 'core' before creating context
        video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MAJOR_VERSION, 2)
        video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MINOR_VERSION, 1)
        video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_PROFILE_MASK,
                                  video.SDL_GL_CONTEXT_PROFILE_CORE)
        self.context = sdl2.SDL_GL_CreateContext(self.window)
        # report GL version, vendor, GLSL version etc
        # try single-argument GL2.0 version first
        gl_ver = GL.glGetString(GL.GL_VERSION)
        if not gl_ver:
            gl_ver = GL.glGetString(GL.GL_VERSION, ctypes.c_int(0))
        gl_ver = gl_ver.decode('utf-8')
        self.log('OpenGL detected: %s' % gl_ver)
        glsl_ver = GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION)
        if not glsl_ver:
            glsl_ver = GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION, ctypes.c_int(0))
        glsl_ver = glsl_ver.decode('utf-8')
        self.log('GLSL detected: %s' % glsl_ver)
        # verify that we got at least a 2.1 context
        majorv, minorv = ctypes.c_int(0), ctypes.c_int(0)
        video.SDL_GL_GetAttribute(video.SDL_GL_CONTEXT_MAJOR_VERSION, majorv)
        video.SDL_GL_GetAttribute(video.SDL_GL_CONTEXT_MINOR_VERSION, minorv)
        context_version = majorv.value + (minorv.value * 0.1)
        vao_support = bool(GL.glGenVertexArrays)
        self.log('Vertex Array Object support %sfound.' % ['NOT ', ''][vao_support])
        if not vao_support  or context_version < 2.1 or gl_ver.startswith('2.0'):
            self.log("Could not create a compatible OpenGL context, your hardware doesn't appear to meet Playscii's requirements!  Sorry ;_________;")
            if not self.run_if_opengl_incompatible:
                self.should_quit = True
                return
        # draw black screen while doing other init
        self.sdl_renderer = sdl2.SDL_CreateRenderer(self.window, -1, sdl2.SDL_RENDERER_ACCELERATED)
        self.blank_screen()
        self.set_icon()
        # SHADERLORD rules shader init/destroy, hot reload
        self.sl = ShaderLord(self)
        self.camera = Camera(self)
        self.art_loaded, self.edit_renderables = [], []
        # lists of currently loaded character sets and palettes
        self.charsets, self.palettes = [], []
        # set ui None so load_art can check for its active art on later runs
        self.ui = None
        self.load_art(art_filename)
        self.fb = Framebuffer(self)
        # setting cursor None now makes for easier check in status bar drawing
        self.cursor, self.grid = None, None
        # initialize UI with first art loaded active
        self.ui = UI(self, self.art_loaded[0])
        self.update_window_title()
        self.cursor = Cursor(self)
        self.grid = Grid(self, self.ui.active_art)
        self.ui.set_active_layer(0)
        self.frame_time, self.fps, self.last_tick_time = 0, 0, 0
        self.init_success = True
        self.log('init done.')
    
    def set_icon(self):
        # TODO: this doesn't seem to work in Ubuntu or Windows,
        # what am i missing?
        img = Image.open(LOGO_FILENAME).convert('RGBA')
        # does icon need to be a specific size?
        img = img.resize((32, 32), Image.ANTIALIAS)
        w, h = img.size
        depth, pitch = 32, w * 4
        #SDL_CreateRGBSurfaceFrom((pixels, width, height, depth, pitch, Rmask, Gmask, Bmask, Amask)
        #mask = (0x0f00, 0x00f0, 0x000f, 0xf000)
        mask = (0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000)
        icon_surf = sdl2.SDL_CreateRGBSurfaceFrom(img.tobytes(), w, h, depth, pitch, *mask)
        # SDL_SetWindowIcon(self.window, SDL_Surface* icon)
        sdl2.SDL_SetWindowIcon(self.window, icon_surf)
        sdl2.SDL_FreeSurface(icon_surf)
    
    def log(self, new_line):
        "write to log file, stdout, and in-app console log"
        self.log_file.write('%s\n' % new_line)
        self.log_lines.append(new_line)
        print(new_line)
    
    def new_art(self, filename):
        filename = filename or '%snew' % ART_DIR
        charset = self.load_charset(self.starting_charset)
        palette = self.load_palette(self.starting_palette)
        return Art(filename, self, charset, palette, self.starting_width, self.starting_height)
    
    def load_art(self, filename):
        """
        determine a viable filename and load it from disk;
        create new file if unsuccessful
        """
        orig_filename = filename
        filename = filename or 'new'
        # try adding art subdir
        if not os.path.exists(filename):
            filename = '%s%s' % (ART_DIR, filename)
        # if not found, try adding extension
        if not os.path.exists(filename):
            filename += '.%s' % ART_FILE_EXTENSION
        art = None
        # use given path + file name even if it doesn't exist; use as new file's name
        if not os.path.exists(filename):
            text = 'creating new document %s' % filename
            if orig_filename:
                text = "couldn't find file %s, %s" % (orig_filename, text)
            self.log(text)
            art = self.new_art(filename)
        else:
            for a in self.art_loaded:
                # TODO: this check doesn't work on EDSCII imports b/c its name changes
                if a.filename == filename:
                    self.log('Art file %s already loaded' % filename)
                    return
            art = ArtFromDisk(filename, self)
            if not art or not art.valid:
                art = ArtFromEDSCII(filename, self)
            # if file failed to load, create a new file with that name
            # TODO: this may be foolish, ensure this never overwrites user data
            if not art or not art.valid:
                art = self.new_art(filename)
        # add to list of arts loaded
        self.art_loaded.insert(0, art)
        renderable = TileRenderable(self, art)
        self.edit_renderables.insert(0, renderable)
        if self.ui:
            self.ui.set_active_art(art)
    
    def recover_edscii(self, filename, width_override):
        "recovers an incorrectly-saved EDSCII file using the given width"
        art = ArtFromEDSCII(filename, self, width_override)
        self.art_loaded.insert(0, art)
        renderable = TileRenderable(self, art)
        self.edit_renderables.insert(0, renderable)
        if self.ui:
            self.ui.set_active_art(art)
    
    def load_charset(self, charset_to_load, log=True):
        "creates and returns a character set with the given name"
        # already loaded?
        for charset in self.charsets:
            if charset_to_load == charset.name:
                return charset
        new_charset = CharacterSet(self, charset_to_load, log)
        if new_charset.init_success:
            self.charsets.append(new_charset)
            return new_charset
        else:
            # if init failed (eg bad filename) return something safe
            return self.ui.active_art.charset
    
    def load_palette(self, palette_to_load, log=True):
        for palette in self.palettes:
            if palette.name == palette_to_load:
                return palette
        new_palette = Palette(self, palette_to_load, log)
        if new_palette.init_success:
            self.palettes.append(new_palette)
            return new_palette
        else:
            # if init failed (eg bad filename) return something safe
            return self.ui.active_art.palette
    
    def set_window_title(self, text):
        new_title = bytes('%s - %s' % (self.base_title, text), 'utf-8')
        sdl2.SDL_SetWindowTitle(self.window, new_title)
    
    def update_window_title(self):
        # display current active document's name and info
        filename = self.ui.active_art.filename
        if filename and os.path.exists(filename):
            full_filename = os.path.abspath(filename)
        else:
            full_filename = filename
        self.set_window_title(full_filename)
    
    def blank_screen(self):
        r = sdl2.SDL_Rect()
        r.x, r.y = 0,0
        r.w, r.h = self.window_width, self.window_height
        sdl2.SDL_SetRenderDrawColor(self.sdl_renderer, 0, 0, 0, 255)
        sdl2.SDL_RenderFillRect(self.sdl_renderer, r)
        sdl2.SDL_GL_SwapWindow(self.window)
    
    def resize_window(self, new_width, new_height):
        GL.glViewport(0, 0, new_width, new_height)
        self.window_width, self.window_height = new_width, new_height
        # preserve FB state, eg CRT shader enabled
        crt = self.fb.crt
        # create a new framebuffer in its place
        # TODO: determine if it's better to do this or change existing fb
        self.fb = Framebuffer(self)
        self.fb.crt = crt
        # tell camera and UI that view aspect has changed
        self.camera.window_resized()
        self.ui.window_resized()
    
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = 0
        if self.fullscreen:
            flags = sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP
        sdl2.SDL_SetWindowFullscreen(self.window, flags)
        # for all intents and purposes, this is like resizing the window
        self.resize_window(self.window_width, self.window_height)
    
    def screenshot(self):
        "saves a date + time-stamped screenshot"
        timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
        output_filename = 'playscii_%s.png' % timestamp
        w, h = self.window_width, self.window_height
        pixels = GL.glReadPixels(0, 0, w, h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
                                 outputType=None)
        pixel_bytes = pixels.flatten().tobytes()
        img = Image.frombytes(mode='RGBA', size=(w, h), data=pixel_bytes)
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img.save(output_filename)
        self.log('Saved screenshot %s' % output_filename)
    
    def export_image(self, art):
        output_filename = '%s.png' % os.path.splitext(art.filename)[0]
        # determine art's native size in pixels
        w = art.charset.char_width * art.width
        h = art.charset.char_height * art.height
        # TODO: if CRT is on, use that shader for output w/ a scale factor!
        scale = 2 if self.fb.crt and not self.fb.disable_crt else 1
        # create render target
        #export_fb = Framebuffer(self, w * scale, h * scale)
        #GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, export_fb.framebuffer)
        #GL.glClearColor(*self.bg_color)
        #GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
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
        #export_fb.render(self.elapsed_time)
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT0)
        # read pixels from it
        pixels = GL.glReadPixels(0, 0, w, h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE,
                                 outputType=None)
        # cleanup / deinit of GL stuff
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        GL.glViewport(0, 0, self.window_width, self.window_height)
        GL.glDeleteFramebuffers(1, [framebuffer])
        GL.glDeleteRenderbuffers(1, [render_buffer])
        # GL pixel data as numpy array -> bytes for PIL image export
        pixel_bytes = pixels.flatten().tobytes()
        img = Image.frombytes(mode='RGBA', size=(w, h), data=pixel_bytes)
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img.save(output_filename)
        self.log('%s exported' % output_filename)
    
    def main_loop(self):
        while not self.should_quit:
            tick_time = sdl2.timer.SDL_GetTicks()
            self.input()
            self.update()
            self.render()
            self.sl.check_hot_reload()
            elapsed_time = sdl2.timer.SDL_GetTicks()
            # determine frame work time, feed it into delay
            tick_time = elapsed_time - tick_time
            self.delta_time = elapsed_time - self.elapsed_time
            self.elapsed_time = elapsed_time
            # determine FPS
            # alpha: lower = smoother
            alpha = 0.2
            self.frame_time = alpha * self.delta_time + (1 - alpha) * self.frame_time
            self.fps = 1000 / self.frame_time
            # delay to maintain framerate, if uncapped
            if self.framerate != -1:
                delay = int(1000 / self.framerate)
                # subtract work time from delay to maintain framerate
                delay -= min(delay, tick_time)
                sdl2.timer.SDL_Delay(delay)
            self.last_tick_time = tick_time
        return 1
    
    def input(self):
        # get and store mouse state
        mx, my = ctypes.c_int(0), ctypes.c_int(0)
        mouse = sdl2.mouse.SDL_GetMouseState(mx, my)
        self.left_mouse = bool(mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_LEFT))
        self.middle_mouse = bool(mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_MIDDLE))
        self.right_mouse = bool(mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_RIGHT))
        self.mouse_x, self.mouse_y = int(mx.value), int(my.value)
        # relative mouse move state
        mdx, mdy = ctypes.c_int(0), ctypes.c_int(0)
        sdl2.mouse.SDL_GetRelativeMouseState(mdx, mdy)
        self.mouse_dx, self.mouse_dy = int(mdx.value), int(mdy.value)
        # get keyboard state so later we can directly query keys
        ks = sdl2.SDL_GetKeyboardState(None)
        # get modifier states
        shift_pressed, alt_pressed, ctrl_pressed = False, False, False
        if ks[sdl2.SDL_SCANCODE_LSHIFT] or ks[sdl2.SDL_SCANCODE_RSHIFT]:
            shift_pressed = True
        if ks[sdl2.SDL_SCANCODE_LALT] or ks[sdl2.SDL_SCANCODE_RALT]:
            alt_pressed = True
        if ks[sdl2.SDL_SCANCODE_LCTRL] or ks[sdl2.SDL_SCANCODE_RCTRL]:
            ctrl_pressed = True
        if self.capslock_is_ctrl and ks[sdl2.SDL_SCANCODE_CAPSLOCK]:
            ctrl_pressed = True
        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                self.should_quit = True
            elif event.type == sdl2.SDL_WINDOWEVENT:
                if event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED:
                    self.resize_window(event.window.data1, event.window.data2)
            elif event.type == sdl2.SDL_KEYDOWN:
                # ctrl q: quit
                if ctrl_pressed and event.key.keysym.sym == sdl2.SDLK_q:
                    self.should_quit = True
                # `: toggle console
                elif event.key.keysym.sym == sdl2.SDLK_BACKQUOTE:
                    self.ui.console.toggle()
                # ctrl-E: export active art to PNG
                elif ctrl_pressed and event.key.keysym.sym == sdl2.SDLK_e:
                    self.export_image(self.ui.active_art)
                # ctrl +/-: change UI scale
                elif ctrl_pressed and event.key.keysym.sym == sdl2.SDLK_EQUALS:
                    self.ui.set_scale(self.ui.scale + SCALE_INCREMENT)
                elif ctrl_pressed and event.key.keysym.sym == sdl2.SDLK_MINUS:
                    if self.ui.scale > SCALE_INCREMENT * 2:
                        self.ui.set_scale(self.ui.scale - SCALE_INCREMENT)
                # alt-enter: toggle fullscreen
                elif alt_pressed and event.key.keysym.sym == sdl2.SDLK_RETURN:
                    self.toggle_fullscreen()
                # if console is up, pass input to it - keys above work regardless
                elif self.ui.console.visible:
                    self.ui.console.handle_input(event.key.keysym.sym, shift_pressed, alt_pressed, ctrl_pressed)
                # 1/2: decrease/increase current tool brush size
                elif event.key.keysym.sym == sdl2.SDLK_1:
                    self.ui.selected_tool.decrease_brush_size()
                elif event.key.keysym.sym == sdl2.SDLK_2:
                    self.ui.selected_tool.increase_brush_size()
                # 3/4/5: set current tool affects char/fg/bg
                elif event.key.keysym.sym == sdl2.SDLK_3:
                    self.ui.selected_tool.toggle_affects_char()
                elif event.key.keysym.sym == sdl2.SDLK_4:
                    self.ui.selected_tool.toggle_affects_fg()
                elif event.key.keysym.sym == sdl2.SDLK_5:
                    self.ui.selected_tool.toggle_affects_bg()
                elif event.key.keysym.sym == sdl2.SDLK_r:
                    self.fb.toggle_crt()
                # spacebar: pop up tool / selector
                elif event.key.keysym.sym == sdl2.SDLK_SPACE:
                    self.ui.popup.show()
                # select next/previous char/fg/bg
                elif event.key.keysym.sym == sdl2.SDLK_c:
                    if shift_pressed:
                        self.ui.select_char(self.ui.selected_char-1)
                    else:
                        self.ui.select_char(self.ui.selected_char+1)
                elif event.key.keysym.sym == sdl2.SDLK_f:
                    if shift_pressed:
                        self.ui.select_fg(self.ui.selected_fg_color-1)
                    else:
                        self.ui.select_fg(self.ui.selected_fg_color+1)
                elif event.key.keysym.sym == sdl2.SDLK_b:
                    if shift_pressed:
                        self.ui.select_bg(self.ui.selected_bg_color-1)
                    else:
                        self.ui.select_bg(self.ui.selected_bg_color+1)
                # shift-S: swap fg/bg color
                elif shift_pressed and event.key.keysym.sym == sdl2.SDLK_s:
                    self.ui.swap_fg_bg_colors()
                # shift-U: toggle UI visibility
                elif shift_pressed and event.key.keysym.sym == sdl2.SDLK_u:
                    self.ui.visible = not self.ui.visible
                # G: toggle grid visibilty:
                elif event.key.keysym.sym == sdl2.SDLK_g:
                    self.grid.visible = not self.grid.visible
                # < > / , . rewind / advance current art's anim frame
                elif event.key.keysym.sym == sdl2.SDLK_COMMA:
                    self.ui.set_active_frame(self.ui.active_frame - 1)
                elif event.key.keysym.sym == sdl2.SDLK_PERIOD:
                    self.ui.set_active_frame(self.ui.active_frame + 1)
                # p starts/pauses animation playback of current art
                elif event.key.keysym.sym == sdl2.SDLK_p:
                    for r in self.ui.active_art.renderables:
                        r.animating = not r.animating
                # [ ] set active layer
                elif event.key.keysym.sym == sdl2.SDLK_RIGHTBRACKET:
                    self.ui.set_active_layer(self.ui.active_layer + 1)
                elif event.key.keysym.sym == sdl2.SDLK_LEFTBRACKET:
                    self.ui.set_active_layer(self.ui.active_layer - 1)
                elif event.key.keysym.sym == sdl2.SDLK_TAB:
                    if ctrl_pressed and not shift_pressed:
                        self.ui.next_active_art()
                    elif ctrl_pressed and shift_pressed:
                        self.ui.previous_active_art()
                # shift-ctrl-z does red, ctrl-z does undo
                elif shift_pressed and ctrl_pressed and event.key.keysym.sym == sdl2.SDLK_z:
                    self.ui.redo()
                elif ctrl_pressed and event.key.keysym.sym == sdl2.SDLK_z:
                    self.ui.undo()
                # enter does Cursor.paint
                elif event.key.keysym.sym == sdl2.SDLK_RETURN:
                    self.cursor.start_paint()
                # q does quick grab
                elif event.key.keysym.sym == sdl2.SDLK_q:
                    self.ui.quick_grab()
                # F12: screenshot
                elif event.key.keysym.sym == sdl2.SDLK_F12:
                    self.screenshot()
                # TEST: toggle artscript running
                elif event.key.keysym.sym == sdl2.SDLK_m:
                    if self.ui.active_art.is_script_running('conway'):
                        self.ui.active_art.stop_script('conway')
                    else:
                        self.ui.active_art.run_script_every('conway', 0.05)
                # TEST: alt + arrow keys [do something]
                elif alt_pressed and event.key.keysym.sym == sdl2.SDLK_UP:
                    pass
                elif alt_pressed and event.key.keysym.sym == sdl2.SDLK_DOWN:
                    pass
                elif alt_pressed and event.key.keysym.sym == sdl2.SDLK_LEFT:
                    pass
                elif alt_pressed and event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    pass
                # TEST: shift-T toggles camera tilt
                elif shift_pressed and event.key.keysym.sym == sdl2.SDLK_t:
                    if self.camera.y_tilt == 2:
                        self.camera.y_tilt = 0
                        self.log('Camera tilt disengaged.')
                    else:
                        self.camera.y_tilt = 2
                        self.log('Camera tilt engaged.')
                # arrow keys move cursor
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    self.cursor.move(0, 1)
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    self.cursor.move(0, -1)
                elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                    self.cursor.move(-1, 0)
                elif event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    self.cursor.move(1, 0)
            elif event.type == sdl2.SDL_KEYUP:
                # spacebar up: dismiss selector popup
                if event.key.keysym.sym == sdl2.SDLK_SPACE:
                    self.ui.popup.hide()
                elif event.key.keysym.sym == sdl2.SDLK_RETURN:
                    self.cursor.finish_paint()
            elif event.type == sdl2.SDL_MOUSEWHEEL:
                if event.wheel.y > 0:
                    self.camera.zoom(-3)
                elif event.wheel.y < 0:
                    self.camera.zoom(3)
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                self.ui.unclicked(event.button.button)
                if event.button.button == sdl2.SDL_BUTTON_LEFT:
                    self.cursor.finish_paint()
            elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                self.ui.clicked(event.button.button)
                if event.button.button == sdl2.SDL_BUTTON_LEFT:
                    self.cursor.start_paint()
                elif event.button.button == sdl2.SDL_BUTTON_RIGHT:
                    self.ui.quick_grab()
        # directly query keys we don't want affected by OS key repeat delay
        if not alt_pressed and not ctrl_pressed and not shift_pressed and not self.ui.console.visible:
            if ks[sdl2.SDL_SCANCODE_W]:
                self.camera.pan(0, 1)
            if ks[sdl2.SDL_SCANCODE_S]:
                self.camera.pan(0, -1)
            if ks[sdl2.SDL_SCANCODE_A]:
                self.camera.pan(-1, 0)
            if ks[sdl2.SDL_SCANCODE_D]:
                self.camera.pan(1, 0)
            if ks[sdl2.SDL_SCANCODE_X]:
                self.camera.zoom(-1)
            if ks[sdl2.SDL_SCANCODE_Z]:
                self.camera.zoom(1)
        sdl2.SDL_PumpEvents()
    
    def update(self):
        for art in self.art_loaded:
            art.update()
        for renderable in self.edit_renderables:
            renderable.update()
        self.camera.update()
        if self.test_mutate_each_frame:
            self.test_mutate_each_frame = False
            self.ui.active_art.run_script_every('mutate', 0.01)
        if self.test_life_each_frame:
            self.test_life_each_frame = False
            self.ui.active_art.run_script_every('conway', 0.05)
        if self.test_art:
            self.test_art = False
            # load some test data - simulates some user edits:
            # add layers, write text, duplicate that frame, do some animation
            self.ui.active_art.run_script('hello1')
        # test saving functionality
        if self.auto_save:
            art.save_to_file()
            self.auto_save = False
        if not self.ui.popup.visible and not self.ui.console.visible:
            self.cursor.update(self.elapsed_time)
        if self.ui.visible:
            self.ui.update()
        self.grid.update()
    
    def render(self):
        # draw main scene to framebuffer
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fb.framebuffer)
        GL.glClearColor(*self.bg_color)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        for r in self.edit_renderables:
            r.render(self.elapsed_time)
        if self.grid.visible:
            self.grid.render(self.elapsed_time)
        if not self.ui.popup.visible and not self.ui.console.visible:
            self.cursor.render(self.elapsed_time)
        # draw framebuffer to screen
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        self.fb.render(self.elapsed_time)
        if self.ui.visible:
            self.ui.render(self.elapsed_time)
        #self.ui.active_art.renderables[0].render_for_export()
        GL.glUseProgram(0)
        sdl2.SDL_GL_SwapWindow(self.window)
    
    def quit(self):
        self.log('Thank you for using Playscii!  <3')
        if self.init_success:
            for r in self.edit_renderables:
                r.destroy()
            self.fb.destroy()
            self.ui.destroy()
            for charset in self.charsets:
                charset.texture.destroy()
            for palette in self.palettes:
                palette.texture.destroy()
            self.sl.destroy()
        sdl2.SDL_GL_DeleteContext(self.context)
        sdl2.SDL_DestroyWindow(self.window)
        sdl2.SDL_Quit()
        self.log_file.close()


# load in config - may change above values and submodule class defaults
# TODO: if doesn't exist, copy a new one from playscii.cfg.example
if os.path.exists(CONFIG_FILENAME):
    exec(open(CONFIG_FILENAME).read())

if __name__ == "__main__":
    file_to_load = None
    # start log file even before Application has initialized so we can write to it
    log_file = open(LOG_FILENAME, 'w')
    log_lines = []
    # startup message: application and version #
    line = '%s v%s' % (Application.base_title, VERSION)
    log_file.write('%s\n' % line)
    log_lines.append(line)
    print(line)
    file_to_load = None
    if len(sys.argv) > 1:
        file_to_load = sys.argv[1]
    app = Application(log_file, log_lines, file_to_load)
    error = app.main_loop()
    app.quit()
    sys.exit(error)
