import sys, os.path

from random import random

# obnoxious PyOpenGL workaround for py2exe
import platform
if platform.system() == 'Windows':
    sys.path += ['.']

# app imports
import ctypes
import sdl2
import sdl2.ext
from sdl2 import video
from OpenGL import GL

# submodules - set here so cfg file can modify them all easily
from shader import ShaderLord
from camera import Camera
from charset import CharacterSet
from palette import Palette
from art import Art, ArtFromDisk, ArtFromEDSCII
from renderable import Renderable
from framebuffer import Framebuffer
from art import ART_DIR, ART_FILE_EXTENSION
from ui import UI

CONFIG_FILENAME = 'playscii.cfg'

class Application:
    
    window_width, window_height = 800, 600
    fullscreen = False
    # framerate: uncapped if -1
    framerate = 60
    base_title = 'Playscii'
    # starting document defaults
    starting_charset = 'c64'
    starting_palette = 'c64'
    starting_width, starting_height = 8, 8
    # use capslock as another ctrl key - SDL2 doesn't seem to respect OS setting
    capslock_is_ctrl = False
    # debug test stuff
    test_mutate_each_frame = False
    test_life_each_frame = False
    test_art = False
    auto_save = False
    
    def __init__(self, art_filename):
        self.elapsed_time = 0
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
        # draw black screen while doing other init
        self.sdl_renderer = sdl2.SDL_CreateRenderer(self.window, -1, sdl2.SDL_RENDERER_ACCELERATED)
        self.blank_screen()
        # TODO: SDL_SetWindowIcon(self.window, SDL_Surface* icon) <- ui/logo.png
        # SHADERLORD rules shader init/destroy, hot reload
        self.sl = ShaderLord(self)
        self.camera = Camera(self.window_width, self.window_height)
        # TODO: cursor
        self.renderables = []
        # lists of currently loaded character sets and palettes
        self.charsets, self.palettes = [], []
        art = ArtFromDisk(art_filename, self)
        if not art or not art.valid:
            art = ArtFromEDSCII(art_filename, self)
            if not art or not art.valid:
                art = self.new_art(art_filename)
        # keep a list of all art assets loaded (stub for MDI support)
        self.art_loaded = [art]
        test_renderable = Renderable(self, art)
        # add renderables to list in reverse draw order (only world for now)
        self.renderables.append(test_renderable)
        self.fb = Framebuffer(self.sl, self.window_width, self.window_height)
        self.update_window_title()
        self.ui = UI(self)
        self.frame_time, self.fps = 0, 0
        print('init done.')
    
    def new_art(self, filename):
        filename = filename or '%snew' % ART_DIR
        charset = self.load_charset(self.starting_charset)
        palette = self.load_palette(self.starting_palette)
        return Art(filename, self, charset, palette, self.starting_width, self.starting_height)
    
    def load_charset(self, charset_to_load):
        "creates and returns a character set with the given name"
        # already loaded?
        for charset in self.charsets:
            if charset_to_load == charset.name:
                return charset
        new_charset = CharacterSet(charset_to_load)
        self.charsets.append(new_charset)
        # return newly loaded charset to whatever's requesting it
        return new_charset
    
    def load_palette(self, palette_to_load):
        for palette in self.palettes:
            if palette.name == palette_to_load:
                return palette
        new_palette = Palette(palette_to_load)
        self.palettes.append(new_palette)
        return new_palette
    
    def set_window_title(self, text):
        new_title = bytes('%s - %s' % (self.base_title, text), 'utf-8')
        sdl2.SDL_SetWindowTitle(self.window, new_title)
    
    def update_window_title(self):
        # TODO: once playscii can open multiple documents, get current active
        # document's name
        filename = self.art_loaded[0].filename
        if filename and os.path.exists(filename):
            full_filename = os.path.abspath(filename)
        else:
            full_filename = filename
        current_frame = self.renderables[0].frame
        title = '%s (frame %s)' % (full_filename, current_frame)
        self.set_window_title(title)
    
    def blank_screen(self):
        r = sdl2.SDL_Rect()
        r.x, r.y = 0,0
        r.w, r.h = self.window_width, self.window_height
        sdl2.SDL_SetRenderDrawColor(self.sdl_renderer, 0, 0, 0, 255)
        sdl2.SDL_RenderFillRect(self.sdl_renderer, r)
        sdl2.SDL_GL_SwapWindow(self.window)
    
    def resize(self, new_width, new_height):
        GL.glViewport(0, 0, new_width, new_height)
        self.window_width, self.window_height = new_width, new_height
        # preserve FB state, eg CRT shader enabled
        crt = self.fb.crt
        # create a new framebuffer in its place
        # TODO: determine if it's better to do this or change existing fb
        self.fb = Framebuffer(self.sl, self.window_width, self.window_height)
        self.fb.crt = crt
        # tell camera and UI that view aspect has changed
        self.camera.window_resized(new_width, new_height)
        self.ui.window_resized()
    
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = 0
        if self.fullscreen:
            flags = sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP
        sdl2.SDL_SetWindowFullscreen(self.window, flags)
    
    def main_loop(self):
        running = True
        while running:
            running = self.input()
            self.update()
            self.render()
            self.sl.check_hot_reload()
            # TODO: use sdlgfx framerate manager class?
            elapsed_time = sdl2.timer.SDL_GetTicks()
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
                # TODO: determine frame work time, subtract from delay to get
                # accurate framerate
                sdl2.timer.SDL_Delay(delay)
        return 1
    
    def input(self):
        # get mouse state and tell cursor
        mouse_x, mouse_y = ctypes.c_int(0), ctypes.c_int(0)
        mouse = sdl2.mouse.SDL_GetMouseState(mouse_x, mouse_y)
        left_mouse = mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_LEFT)
        middle_mouse = mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_MIDDLE)
        right_mouse = mouse & sdl2.SDL_BUTTON(sdl2.SDL_BUTTON_RIGHT)
        #self.cursor.mouse_x,self.cursor.mouse_y = int(mouse_x.value), int(mouse_y.value)
        # tell UI about mouse as well
        #self.ui.mouse_x, self.ui.mouse_y = self.cursor.mouse_x,self.cursor.mouse_y
        # relative mouse move state for panning
        mouse_dx, mouse_dy = ctypes.c_int(0), ctypes.c_int(0)
        sdl2.mouse.SDL_GetRelativeMouseState(mouse_dx, mouse_dy)
        mouse_dx, mouse_dy = int(mouse_dx.value), int(mouse_dy.value)
        # directly query keys we don't want affected by OS key repeat delay
        ks = sdl2.SDL_GetKeyboardState(None)
        # get modifier states
        alt_pressed, ctrl_pressed = False, False
        if ks[sdl2.SDL_SCANCODE_LALT] or ks[sdl2.SDL_SCANCODE_RALT]:
            alt_pressed = True
        if ks[sdl2.SDL_SCANCODE_LCTRL] or ks[sdl2.SDL_SCANCODE_RCTRL]:
            ctrl_pressed = True
        if self.capslock_is_ctrl and ks[sdl2.SDL_SCANCODE_CAPSLOCK]:
            ctrl_pressed = True
        if not alt_pressed and not ctrl_pressed:
            if ks[sdl2.SDL_SCANCODE_UP] or ks[sdl2.SDL_SCANCODE_W]:
                self.camera.pan(0, 1)
            if ks[sdl2.SDL_SCANCODE_DOWN] or ks[sdl2.SDL_SCANCODE_S]:
                self.camera.pan(0, -1)
            if ks[sdl2.SDL_SCANCODE_LEFT] or ks[sdl2.SDL_SCANCODE_A]:
                self.camera.pan(-1, 0)
            if ks[sdl2.SDL_SCANCODE_RIGHT] or ks[sdl2.SDL_SCANCODE_D]:
                self.camera.pan(1, 0)
            if ks[sdl2.SDL_SCANCODE_X]:
                self.camera.zoom(-1)
            if ks[sdl2.SDL_SCANCODE_Z]:
                self.camera.zoom(1)
        for event in sdl2.ext.get_events():
            if event.type == sdl2.SDL_QUIT:
                return False
            elif event.type == sdl2.SDL_WINDOWEVENT:
                if event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED:
                    self.resize(event.window.data1, event.window.data2)
            elif event.type == sdl2.SDL_KEYDOWN:
                # TODO: move exit to something safer, eg ctrl-q
                if event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                    return False
                elif event.key.keysym.sym == sdl2.SDLK_RETURN and alt_pressed:
                    self.toggle_fullscreen()
                # TODO: redo these from u4mapvu
                elif event.key.keysym.sym == sdl2.SDLK_1:
                    self.camera.set_zoom(1)
                elif event.key.keysym.sym == sdl2.SDLK_2:
                    self.camera.set_zoom(2)
                elif event.key.keysym.sym == sdl2.SDLK_c:
                    self.fb.toggle_crt()
                # ctrl +/- changes UI scale
                elif ctrl_pressed and event.key.keysym.sym == sdl2.SDLK_EQUALS:
                    self.ui.set_scale(self.ui.scale + 1)
                elif ctrl_pressed and event.key.keysym.sym == sdl2.SDLK_MINUS:
                    self.ui.set_scale(self.ui.scale - 1)
                # TEST: < > / , . rewind / advance anim frame
                elif event.key.keysym.sym == sdl2.SDLK_COMMA:
                    self.renderables[0].rewind_frame()
                    self.update_window_title()
                elif event.key.keysym.sym == sdl2.SDLK_PERIOD:
                    self.renderables[0].advance_frame()
                    self.update_window_title()
                # TEST: p starts/pauses animation playback
                elif event.key.keysym.sym == sdl2.SDLK_p:
                    self.renderables[0].animating = not self.renderables[0].animating
                # TEST: toggle artscript running
                elif event.key.keysym.sym == sdl2.SDLK_m:
                    art = self.art_loaded[0]
                    if art.is_script_running('conway'):
                        art.stop_script('conway')
                    else:
                        art.run_script_every('conway', 0.05)
                # TEST: alt + arrow keys move object
                elif alt_pressed and event.key.keysym.sym == sdl2.SDLK_UP:
                    self.ui.elements[0].renderable.y += 0.1
                elif alt_pressed and event.key.keysym.sym == sdl2.SDLK_DOWN:
                    self.ui.elements[0].renderable.y -= 0.1
                elif alt_pressed and event.key.keysym.sym == sdl2.SDLK_LEFT:
                    self.ui.elements[0].renderable.x -= 0.1
                elif alt_pressed and event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    self.ui.elements[0].renderable.x += 0.1
                    self.ui.elements[0].renderable.log_loc()
            elif event.type == sdl2.SDL_MOUSEWHEEL:
                if event.wheel.y > 0:
                    self.camera.zoom(-3)
                elif event.wheel.y < 0:
                    self.camera.zoom(3)
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                self.ui.unclicked(event.button.button)
            elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                self.ui.clicked(event.button.button)
        sdl2.SDL_PumpEvents()
        return True
    
    def update(self):
        for art in self.art_loaded:
            art.update()
        for renderable in self.renderables:
            renderable.update()
        self.camera.update()
        if self.test_mutate_each_frame:
            self.test_mutate_each_frame = False
            self.art_loaded[0].run_script_every('mutate', 0.01)
        if self.test_life_each_frame:
            self.test_life_each_frame = False
            self.art_loaded[0].run_script_every('conway', 0.05)
        if self.test_art:
            self.test_art = False
            art = self.art_loaded[0]
            # load some test data - simulates some user edits:
            # add layers, write text, duplicate that frame, do some animation
            art.run_script('hello1')
        # test saving functionality
        if self.auto_save:
            art.save_to_file()
            self.auto_save = False
        # TODO: cursor
        #self.cursor.update(self.elapsed_time)
        self.ui.update()
    
    def render(self):
        # draw main scene to framebuffer
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fb.framebuffer)
        GL.glClearColor(0.1, 0.1, 0.1, 1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        for r in self.renderables:
            r.render(self.elapsed_time)
        # draw framebuffer to screen
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        self.fb.render(self.elapsed_time)
        self.ui.render(self.elapsed_time)
        GL.glUseProgram(0)
        sdl2.SDL_GL_SwapWindow(self.window)
    
    def quit(self):
        # TODO: save to temp file quit?
        for r in self.renderables:
            r.destroy()
        self.fb.destroy()
        for charset in self.charsets:
            charset.texture.destroy()
        for palette in self.palettes:
            palette.texture.destroy()
        self.sl.destroy()
        sdl2.SDL_GL_DeleteContext(self.context)
        sdl2.SDL_DestroyWindow(self.window)
        sdl2.SDL_Quit()


# load in config - may change above values and submodule class defaults
# TODO: if doesn't exist, copy a new one from playscii.cfg.example
if os.path.exists(CONFIG_FILENAME):
    exec(open(CONFIG_FILENAME).read())

if __name__ == "__main__":
    file_to_load = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # if file not found, try adding art subdir
        if not os.path.exists(arg):
            arg = '%s%s' % (ART_DIR, arg)
        # if file still not found, try adding extension
        if not os.path.exists(arg):
            arg += '.%s' % ART_FILE_EXTENSION
        # use given path + file name even if it doesn't exist; use as new file's name
        if not os.path.exists(arg):
            print("couldn't find file %s, creating a new document." % sys.argv[1])
        file_to_load = arg
    app = Application(file_to_load)
    error = app.main_loop()
    app.quit()
    sys.exit(error)
