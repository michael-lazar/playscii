import sys, os.path

# obnoxious PyOpenGL workaround for py2exe
import platform
if platform.system() == 'Windows':
    import os
    # set env variable so pysdl2 can find sdl2.dll
    os.environ['PYSDL2_DLL_PATH'] = '.'
    sys.path += ['.']

# app imports
import ctypes, time, hashlib
import sdl2
import sdl2.ext
import appdirs
from sdl2 import video
from OpenGL import GL
from PIL import Image

# submodules - set here so cfg file can modify them all easily
from audio import AudioLord
from shader import ShaderLord
from camera import Camera
from charset import CharacterSet, CHARSET_DIR
from palette import Palette, PALETTE_DIR
from art import Art, ArtFromDisk, ArtFromEDSCII, EDSCII_FILE_EXTENSION
from renderable import TileRenderable, OnionTileRenderable
from framebuffer import Framebuffer
from art import ART_DIR, ART_FILE_EXTENSION, SCRIPT_DIR
from ui import UI
from cursor import Cursor
from grid import Grid
from input_handler import InputLord
from ui_file_chooser_dialog import THUMBNAIL_CACHE_DIR
# some classes are imported only so the cfg file can modify their defaults
from renderable_line import LineRenderable
from ui_swatch import CharacterSetSwatch
from ui_element import UIRenderable, FPSCounterUI, DebugTextUI
from image_convert import ImageConverter
from game_world import GameWorld, TOP_GAME_DIR
from game_object import GameObject

APP_NAME = 'Playscii'
VERSION_FILENAME = 'version'

CONFIG_FILENAME = 'playscii.cfg'
CONFIG_TEMPLATE_FILENAME = CONFIG_FILENAME + '.default'
LOG_FILENAME = 'console.log'
LOGO_FILENAME = 'ui/logo.png'
SCREENSHOT_DIR = 'screenshots/'

MAX_ONION_FRAMES = 3

class Application:
    # default window dimensions, may be updated during screen res detection
    window_width, window_height = 800, 600
    fullscreen = False
    # framerate: uncapped if -1
    framerate = 60
    # force to run even if we can't get an OpenGL 2.1 context
    run_if_opengl_incompatible = False
    # starting document defaults
    starting_charset = 'c64_petscii'
    starting_palette = 'c64_original'
    new_art_width, new_art_height = 20, 15
    # arbitrary size cap, but something bigger = probably a bad idea
    max_art_width, max_art_height = 9999, 9999
    # use capslock as another ctrl key - SDL2 doesn't seem to respect OS setting
    capslock_is_ctrl = False
    bg_color = [0.1, 0.1, 0.1, 1]
    # scaling factor used when CRT filter is on during image export
    export_crt_scale_factor = 4
    # scale for export when no CRT
    export_no_crt_scale_factor = 1
    # if True, ignore camera loc saved in .psci files
    override_saved_camera = False
    # launch into art mode even if a game dir is specified via CLI
    always_launch_art_mode = False
    # show dev-only log messages
    show_dev_log = False
    # toggles for "show all" debug viz modes
    show_collision_all = False
    show_bounds_all = False
    show_origin_all = False
    # in art mode, show layers marked invisible to game mode
    show_hidden_layers = False
    welcome_message = 'Welcome to Playscii! Press SPACE to select characters and colors to paint.'
    compat_fail_message = "your hardware doesn't appear to meet Playscii's requirements!  Sorry ;________;"
    game_mode_message = 'Game Mode active, press %s to return to Art Mode.'
    # can_edit: if False, user can't use art or edit functionality
    can_edit = True
    # start_game: if set, load this game on start no matter what
    start_game = None
    
    def __init__(self, config_dir, documents_dir, cache_dir,
                 log_lines, art_filename, game_dir_to_load, state_to_load):
        self.init_success = False
        self.config_dir = config_dir
        self.documents_dir = documents_dir
        self.cache_dir = cache_dir
        # last dir art was opened from
        self.last_art_dir = None
        # class to use for temp thumbnail renderable
        self.thumbnail_renderable_class = TileRenderable
        # log fed in from __main__, might already have stuff in it
        self.log_lines = log_lines
        self.log_file = open(self.config_dir + LOG_FILENAME, 'w')
        for line in self.log_lines:
            self.log_file.write('%s\n' % line)
        self.elapsed_time = 0
        self.delta_time = 0
        self.should_quit = False
        self.mouse_x, self.mouse_y = 0, 0
        self.inactive_layer_visibility = 1
        self.version = get_version()
        # last edit came from keyboard or mouse, used by cursor control logic
        self.keyboard_editing = False
        # set ui None so other objects can check it None, eg load_art check
        # for its active art on later runs (audiolord too)
        self.ui, self.al = None, None
        sdl2.ext.init()
        winpos = sdl2.SDL_WINDOWPOS_UNDEFINED
        # determine screen resolution
        test_window = sdl2.SDL_CreateWindow(bytes(APP_NAME, 'utf-8'),
                                            winpos, winpos,
                                            128, 128,
                                            sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP)
        sdl2.SDL_HideWindow(test_window)
        # SDL2 windows behavior differs, won't create window at desktop res :[
        if platform.system() == 'Windows':
            desktop = sdl2.video.SDL_DisplayMode()
            sdl2.SDL_GetDesktopDisplayMode(0, desktop)
            screen_width, screen_height = desktop.w, desktop.h
        else:
            screen_width, screen_height = ctypes.c_int(0), ctypes.c_int(0)
            sdl2.SDL_GetWindowSize(test_window, ctypes.pointer(screen_width),
                                   ctypes.pointer(screen_height))
            screen_width = screen_width.value
            screen_height = screen_height.value
        sdl2.SDL_DestroyWindow(test_window)
        # make sure main window won't be too big for screen
        max_width = int(screen_width * 0.8)
        max_height = int(screen_height * 0.8)
        self.window_width = min(self.window_width, max_width)
        self.window_height = min(self.window_height, max_height)
        # TODO: SDL_WINDOW_ALLOW_HIGHDPI doesn't seem to work right,
        # determine whether we're using it wrong or it's broken
        flags = sdl2.SDL_WINDOW_OPENGL | sdl2.SDL_WINDOW_RESIZABLE# | sdl2.SDL_WINDOW_ALLOW_HIGHDPI
        if self.fullscreen:
            flags = flags | sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP
        self.window = sdl2.SDL_CreateWindow(bytes(APP_NAME, 'utf-8'),
                                            winpos, winpos,
                                            self.window_width, self.window_height,
                                            flags)
        # force GL2.1 'core' before creating context
        video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MAJOR_VERSION, 2)
        video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_MINOR_VERSION, 1)
        video.SDL_GL_SetAttribute(video.SDL_GL_CONTEXT_PROFILE_MASK,
                                  video.SDL_GL_CONTEXT_PROFILE_CORE)
        self.context = sdl2.SDL_GL_CreateContext(self.window)
        # report OS, version, CPU
        self.log('OS: %s' % platform.platform())
        self.log('CPU: %s' % platform.processor())
        self.log('Python: %s' % ' '.join(sys.version.split('\n')))
        self.log('Detected screen resolution: %.0f x %.0f, using: %s x %s' % (screen_width, screen_height, self.window_width, self.window_height))
        # report GL version, vendor, GLSL version etc
        # try single-argument GL2.0 version first
        gl_ver = GL.glGetString(GL.GL_VERSION)
        if not gl_ver:
            gl_ver = GL.glGetString(GL.GL_VERSION, ctypes.c_int(0))
        gl_ver = gl_ver.decode('utf-8')
        self.log('OpenGL detected: %s' % gl_ver)
        # GL 1.1 doesn't even habla shaders, quit if we fail GLSL version check
        try:
            glsl_ver = GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION)
            if not glsl_ver:
                glsl_ver = GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION, ctypes.c_int(0))
        except:
            self.log('GLSL support not detected, ' + self.compat_fail_message)
            self.should_quit = True
            return
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
            self.log("Couldn't create a compatible OpenGL context, " + self.compat_fail_message)
            if not self.run_if_opengl_incompatible:
                self.should_quit = True
                return
        # draw black screen while doing other init
        GL.glClearColor(0.0, 0.0, 0.0, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        # initialize audio
        self.al = AudioLord(self)
        self.set_icon()
        # SHADERLORD rules shader init/destroy, hot reload
        self.sl = ShaderLord(self)
        # separate cameras for edit vs game mode
        self.edit_camera = Camera(self)
        self.camera = self.edit_camera
        self.art_loaded_for_edit, self.edit_renderables = [], []
        self.converter = None
        self.game_mode = False
        self.gw = GameWorld(self)
        # if game dir specified, set it before we try to load any art
        if game_dir_to_load or self.start_game:
            self.gw.set_game_dir(game_dir_to_load or self.start_game, False)
        # onion skin renderables
        self.onion_frames_visible = False
        self.onion_show_frames = MAX_ONION_FRAMES
        # store constant so input_handler etc can read it
        self.max_onion_frames = MAX_ONION_FRAMES
        self.onion_show_frames_behind = self.onion_show_frames_ahead = True
        self.onion_renderables_prev, self.onion_renderables_next = [], []
        # lists of currently loaded character sets and palettes
        self.charsets, self.palettes = [], []
        self.load_art_for_edit(art_filename)
        self.fb = Framebuffer(self)
        # setting cursor None now makes for easier check in status bar drawing
        self.cursor, self.grid = None, None
        # initialize UI with first art loaded active
        self.ui = UI(self, self.art_loaded_for_edit[0])
        # init onion skin
        for i in range(self.onion_show_frames):
            renderable = OnionTileRenderable(self, self.ui.active_art)
            self.onion_renderables_prev.append(renderable)
        for i in range(self.onion_show_frames):
            renderable = OnionTileRenderable(self, self.ui.active_art)
            self.onion_renderables_next.append(renderable)
        # set camera bounds based on art size
        self.camera.set_for_art(self.ui.active_art)
        self.update_window_title()
        self.cursor = Cursor(self)
        self.grid = Grid(self, self.ui.active_art)
        self.ui.set_active_layer(self.ui.active_art.active_layer)
        self.frame_time, self.fps, self.last_tick_time = 0, 0, 0
        # INPUTLORD rules input handling and keybinds
        self.il = InputLord(self)
        self.init_success = True
        self.log('init done.')
        if (game_dir_to_load or self.start_game) and self.gw.game_dir:
            # set initial game state
            if state_to_load:
                self.gw.load_game_state(state_to_load)
            else:
                self.gw.load_game_state()
        else:
            #self.ui.message_line.post_line(self.welcome_message, 10)
            pass
        if not self.can_edit:
            self.enter_game_mode()
        elif self.gw.game_dir and self.always_launch_art_mode:
            self.exit_game_mode()
    
    def set_icon(self):
        # TODO: this doesn't seem to work in Ubuntu, what am i missing?
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
        if self.ui:
            self.ui.message_line.post_line(new_line)
    
    def dev_log(self, new_line):
        if self.show_dev_log:
            self.log(new_line)
    
    def new_art(self, filename, width=None, height=None,
                charset=None, palette=None):
        width = width or self.new_art_width
        height = height or self.new_art_height
        filename = filename if filename and filename != '' else 'new'
        charset = self.load_charset(charset or self.starting_charset)
        palette = self.load_palette(palette or self.starting_palette)
        art = Art(filename, self, charset, palette, width, height)
        art.set_filename(filename)
        art.time_loaded = time.time()
        return art
    
    def load_art(self, filename, autocreate=True):
        """
        load given file from disk; by default autocreate new file if it
        couldn't be found
        """
        valid_filename = self.find_filename_path(filename, ART_DIR,
                                                 ART_FILE_EXTENSION)
        art = None
        if not valid_filename:
            if autocreate:
                self.log('Creating new art %s' % filename)
                return self.new_art(filename)
            else:
                #self.log("Couldn't find art %s" % filename)
                return None
        # if already loaded, return that
        for a in self.art_loaded_for_edit + self.gw.art_loaded:
            if a.filename == valid_filename:
                return a
        art = ArtFromDisk(valid_filename, self)
        # if loading failed, create new file
        if not art or not art.valid:
            return self.new_art(valid_filename)
        # remember time loaded for UI list sorting
        art.time_loaded = time.time()
        return art
    
    def new_art_for_edit(self, filename, width, height):
        art = self.new_art(filename, width, height)
        self.art_loaded_for_edit.insert(0, art)
        renderable = TileRenderable(self, art)
        self.edit_renderables.insert(0, renderable)
        self.ui.set_active_art(art)
        art.set_unsaved_changes(True)
    
    def load_art_for_edit(self, filename):
        art = self.load_art(filename)
        if art in self.art_loaded_for_edit:
            self.ui.message_line.post_line('Art file %s already loaded' % filename)
            return
        self.art_loaded_for_edit.insert(0, art)
        renderable = TileRenderable(self, art)
        self.edit_renderables.insert(0, renderable)
        if self.ui:
            self.ui.set_active_art(art)
    
    def close_art(self, art):
        if not art in self.art_loaded_for_edit:
            return
        self.art_loaded_for_edit.remove(art)
        for r in art.renderables:
            if r in self.edit_renderables:
                self.edit_renderables.remove(r)
        if art is self.ui.active_art:
            self.ui.active_art = None
        self.log('Unloaded %s' % art.filename)
        if len(self.art_loaded_for_edit) > 0:
            self.ui.set_active_art(self.art_loaded_for_edit[0])
        self.update_window_title()
    
    def revert_active_art(self):
        filename = self.ui.active_art.filename
        self.close_art(self.ui.active_art)
        self.load_art_for_edit(filename)
    
    def get_file_hash(self, filename):
        f_data = open(filename, 'rb').read()
        return hashlib.md5(f_data).hexdigest()
    
    def get_dirnames(self, subdir=None, include_base=True):
        "returns list of suitable directory names across app and user dirs"
        dirnames = []
        # build list of dirs to check, by priority:
        # gamedir/subdir if it exists, then ./subdir, then ./
        if self.gw.game_dir is not None:
            game_dir = self.gw.game_dir
            if subdir:
                game_dir += subdir
            if os.path.exists(game_dir):
                dirnames.append(game_dir)
        if subdir is not None:
            dirnames.append(subdir)
        if include_base:
            dirnames.append('')
        # add duplicate set of dirs in user documents path
        doc_dirs = []
        for dirname in dirnames:
            # dir might already have documents path in it, add as-is if so
            if dirname.startswith(self.documents_dir) and os.path.exists(dirname):
                doc_dirs.append(dirname)
                continue
            doc_dir = self.documents_dir + dirname
            if os.path.exists(doc_dir):
                doc_dirs.append(doc_dir)
        # check in user document dirs first
        return doc_dirs + dirnames
    
    def find_filename_path(self, filename, subdir=None, extensions=None):
        "returns a valid path for given file, extension, subdir (art/ etc)"
        if not filename or filename == '':
            return None
        dirnames = self.get_dirnames(subdir)
        # build list of filenames from each dir, first w/ extension then w/o
        filenames = []
        # extensions: accept list or single item,
        # list with one empty string if None passed
        if extensions is None or len(extensions) == 0:
            extensions = ['']
        elif not type(extensions) is list:
            extensions = [extensions]
        for dirname in dirnames:
            for ext in extensions:
                f = '%s%s' % (dirname, filename)
                # filename passed in might already have intended extension,
                # eg from a directory listing
                if ext and ext != '' and not filename.endswith(ext):
                    f += '.' + ext
                filenames.append(f)
        # return first one we find
        for f in filenames:
            if f is not None and os.path.exists(f) and os.path.isfile(f):
                return f
        return None
    
    def import_edscii(self, filename, width_override=None):
        """
        imports an EDSCII legacy file for edit
        use width_override to recover an incorrectly-saved file
        """
        valid_filename = self.find_filename_path(filename, ART_DIR,
                                                 EDSCII_FILE_EXTENSION)
        if not valid_filename:
            self.log("Couldn't find EDSCII file %s" % filename)
        art = ArtFromEDSCII(valid_filename, self, width_override)
        if not art.valid:
            self.log('Failed to load %s' % valid_filename)
            return
        art.time_loaded = time.time()
        self.art_loaded_for_edit.insert(0, art)
        renderable = TileRenderable(self, art)
        self.edit_renderables.insert(0, renderable)
        if self.ui:
            self.ui.set_active_art(art)
    
    def load_charset(self, charset_to_load, log=False):
        "creates and returns a character set with the given name"
        # already loaded?
        base_charset_to_load = os.path.basename(charset_to_load)
        base_charset_to_load = os.path.splitext(base_charset_to_load)[0]
        for charset in self.charsets:
            if charset.base_filename == base_charset_to_load:
                return charset
        new_charset = CharacterSet(self, charset_to_load, log)
        if new_charset.init_success:
            self.charsets.append(new_charset)
            return new_charset
        elif self.ui and self.ui.active_art:
            # if init failed (eg bad filename) return something safe
            return self.ui.active_art.charset
    
    def load_palette(self, palette_to_load, log=False):
        base_palette_to_load = os.path.basename(palette_to_load)
        base_palette_to_load = os.path.splitext(base_palette_to_load)[0]
        for palette in self.palettes:
            if palette.base_filename == base_palette_to_load:
                return palette
        new_palette = Palette(self, palette_to_load, log)
        if new_palette.init_success:
            self.palettes.append(new_palette)
            return new_palette
        elif self.ui and self.ui.active_art:
            # if init failed (eg bad filename) return something safe
            return self.ui.active_art.palette
    
    def set_window_title(self, text=None):
        new_title = APP_NAME
        if text:
            new_title += ' - %s' % text
        new_title = bytes(new_title, 'utf-8')
        sdl2.SDL_SetWindowTitle(self.window, new_title)
    
    def update_window_title(self):
        if self.game_mode and self.gw.game_dir:
            title = self.gw.last_state_loaded
            self.set_window_title(title)
            return
        if not self.ui.active_art:
            self.set_window_title()
            return
        # display current active document's name and info
        filename = self.ui.active_art.filename
        if filename and os.path.exists(filename):
            full_filename = os.path.abspath(filename)
        else:
            full_filename = filename
        if self.ui.active_art.unsaved_changes:
            full_filename += '*'
        self.set_window_title(full_filename)
    
    def resize_window(self, new_width, new_height):
        GL.glViewport(0, 0, new_width, new_height)
        self.window_width, self.window_height = new_width, new_height
        # tell FB, camera, and UI that view aspect has changed
        self.fb.resize(new_width, new_height)
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
        img.save('%s%s' % (self.documents_dir + SCREENSHOT_DIR, output_filename))
        self.log('Saved screenshot %s' % output_filename)
    
    def enter_game_mode(self):
        self.game_mode = True
        self.camera = self.gw.camera
        # cursor might be hovering an object's art, undo preview viz
        self.cursor.undo_preview_edits()
        # display message on how to toggle game mode
        mode_bind = self.il.get_command_shortcut('toggle_game_mode')
        mode_bind = mode_bind.title()
        if self.can_edit:
            self.ui.message_line.post_line(self.game_mode_message % mode_bind, 10)
        self.al.resume_music()
    
    def exit_game_mode(self):
        self.game_mode = False
        self.camera = self.edit_camera
        if self.ui.active_art:
            self.camera.set_for_art(self.ui.active_art)
        self.ui.message_line.post_line('', 1)
        self.update_window_title()
        self.al.pause_music()
    
    def main_loop(self):
        while not self.should_quit:
            # set all arts to "not updated"
            if self.game_mode:
                self.gw.pre_update()
            else:
                for art in self.art_loaded_for_edit:
                    art.updated_this_tick = False
            tick_time = sdl2.timer.SDL_GetTicks()
            self.handle_input()
            self.update(self.delta_time / 1000)
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
    
    def handle_input(self):
        self.il.handle_input()
    
    def update(self, dt):
        self.al.update()
        for art in self.art_loaded_for_edit:
            art.update()
        for renderable in self.edit_renderables:
            renderable.update()
        if self.converter:
            self.converter.update()
        if self.game_mode:
            self.gw.update(dt)
        self.camera.update()
        if self.ui.active_art and not self.ui.popup.visible and not self.ui.console.visible and not self.game_mode and not self.ui.menu_bar in self.ui.hovered_elements and not self.ui.menu_bar.active_menu_name and not self.ui.active_dialog:
            self.cursor.update(self.elapsed_time)
        if self.ui.visible:
            self.ui.update()
        if not self.game_mode:
            self.grid.update()
            self.cursor.end_update()
    
    def debug_onion_frames(self):
        "debug function to log onion renderable state"
        # TODO: remove this once it's served its purpose
        debug = ['current frame: %s' % self.ui.active_art.active_frame, '']
        debug.append('onion_renderables_prev:')
        def get_onion_info(i, r):
            visible = 'VISIBLE' if r.visible else ''
            return '%s: %s frame %s %s' % (i, r.art.filename.ljust(20), r.frame, visible)
        for i,r in enumerate(self.onion_renderables_prev):
            debug.append(get_onion_info(i, r))
        debug.append('')
        debug.append('onion_renderables_next:')
        for i,r in enumerate(self.onion_renderables_next):
            debug.append(get_onion_info(i, r))
        self.ui.debug_text.post_lines(debug)
    
    def render(self):
        # draw main scene to framebuffer
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fb.framebuffer)
        bg_color = self.gw.bg_color if self.game_mode else self.bg_color
        GL.glClearColor(*bg_color)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        if self.game_mode:
            self.gw.render()
        else:
            if self.converter:
                self.converter.preview_sprite.render()
            for r in self.edit_renderables:
                r.render()
            #self.debug_onion_frames()
            if self.onion_frames_visible:
                # draw "nearest" frames first
                i = 0
                while i < self.onion_show_frames:
                    if self.onion_show_frames_behind:
                        self.onion_renderables_prev[i].render()
                    if self.onion_show_frames_ahead:
                        self.onion_renderables_next[i].render()
                    i += 1
            # draw selection grid, then selection, then cursor
            if self.grid.visible and self.ui.active_art:
                self.grid.render()
            self.ui.select_tool.render_selections()
            if self.ui.active_art and not self.ui.popup.visible and not self.ui.console.visible and not self.ui.menu_bar in self.ui.hovered_elements and not self.ui.menu_bar.active_menu_name and not self.ui.active_dialog:
                self.cursor.render()
        # draw framebuffer to screen
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        self.fb.render(self.elapsed_time)
        if self.ui.visible:
            self.ui.render()
        GL.glUseProgram(0)
        sdl2.SDL_GL_SwapWindow(self.window)
    
    def quit(self):
        if self.init_success:
            self.log('Thank you for using Playscii!  <3')
            for r in self.edit_renderables:
                r.destroy()
            self.gw.destroy()
            self.fb.destroy()
            self.ui.destroy()
            for charset in self.charsets:
                charset.texture.destroy()
            for palette in self.palettes:
                palette.texture.destroy()
            self.sl.destroy()
        if self.al:
            self.al.destroy()
        sdl2.SDL_GL_DeleteContext(self.context)
        sdl2.SDL_DestroyWindow(self.window)
        sdl2.SDL_Quit()
        self.log_file.close()

def get_win_documents_path():
    # from http://stackoverflow.com/a/30924555/1191587
    # (winshell module too much of a pain to get working with py2exe)
    import ctypes.wintypes
    CSIDL_PERSONAL = 5       # My Documents
    SHGFP_TYPE_CURRENT = 1   # Get current, not default value
    buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
    return buf.value

def get_paths():
    # pass False as second arg to disable "app author" windows dir convention
    config_dir = appdirs.user_config_dir(APP_NAME, False) + '/'
    cache_dir = appdirs.user_cache_dir(APP_NAME, False) + '/'
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
    if not os.path.exists(cache_dir + THUMBNAIL_CACHE_DIR):
        os.mkdir(cache_dir + THUMBNAIL_CACHE_DIR)
    DOCUMENTS_SUBDIR = '/Documents'
    if platform.system() == 'Windows':
        documents_dir = get_win_documents_path()
    elif platform.system() == 'Darwin':
        documents_dir = os.path.expanduser('~') + DOCUMENTS_SUBDIR
    elif platform.system() == 'Linux':
        # XDG spec doesn't cover any concept of a documents folder :[
        # if ~/Documents exists use that, else just use ~/Playscii
        documents_dir = os.path.expanduser('~')
        if os.path.exists(documents_dir + DOCUMENTS_SUBDIR):
            documents_dir += DOCUMENTS_SUBDIR
    # add Playscii/ to documents path
    documents_dir += '/%s/' % APP_NAME
    # create Playscii dir AND subdirs for user art, charsets etc if not present
    for subdir in ['', ART_DIR, CHARSET_DIR, PALETTE_DIR,
                   SCRIPT_DIR, SCREENSHOT_DIR, TOP_GAME_DIR]:
        if not os.path.exists(documents_dir + subdir):
            os.mkdir(documents_dir + subdir)
    return config_dir, documents_dir, cache_dir

def get_version():
    return open(VERSION_FILENAME).readlines()[0].strip()

if __name__ == "__main__":
    # start log even before Application has initialized so we can write to it
    # startup message: application and version #
    line = '%s v%s' % (APP_NAME, get_version())
    log_lines = [line]
    print(line)
    # get paths for config file, later to be passed into Application
    config_dir, documents_dir, cache_dir = get_paths()
    # load in config - may change above values and submodule class defaults
    if os.path.exists(config_dir + CONFIG_FILENAME):
        exec(open(config_dir + CONFIG_FILENAME).read())
        line = 'Loaded config from %s' % config_dir + CONFIG_FILENAME
        log_lines.append(line)
        print(line)
    # if cfg file doesn't exist, copy a new one from playscii.cfg.default
    else:
        # snip first "this is a template" line
        default_data = open(CONFIG_TEMPLATE_FILENAME).readlines()[1:]
        new_cfg = open(config_dir + CONFIG_FILENAME, 'w')
        new_cfg.writelines(default_data)
        new_cfg.close()
        exec(''.join(default_data))
        line = 'Created new config file %s' % config_dir + CONFIG_FILENAME
        log_lines.append(line)
        print(line)
    file_to_load, game_dir_to_load, state_to_load = None, None, None
    # usage:
    # playscii.py [artfile] | [-game gamedir [-state statefile | artfile]]
    if len(sys.argv) > 1:
        # "-game test1" args will set test1/ as game dir
        if len(sys.argv) > 2 and sys.argv[1] == '-game':
            game_dir_to_load = sys.argv[2]
            # "-state testX" args will load testX game state from given game dir
            if len(sys.argv) > 4 and sys.argv[3] == '-state':
                state_to_load = sys.argv[4]
            elif len(sys.argv) > 3:
                file_to_load = sys.argv[3]
        else:
            # else assume first arg is an art file to load in art mode
            file_to_load = sys.argv[1]
    app = Application(config_dir, documents_dir, cache_dir, log_lines,
                      file_to_load or 'new', game_dir_to_load, state_to_load)
    error = app.main_loop()
    app.quit()
    sys.exit(error)
