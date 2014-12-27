import sys, os.path

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
from framebuffer import Framebuffer

CONFIG_FILENAME = 'playscii.cfg'

class Application:
    
    window_width, window_height = 800, 600
    fullscreen = False
    framerate = 60
    title = b'<3 Playscii'
    starting_charset = 'c64'
    starting_palette = 'c64'
    
    def __init__(self):
        self.elapsed_time = 0
        sdl2.ext.init()
        flags = sdl2.SDL_WINDOW_OPENGL | sdl2.SDL_WINDOW_RESIZABLE | sdl2.SDL_WINDOW_ALLOW_HIGHDPI
        if self.fullscreen:
            flags = flags | sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP
        self.window = sdl2.SDL_CreateWindow(self.title, sdl2.SDL_WINDOWPOS_UNDEFINED, sdl2.SDL_WINDOWPOS_UNDEFINED, self.window_width, self.window_height, flags)
        # force GL2.1 'core' before creating context
        video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MAJOR_VERSION, 2)
        video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MINOR_VERSION, 1)
        video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_PROFILE_MASK,
                                  video.SDL_GL_CONTEXT_PROFILE_CORE)
        self.context = sdl2.SDL_GL_CreateContext(self.window)
        # draw black screen while doing other init
        self.sdl_renderer = sdl2.SDL_CreateRenderer(self.window, -1, sdl2.SDL_RENDERER_ACCELERATED)
        self.blank_screen()
        # SHADERLORD rules shader init/destroy, hot reload
        self.sl = ShaderLord(self)
        self.camera = Camera(self.window_width, self.window_height)
        # TODO: cursor
        self.renderables = []
        # add renderables to list in reverse draw order (only world for now)
        # TODO: create a test renderable
        #self.renderables.append()
        self.fb = Framebuffer(self.sl, self.window_width, self.window_height)
        # TODO: UI
    
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
        #self.ui.window_resized(new_width, new_height)
    
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
            self.camera.update()
            #self.cursor.update(self.elapsed_time)
            #self.ui.update()
            self.render()
            sdl2.SDL_Delay(int(1000/self.framerate))
            self.elapsed_time = sdl2.timer.SDL_GetTicks()
            self.sl.check_hot_reload()
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
        # don't mouse pan view if we're hovering any UI
        """
        if len(self.ui.hovered_elements) == 0 and (left_mouse or right_mouse) and mouse_dx != 0 and mouse_dy != 0:
            self.camera.mouse_pan(mouse_dx, mouse_dy)
        """
        # directly query keys we don't want affected by OS key repeat delay
        ks = sdl2.SDL_GetKeyboardState(None)
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
        alt_pressed, ctrl_pressed = False, False
        if ks[sdl2.SDL_SCANCODE_LALT] or ks[sdl2.SDL_SCANCODE_RALT]:
            alt_pressed = True
        if ks[sdl2.SDL_SCANCODE_LCTRL] or ks[sdl2.SDL_SCANCODE_RCTRL]:
            ctrl_pressed = True
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
            elif event.type == sdl2.SDL_MOUSEWHEEL:
                if event.wheel.y > 0:
                    self.camera.zoom(-3)
                elif event.wheel.y < 0:
                    self.camera.zoom(3)
            """
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                self.ui.unclicked(event.button.button)
            elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                self.ui.clicked(event.button.button)
            """
        sdl2.SDL_PumpEvents()
        return True
    
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
        #self.ui.render(self.elapsed_time)
        GL.glUseProgram(0)
        sdl2.SDL_GL_SwapWindow(self.window)
    
    def quit(self):
        for r in self.renderables:
            r.destroy()
        self.fb.destroy()
        self.sl.destroy()
        sdl2.SDL_GL_DeleteContext(self.context)
        sdl2.SDL_DestroyWindow(self.window)
        sdl2.SDL_Quit()


# load in config - may change above values and submodule class defaults
# TODO: if doesn't exist, copy a new one from playscii.cfg.example
if os.path.exists(CONFIG_FILENAME):
    exec(open(CONFIG_FILENAME).read())

if __name__ == "__main__":
    app = Application()
    error = app.main_loop()
    app.quit()
    sys.exit(error)
