#!/usr/bin/env python3
# coding=utf-8

from __future__ import print_function
import sys, os.path

if sys.version_info.major < 3:
    print('Python 3 is required to run Playscii.', file=sys.stderr)
    sys.exit(1)

import platform
if platform.system() == 'Windows' or platform.system() == 'Darwin':
    import os
    # set env variable so pysdl2 can find sdl2.dll
    os.environ['PYSDL2_DLL_PATH'] = '.'
    sys.path += ['.']

# fix the working directory when running in a mac app
if platform.system() == 'Darwin' and hasattr(sys, 'frozen'):
    os.chdir(os.path.abspath(os.path.dirname(sys.executable)))

# app imports
import ctypes, time, hashlib, importlib, traceback
import webbrowser
import sdl2
import sdl2.ext
import appdirs
import PIL, OpenGL, numpy # just for version checks
from sdl2 import video, sdlmixer
from OpenGL import GL
from PIL import Image
# import pdoc here so pyinstaller recognizes it's a dependency,
# but fail non-catastrophically
# TODO: this shouldn't be necessary; remove this ASAP
try:
    import pdoc, markdown
except:
    pass

# submodules - set here so cfg file can modify them all easily
from audio import AudioLord
from shader import ShaderLord
from camera import Camera
from charset import CharacterSet, CharacterSetLord, CHARSET_DIR
from palette import Palette, PaletteLord, PALETTE_DIR
from art import Art, ArtFromDisk, DEFAULT_CHARSET, DEFAULT_PALETTE, DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_ART_FILENAME
from art_import import ArtImporter
from art_export import ArtExporter
from renderable import TileRenderable, OnionTileRenderable
from renderable_line import DebugLineRenderable
from renderable_sprite import UIBGTextureRenderable
from framebuffer import Framebuffer
from art import ART_DIR, ART_FILE_EXTENSION, ART_SCRIPT_DIR
from ui import UI
from cursor import Cursor
from grid import ArtGrid
from input_handler import InputLord
from ui_file_chooser_dialog import THUMBNAIL_CACHE_DIR
# some classes are imported only so the cfg file can modify their defaults
from renderable_line import LineRenderable
from ui_swatch import CharacterSetSwatch
from ui_element import UIRenderable, FPSCounterUI, DebugTextUI
from ui_menu_pulldown import PulldownMenu
from ui_dialog import UIDialog
from ui_chooser_dialog import ScrollArrowButton, ChooserDialog
from image_convert import ImageConverter
from game_world import GameWorld, TOP_GAME_DIR
from game_object import GameObject
from shader import Shader

APP_NAME = 'Playscii'
VERSION_FILENAME = 'version'

CONFIG_FILENAME = 'playscii.cfg'
CONFIG_TEMPLATE_FILENAME = CONFIG_FILENAME + '.default'
LOG_FILENAME = 'console.log'
SESSION_FILENAME = 'playscii.session'
LOGO_FILENAME = 'ui/logo.png'
SCREENSHOT_DIR = 'screenshots/'
FORMATS_DIR = 'formats/'
AUTOPLAY_GAME_FILENAME = 'autoplay_this_game'

WEBSITE_URL = 'http://vectorpoem.com/playscii'
WEBSITE_HELP_URL = 'docs/html/howto_main.html'
AUTOGEN_DOCS_PATH = 'docs/html/generated/'
AUTOGEN_DOC_MODULES = ['game_object', 'game_world', 'game_room', 'collision',
                       'game_util_objects', 'art', 'renderable', 'vector',
                       'art_import', 'art_export']
AUTOGEN_DOC_TOC_PAGE = 'pdoc_toc.html'

MAX_ONION_FRAMES = 3

class Application:
    # default window dimensions, may be updated during screen res detection
    window_width, window_height = 1280, 720
    fullscreen = False
    # framerate: uncapped if -1
    framerate = 30
    # fixed timestep for game physics
    update_rate = 30
    # force to run even if we can't get an OpenGL 2.1 context
    run_if_opengl_incompatible = False
    # arbitrary size cap, but something bigger = probably a bad idea
    max_art_width, max_art_height = 9999, 9999
    # use capslock as another ctrl key - SDL2 doesn't seem to respect OS setting
    capslock_is_ctrl = False
    bg_color = [0.2, 0.2, 0.2, 2]
    show_bg_texture = True
    # if True, ignore camera loc saved in .psci files
    override_saved_camera = False
    # launch into art mode even if a game dir is specified via CLI
    always_launch_art_mode = False
    # show dev-only log messages
    show_dev_log = False
    # in art mode, show layers marked invisible to game mode
    show_hidden_layers = False
    welcome_message = 'Welcome to Playscii! Press SPACE to select characters and colors to paint.'
    compat_fail_message = "your hardware doesn't appear to meet Playscii's requirements!  Sorry ;________;"
    game_mode_message = 'Game Mode active, press %s to return to Art Mode.'
    img_convert_message = 'converting bitmap image: %s'
    # can_edit: if False, user can't use art or edit functionality
    can_edit = True
    # these values should be written to cfg files on exit
    # key = module path, value = [member object (blank if self), var name]
    persistent_setting_names = {
        'UI.popup_hold_to_show': ['ui', 'popup_hold_to_show'],
        'Framebuffer.start_crt_enabled': ['fb', 'crt'],
        'Application.show_bg_texture': ['', 'show_bg_texture'],
        'ArtGrid.visible': ['art_grid', 'visible']
    }
    # characters that can't appear in filenames (any OS; Windows is least permissive)
    forbidden_filename_chars = ['/', '\\', '*', ':']
    
    def __init__(self, config_dir, documents_dir, cache_dir, logger,
                 art_filename, game_dir_to_load, state_to_load, autoplay_game):
        self.init_success = False
        self.config_dir = config_dir
        # keep playscii.cfg lines in case we want to add some
        self.config_lines = open(self.config_dir + CONFIG_FILENAME).readlines()
        self.documents_dir = documents_dir
        self.cache_dir = cache_dir
        # last dir art was opened from
        self.last_art_dir = None
        # last dir file was imported from
        self.last_import_dir = None
        # class to use for temp thumbnail renderable
        self.thumbnail_renderable_class = TileRenderable
        # logger fed in from __main__
        self.logger = logger
        self.last_time = 0
        self.this_frame_start, self.last_frame_end = 0, 0
        # number of updates (world, etc) and rendered frames this session
        self.updates, self.frames = 0, 0
        self.timestep = (1 / self.update_rate) * 1000
        # for FPS counter
        self.frame_time, self.fps = 0, 0
        self.should_quit = False
        self.mouse_x, self.mouse_y = 0, 0
        self.mouse_dx, self.mouse_dy = 0, 0
        self.inactive_layer_visibility = 1
        self.version = get_version()
        # last edit came from keyboard or mouse, used by cursor control logic
        self.keyboard_editing = False
        # set ui None so other objects can check it None, eg load_art check
        # for its active art on later runs (audiolord too)
        self.ui, self.al = None, None
        sdl2.ext.init()
        winpos = sdl2.SDL_WINDOWPOS_UNDEFINED
        screen_width, screen_height = self.get_desktop_resolution()
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
        self.log('Detecting hardware...')
        # report OS, version, CPU
        cpu = platform.processor()
        self.log('  CPU: %s' % (cpu if cpu != '' else "[couldn't detect CPU]"))
        self.log('  OS: %s' % platform.platform())
        py_version = ' '.join(sys.version.split('\n'))
        # report 32 vs 64 bit as it's not clear from sys.version or OS
        bitness = platform.architecture()[0]
        self.log('  Python: %s (%s)' % (py_version, bitness))
        module_versions = 'PySDL2: %s, ' % sdl2.__version__
        module_versions += 'numpy: %s, ' % numpy.__version__
        module_versions += 'PyOpenGL: %s, ' % OpenGL.__version__
        module_versions += 'appdirs: %s, ' % appdirs.__version__
        module_versions += 'PIL: %s' % PIL.__version__
        self.log('  Modules: %s' % module_versions)
        sdl_version = '%s.%s.%s ' % (sdl2.version.SDL_MAJOR_VERSION,
                                     sdl2.version.SDL_MINOR_VERSION,
                                     sdl2.version.SDL_PATCHLEVEL)
        sdl_version += sdl2.version.SDL_GetRevision().decode('utf-8')
        sdl_version += ', SDLmixer: %s.%s.%s' % (sdlmixer.SDL_MIXER_MAJOR_VERSION,
                                                 sdlmixer.SDL_MIXER_MINOR_VERSION,
                                                 sdlmixer.SDL_MIXER_PATCHLEVEL)
        self.log('  SDL: %s' % sdl_version)
        self.log('  Detected screen resolution: %.0f x %.0f, window: %s x %s' % (screen_width, screen_height, self.window_width, self.window_height))
        # report GL vendor, version, GLSL version etc
        try: gpu_vendor = GL.glGetString(GL.GL_VENDOR).decode('utf-8')
        except: gpu_vendor = "[couldn't detect vendor]"
        try: gpu_renderer = GL.glGetString(GL.GL_RENDERER).decode('utf-8')
        except: gpu_renderer = "[couldn't detect renderer]"
        self.log('  GPU: %s - %s' % (gpu_vendor, gpu_renderer))
        try:
            # try single-argument GL2.0 version first
            gl_ver = GL.glGetString(GL.GL_VERSION)
            if not gl_ver:
                gl_ver = GL.glGetString(GL.GL_VERSION, ctypes.c_int(0))
            gl_ver = gl_ver.decode('utf-8')
        except:
            gl_ver = "[couldn't detect GL version]"
        self.log('  OpenGL detected: %s' % gl_ver)
        # GL 1.1 doesn't even habla shaders, quit if we fail GLSL version check
        try:
            glsl_ver = GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION)
            if not glsl_ver:
                glsl_ver = GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION, ctypes.c_int(0))
        except:
            self.log('GLSL support not detected, ' + self.compat_fail_message)
            self.should_quit = True
            return
	
        glsl_ver = glsl_ver.decode('utf-8') if glsl_ver != None else None
        self.log('  GLSL detected: %s' % glsl_ver or '[unknown]')
        # verify that we got at least a 2.1 context
        majorv, minorv = ctypes.c_int(0), ctypes.c_int(0)
        video.SDL_GL_GetAttribute(video.SDL_GL_CONTEXT_MAJOR_VERSION, majorv)
        video.SDL_GL_GetAttribute(video.SDL_GL_CONTEXT_MINOR_VERSION, minorv)
        context_version = majorv.value + (minorv.value * 0.1)
        self.use_vao = bool(GL.glGenVertexArrays)
        self.log('  Vertex Array Object support %sfound.' % ['NOT ', ''][self.use_vao])
        self.use_vao = False ##### DEBUG
        # enforce VAO / GL version requirement
        if context_version < 2.1 or gl_ver.startswith('2.0'):
            self.log("Couldn't create a compatible OpenGL context, " + self.compat_fail_message)
            if not self.run_if_opengl_incompatible:
                self.should_quit = True
                return
        # enforce GLSL version requirement
        if bool(glsl_ver) and float(glsl_ver.split()[0]) <= 1.2:
            self.log("GLSL 1.30 or higher is required, " + self.compat_fail_message)
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
        self.art_camera = Camera(self)
        self.camera = self.art_camera
        self.art_loaded_for_edit, self.edit_renderables = [], []
        # raster images (debug)
        self.img_renderables = []
        self.converter = None
        # set when an import is in progress
        self.importer = None
        # set when an exporter is chosen, remains so last_export can run
        self.exporter = None
        self.last_export_options = {}
        # dict of available importer/exporter modules
        self.converter_modules = {}
        # last art script run (remember for "run last")
        self.last_art_script = None
        self.game_mode = False
        self.gw = GameWorld(self)
        # if game dir specified, set it before we try to load any art
        if game_dir_to_load or autoplay_game:
            self.gw.set_game_dir(game_dir_to_load or autoplay_game, False)
        # autoplay = distribution mode, no editing
        if autoplay_game and not game_dir_to_load and self.gw.game_dir:
            self.can_edit = False
        # debug line renderable
        self.debug_line_renderable = DebugLineRenderable(self, None)
        # onion skin renderables
        self.onion_frames_visible = False
        self.onion_show_frames = MAX_ONION_FRAMES
        # store constant so input_handler etc can read it
        self.max_onion_frames = MAX_ONION_FRAMES
        self.onion_show_frames_behind = self.onion_show_frames_ahead = True
        self.onion_renderables_prev, self.onion_renderables_next = [], []
        # lists of currently loaded character sets and palettes
        self.charsets, self.palettes = [], []
        self.csl = CharacterSetLord(self)
        self.pl = PaletteLord(self)
        # set/create an active art
        self.load_art_for_edit(art_filename)
        self.fb = Framebuffer(self)
        # setting cursor None now makes for easier check in status bar drawing
        self.cursor, self.grid = None, None
        # separate grids for art vs game mode
        self.art_grid = None
        # forward-declare inputlord in case UI looks for it
        self.il = None
        # initialize UI with first art loaded active
        self.ui = UI(self, self.art_loaded_for_edit[0])
        # textured background renderable
        self.bg_texture = UIBGTextureRenderable(self)
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
        self.art_grid = ArtGrid(self, self.ui.active_art)
        self.grid = self.art_grid
        self.ui.set_active_layer(self.ui.active_art.active_layer)
        # INPUTLORD rules input handling and keybinds
        self.il = InputLord(self)
        self.init_success = True
        self.log('init done.')
        if self.can_edit:
            self.restore_session()
        # if art file was given in arguments, set it active
        if art_filename:
            self.ui.set_active_art_by_filename(art_filename)
        if (game_dir_to_load or autoplay_game) and self.gw.game_dir:
            # set initial game state
            if state_to_load:
                self.gw.load_game_state(state_to_load)
            else:
                self.gw.load_game_state()
        else:
            #self.ui.message_line.post_line(self.welcome_message, 10)
            pass
        # if "autoplay_this_game" used and game is valid, lock out edit mode
        if not self.can_edit:
            self.enter_game_mode()
            self.ui.set_game_edit_ui_visibility(False, False)
            self.gw.draw_debug_objects = False
        elif self.gw.game_dir and self.always_launch_art_mode:
            self.exit_game_mode()
    
    def get_desktop_resolution(self):
        winpos = sdl2.SDL_WINDOWPOS_UNDEFINED
        # SDL2 win/mac behavior differs, won't create window at desktop res :[
        create_test_window = platform.system() not in ['Windows', 'Darwin']
        if not create_test_window:
            desktop = sdl2.video.SDL_DisplayMode()
            sdl2.SDL_GetDesktopDisplayMode(0, desktop)
            return desktop.w, desktop.h
        test_window = sdl2.SDL_CreateWindow(bytes(APP_NAME, 'utf-8'),
                                            winpos, winpos,
                                            128, 128,
                                            sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP)
        sdl2.SDL_HideWindow(test_window)
        screen_width, screen_height = ctypes.c_int(0), ctypes.c_int(0)
        sdl2.SDL_GetWindowSize(test_window, ctypes.pointer(screen_width),
                               ctypes.pointer(screen_height))
        screen_width = screen_width.value
        screen_height = screen_height.value
        sdl2.SDL_DestroyWindow(test_window)
        return screen_width, screen_height
    
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
    
    def log(self, new_line, error=False):
        "write to log file, stdout, and in-app console log"
        self.logger.log(new_line)
        if self.ui and self.can_edit:
            self.ui.message_line.post_line(new_line, hold_time=None, error=error)
    
    def dev_log(self, new_line):
        if self.show_dev_log:
            self.log(new_line)
    
    def log_import_exception(self, e, module_name):
        """
        Logs a readable version of stack trace of given exception encountered
        importing given module name.
        """
        for line in traceback.format_exc().split('\n'):
            # ignore the importlib parts of the call stack,
            # not useful and always the same
            if line and not 'importlib' in line and \
               not 'in _import_all' in line and \
               not '_bootstrap._gcd_import' in line:
                self.log(line.rstrip())
            s = 'Error importing module %s! See console.' % module_name
            if self.ui:
                self.ui.message_line.post_line(s, 10, True)
    
    def new_art(self, filename, width=None, height=None,
                charset=None, palette=None):
        width, height = width or DEFAULT_WIDTH, height or DEFAULT_HEIGHT
        filename = filename if filename and filename != '' else DEFAULT_ART_FILENAME
        charset = self.load_charset(charset or DEFAULT_CHARSET)
        palette = self.load_palette(palette or DEFAULT_PALETTE)
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
    
    def new_art_for_edit(self, filename, width=None, height=None):
        "Create a new Art and set it editable in Art Mode."
        art = self.new_art(filename, width, height)
        self.set_new_art_for_edit(art)
    
    def set_new_art_for_edit(self, art):
        "Makes given Art editable in Art Mode UI."
        self.art_loaded_for_edit.insert(0, art)
        renderable = TileRenderable(self, art)
        self.edit_renderables.insert(0, renderable)
        self.ui.set_active_art(art)
        self.camera.toggle_zoom_extents()
        art.set_unsaved_changes(True)
    
    def load_art_for_edit(self, filename):
        art = self.load_art(filename)
        if art in self.art_loaded_for_edit:
            self.ui.set_active_art(art)
            #self.ui.message_line.post_line('Art file %s already loaded' % filename)
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
    
    def get_converter_classes(self, base_class):
        "return a list of converter classes for importer/exporter selection"
        classes = []
        # on first load, documents dir may not be in import path
        if not self.documents_dir in sys.path:
            sys.path += [self.documents_dir]
        # read from application (builtins) and user documents dirs
        files = os.listdir(FORMATS_DIR)
        files += os.listdir(self.documents_dir + FORMATS_DIR)
        for filename in files:
            basename, ext = os.path.splitext(filename)
            if not ext.lower() == '.py':
                continue
            try:
                if basename in self.converter_modules:
                    m = importlib.reload(self.converter_modules[basename])
                else:
                    m = importlib.import_module('formats.%s' % basename)
                    self.converter_modules[basename] = m
            except Exception as e:
                self.log_import_exception(e, basename)
            for k,v in m.__dict__.items():
                if not type(v) is type:
                    continue
                if issubclass(v, base_class) and v is not base_class:
                    classes.append(v)
        return classes
    
    def get_importers(self):
        "Returns list of all ArtImporter subclasses found in formats/ dir."
        return self.get_converter_classes(ArtImporter)
    
    def get_exporters(self):
        "Returns list of all ArtExporter subclasses found in formats/ dir."
        return self.get_converter_classes(ArtExporter)
    
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
        # if editing is locked, don't even show Playscii name
        new_title = '%s - %s' % (APP_NAME, text) if self.can_edit else str(text)
        new_title = bytes(new_title, 'utf-8')
        sdl2.SDL_SetWindowTitle(self.window, new_title)
    
    def update_window_title(self):
        if self.game_mode:
            if self.gw and self.gw.game_dir:
                # if edit UI is up, show last loaded state
                if self.ui.game_menu_bar.visible:
                    title = self.gw.last_state_loaded
                # if not, show user-friendly game name
                else:
                    title = self.gw.game_title
            else:
                title = 'Game Mode'
            self.set_window_title(title)
            return
        if not self.ui or not self.ui.active_art:
            self.set_window_title()
            return
        # show message if converting
        if self.converter:
            title = self.img_convert_message % self.converter.image_filename
            self.set_window_title(title)
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
        self.grid = self.gw.grid
        # cursor might be hovering an object's art, undo preview viz
        self.cursor.undo_preview_edits()
        # display message on how to toggle game mode
        mode_bind = self.il.get_command_shortcut('toggle_game_mode')
        mode_bind = mode_bind.title()
        if self.can_edit:
            self.ui.message_line.post_line(self.game_mode_message % mode_bind, 10)
        self.al.resume_music()
        self.ui.menu_bar.close_active_menu()
        self.ui.menu_bar = self.ui.game_menu_bar
    
    def exit_game_mode(self):
        self.game_mode = False
        self.camera = self.art_camera
        self.grid = self.art_grid
        if self.ui.active_art:
            self.camera.set_for_art(self.ui.active_art)
        self.ui.message_line.post_line('', 1)
        self.update_window_title()
        self.al.pause_music()
        self.ui.menu_bar.close_active_menu()
        self.ui.menu_bar = self.ui.art_menu_bar
    
    def get_elapsed_time(self):
        return sdl2.timer.SDL_GetTicks()
    
    def main_loop(self):
        self.last_time = self.get_elapsed_time()
        while not self.should_quit:
            self.this_frame_start = self.get_elapsed_time()
            self.update()
            self.render()
            self.last_frame_end = self.get_elapsed_time()
            self.frames += 1
            self.sl.check_hot_reload()
            self.csl.check_hot_reload()
            self.pl.check_hot_reload()
            # determine FPS
            # alpha: lower = smoother
            alpha = 0.05
            dt = self.get_elapsed_time() - self.this_frame_start
            self.frame_time = alpha * dt + (1 - alpha) * self.frame_time
            self.fps = 1000 / self.frame_time
            # delay to maintain framerate, if uncapped
            if self.framerate != -1:
                delay = 1000 / self.framerate
                # subtract work time from delay to maintain framerate
                delay -= min(delay, dt)
                #print('frame time %s, delaying %sms to hit %s' % (self.frame_time, delay, self.framerate))
                sdl2.timer.SDL_Delay(int(delay))
        return 1
    
    def update(self):
        # start-of-frame stuff
        if self.game_mode:
            self.gw.frame_begin()
        else:
            # set all arts to "not updated"
            for art in self.art_loaded_for_edit:
                art.updated_this_tick = False
        # handle input - once per frame
        self.il.handle_input()
        # update game world & anything else that should happen on fixed timestep
        # avoid too many updates if eg machine straight up hangs
        if self.get_elapsed_time() - self.last_time > 1000:
            self.last_time = self.get_elapsed_time()
        updates = (self.get_elapsed_time() - self.last_time) / self.timestep
        for i in range(int(updates)):
            if self.game_mode:
                self.gw.pre_update()
                self.gw.update()
                self.gw.post_update()
            self.last_time += self.timestep
            self.updates += 1
        self.frame_update()
    
    def frame_update(self):
        "non-game updates that should happen once per frame"
        if self.converter:
            self.converter.update()
        # game world has its own once-a-frame updates, eg art/renderables
        if self.game_mode:
            self.gw.frame_update()
        else:
            for art in self.art_loaded_for_edit:
                art.update()
        if self.ui.active_art and not self.ui.console.visible and not self.game_mode and not self.ui.menu_bar in self.ui.hovered_elements and not self.ui.menu_bar.active_menu_name and not self.ui.active_dialog:
            self.cursor.update()
        self.camera.update()
        if not self.game_mode:
            self.grid.update()
            self.cursor.end_update()
        if self.ui.visible:
            self.ui.update()
        self.al.update()
    
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
            for renderable in self.edit_renderables:
                renderable.update()
            if self.show_bg_texture:
                self.bg_texture.render()
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
            if self.ui.active_art:
                self.grid.render()
            self.ui.select_tool.render_selections()
            if self.ui.active_art and not self.ui.console.visible and not self.ui.menu_bar in self.ui.hovered_elements and not self.ui.menu_bar.active_menu_name and not self.ui.active_dialog:
                self.cursor.render()
        self.debug_line_renderable.render()
        for r in self.img_renderables:
            r.render()
        # draw framebuffer to screen
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        self.fb.render()
        if self.ui.visible:
            self.ui.render()
        GL.glUseProgram(0)
        sdl2.SDL_GL_SwapWindow(self.window)
    
    def save_persistent_setting(self, setting_name, setting_value):
        # iterate over list backwards so we may safely remove from it
        for line in reversed(self.config_lines):
            if line.strip().startswith(setting_name):
                # ignore lines that contain setting name but don't set it
                if line.find('=') == -1:
                    continue
                # setting already found, remove this redundant line
                self.config_lines.remove(line)
        # get current value from top-level scope and write it to end of cfg
        self.config_lines += '%s = %s\n' % (setting_name, setting_value)
    
    def save_persistent_config(self):
        "write options we want to persist across sessions to config file"
        for name in self.persistent_setting_names:
            # get current setting value from top-level scope
            obj, member = self.persistent_setting_names[name]
            obj = self if obj == '' else getattr(self, obj)
            value = getattr(obj, member)
            self.save_persistent_setting(name, value)
    
    def restore_session(self):
        session_filename = self.config_dir + SESSION_FILENAME
        if not os.path.exists(session_filename):
            return
        # more recent arts should open later
        filenames = open(session_filename).readlines()
        filenames.reverse()
        for filename in filenames:
            self.load_art_for_edit(filename.strip())
    
    def save_session(self):
        if not self.can_edit:
            return
        # write all currently open art to a file
        session_file = open(self.config_dir + SESSION_FILENAME, 'w')
        for art in self.art_loaded_for_edit:
            # if an art has never been saved, don't bother storing it
            if not os.path.exists(art.filename):
                continue
            session_file.write(art.filename + '\n')
        session_file.close()
    
    def quit(self):
        if self.init_success:
            self.save_persistent_config()
            self.save_session()
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
        # write to config file
        cfg_file = open(self.config_dir + CONFIG_FILENAME, 'w')
        cfg_file.writelines(self.config_lines)
        cfg_file.close()
        self.log('Thank you for using Playscii!  <3')
    
    def open_local_url(self, url):
        "opens given local (this file system) URL in a cross-platform way"
        webbrowser.open('file://%s/%s' % (os.getcwd(), url))
    
    def open_help_docs(self):
        self.open_local_url(WEBSITE_HELP_URL)
    
    def open_website(self):
        webbrowser.open(WEBSITE_URL)
    
    def generate_docs(self):
        # fail gracefully if pdoc not found
        try:
            import pdoc
        except:
            self.log("pdoc module needed for documentation generation not found.")
            return
        # until better solution is found for "bloat from unchanged parent class
        # members", exclude certain classes from doc export
        blacklist = ['GameObjectRenderable', 'OnionTileRenderable']
        def docfilter(obj):
            if obj.name in blacklist:
                return False
            return True
        for module_name in AUTOGEN_DOC_MODULES:
            pdoc.import_module(module_name)
            html = pdoc.html(module_name, docfilter=docfilter)
            docfile = open(AUTOGEN_DOCS_PATH + module_name + '.html', 'w')
            docfile.write(html)
            docfile.close()
        self.log('Documentation generated successfully.')
        # open ToC page
        self.open_local_url(AUTOGEN_DOCS_PATH + AUTOGEN_DOC_TOC_PAGE)


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
        # issue #18: win documents path may not exist?!
        if not os.path.exists(documents_dir):
            os.mkdir(documents_dir)
    elif platform.system() == 'Darwin':
        documents_dir = os.path.expanduser('~') + DOCUMENTS_SUBDIR
    # assume anything that isn't Win/Mac is a UNIX
    else:
        # XDG spec doesn't cover any concept of a documents folder :[
        # if ~/Documents exists use that, else just use ~/Playscii
        documents_dir = os.path.expanduser('~')
        if os.path.exists(documents_dir + DOCUMENTS_SUBDIR):
            documents_dir += DOCUMENTS_SUBDIR
    # add Playscii/ to documents path
    documents_dir += '/%s/' % APP_NAME
    # create Playscii dir AND subdirs for user art, charsets etc if not present
    for subdir in ['', ART_DIR, CHARSET_DIR, PALETTE_DIR, FORMATS_DIR,
                   ART_SCRIPT_DIR, SCREENSHOT_DIR, TOP_GAME_DIR]:
        if not os.path.exists(documents_dir + subdir):
            os.mkdir(documents_dir + subdir)
    return config_dir, documents_dir, cache_dir

def get_version():
    return open(VERSION_FILENAME).readlines()[0].strip()


class Logger:
    """
    Minimal object for logging, starts very early so we can write to it even
    before Application has initialized.
    """
    def __init__(self, config_dir):
        self.lines = []
        config_dir, docs_dir, cache_dir = get_paths()
        # use line buffering (last lines should appear even in case of crash)
        bufsize = 1
        self.log_file = open(config_dir + LOG_FILENAME, 'w', bufsize)
    
    def log(self, new_line):
        self.log_file.write('%s\n' % new_line)
        self.lines.append(new_line)
        print(new_line)
    
    def close(self):
        self.log_file.close()


if __name__ == "__main__":
    # get paths for config file, later to be passed into Application
    config_dir, documents_dir, cache_dir = get_paths()
    # start logger even before Application has initialized so we can write to it
    # startup message: application and version #
    logger = Logger(config_dir)
    logger.log('%s v%s' % (APP_NAME, get_version()))
    # see if "autoplay this game" file exists and has anything in it
    autoplay_game = None
    if os.path.exists(AUTOPLAY_GAME_FILENAME):
        autoplay_game = open(AUTOPLAY_GAME_FILENAME).readlines()[0].strip()
    # load in config - may change above values and submodule class defaults
    cfg_filename = config_dir + CONFIG_FILENAME
    if os.path.exists(cfg_filename):
        logger.log('Loading config from %s...' % cfg_filename)
        # execute cfg line by line so we can continue past lines with errors.
        # this does mean that commenting out blocks with triple-quotes fails,
        # but that's not a good practice anyway.
        cfg_lines = open(cfg_filename).readlines()
        # compile a new cfg with any error lines stripped out
        new_cfg_lines = []
        for i,cfg_line in enumerate(cfg_lines):
            cfg_line = cfg_line.strip()
            try:
                exec(cfg_line)
                new_cfg_lines.append(cfg_line + '\n')
            except:
                # find line with "Error", ie the exception name, log that
                error_lines = traceback.format_exc().split('\n')
                error = '[an unknown error]'
                for el in error_lines:
                    if 'Error' in el:
                        error = el
                        break
                logger.log('  Removing line %s with %s' % (i, error))
        new_cfg = open(cfg_filename, 'w')
        new_cfg.writelines(new_cfg_lines)
        new_cfg.close()
        logger.log('Config loaded.')
    # if cfg file doesn't exist, copy a new one from playscii.cfg.default
    else:
        # snip first "this is a template" line
        default_data = open(CONFIG_TEMPLATE_FILENAME).readlines()[1:]
        new_cfg = open(cfg_filename, 'w')
        new_cfg.writelines(default_data)
        new_cfg.close()
        exec(''.join(default_data))
        logger.log('Created new config file %s' % cfg_filename)
    art_to_load, game_dir_to_load, state_to_load = None, None, None
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
                art_to_load = sys.argv[3]
        else:
            # else assume first arg is an art file to load in art mode
            art_to_load = sys.argv[1]
    app = Application(config_dir, documents_dir, cache_dir, logger,
                      art_to_load or DEFAULT_ART_FILENAME, game_dir_to_load,
                      state_to_load, autoplay_game)
    error = app.main_loop()
    app.quit()
    logger.close()
    sys.exit(error)
