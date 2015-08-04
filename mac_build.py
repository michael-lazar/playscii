"""
py2app build script for playscii

Requirements:
 - env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.4.2
 - py2app 0.9+
  - has some bugs still, needs manual build or manual edits?

Usage:
    python mac_build.py py2app --packages=PIL,OpenGL,ctypes,logging
"""
from setuptools import setup

APP = ['playscii.py']

# Extra items to add to dist/HelloAppStore.app/Contents/Resources
DATA_FILES = []
OPTIONS = {
    # 'use_pythonpath': True,
    # 'optimize': 2,
    # 'compressed': True,
    'argv_emulation': True,
    'iconfile': 'ui/logo.png',
    'plist': 'Info.plist',
    'includes': ['ctypes', 'logging',],
    # 'packages': ['PIL', 'OpenGL', 'numpy',],
    'resources': [
        'playscii.cfg.default',
        'binds.cfg.default',
        'ui',
        'shaders',
        'scripts',
        'palettes',
        'games',
        'docs',
        'charsets',
        'art'
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
