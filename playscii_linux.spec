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
    ('artscripts', 'artscripts'),
    ('shaders', 'shaders'),
    ('games', 'games'),
    ('ui/*.png', 'ui'),
    ('docs/html/*.*', 'docs/html'),
    ('docs/html/generated/pdoc_toc.html', 'docs/html/generated'),
]

a = Analysis(['playscii.py'],
             pathex=['./'],
             binaries=None,
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
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='playscii')
