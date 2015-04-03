# py2exe windows build script
from distutils.core import setup
import py2exe

data_files = [
#    'playscii.cfg',
]

includes = ['ctypes', 'logging']
# in addition to core python stuff, includes list should include any
# modules that game scripts need, eg GameObject
includes += ['game_object']

excludes = [
    # exclude OpenGL then manually copy from python install dir's sitepackages/
    # (see build.bat)
    'OpenGL',
    # random other stuff we don't seem to need
    'Tkconstants','Tkinter','tcl',
    '_imagingtk', 'PIL._imagingtk', 'ImageTk', 'PIL.ImageTk', 'FixTk',
    'ssl',
]

setup(
    windows = ['playscii.py'],
    data_files = [('', data_files)],
    options = {
        'py2exe': {
            'optimize': 2,
            'bundle_files': 2,
            'compressed': True,
            'includes': includes,
            'excludes': excludes,
            }
        }
)
