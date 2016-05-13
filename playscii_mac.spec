# -*- mode: python -*-

block_cipher = None

include_files = [
    ('./README.md', '.'),
    ('license.txt', '.'),
    ('*.cfg.default', '.'),
    ('version', '.'),
    ('art', 'art'),
    ('charsets', 'charsets'),
    ('palettes', 'palettes'),
    ('scripts', 'scripts'),
    ('shaders', 'shaders'),
    ('shaders', 'shaders'),
    ('games', 'games'),
    ('ui/*.png', 'ui')
]

include_bins = [
    ('/usr/local/Cellar/sdl2/2.0.4/lib/libSDL2-2.0.0.dylib', '.'),
    ('/usr/local/Cellar/sdl2_mixer/2.0.1/lib/libSDL2_mixer-2.0.0.dylib', '.'),
    ('/usr/local/Cellar/flac/1.3.1/lib/libFLAC.8.dylib', '.'),
    ('/usr/local/Cellar/libmikmod/3.3.8/lib/libmikmod.3.dylib', '.'),
    ('/usr/local/Cellar/libmodplug/0.8.8.5/lib/libmodplug.1.dylib', '.'),
    ('/usr/local/Cellar/libogg/1.3.2/lib/libogg.0.dylib', '.'),
    ('/usr/local/Cellar/libvorbis/1.3.5/lib/libvorbis.0.dylib', '.'),
    ('/usr/local/Cellar/libvorbis/1.3.5/lib/libvorbisfile.3.dylib', '.'),
    ('/usr/local/Cellar/smpeg2/2.0.0/lib/libsmpeg2-2.0.0.dylib', '.')
]

a = Analysis(['playscii.py'],
             pathex=['./'],
             binaries=include_bins,
             datas=include_files,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='playscii',
          debug=False,
          strip=None,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='playscii')
app = BUNDLE(coll,
             name='Playscii.app',
             icon='ui/playscii.icns',
             bundle_identifier='net.jplebreton.playscii')
