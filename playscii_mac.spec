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
    ('/usr/local/Cellar/sdl2/2.0.3/lib/libSDL2-2.0.0.dylib', '.'),
    ('/usr/local/Cellar/sdl2_mixer/2.0.0/lib/libSDL2_mixer-2.0.0.dylib', '.')
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