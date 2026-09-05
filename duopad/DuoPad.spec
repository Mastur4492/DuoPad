# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('duopad_neon.ico', '.'), ('duopad_icon.png', '.')]
binaries = [('C:/Users/mo.mastur/anaconda3/Library/bin/tcl86t.dll', '.'), ('C:/Users/mo.mastur/anaconda3/Library/bin/tk86t.dll', '.'), ('C:/Users/mo.mastur/anaconda3/Library/bin/ffi.dll', '.')]
hiddenimports = ['engineio.async_drivers.aiohttp']
tmp_ret = collect_all('vgamepad')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['duopad_hub.py'],
    pathex=['C:/Users/mo.mastur/anaconda3/Library/bin', 'C:/Users/mo.mastur/anaconda3/DLLs'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PIL', 'Pillow', 'pytest', 'numpy', 'pygments', 'scipy', 'pandas'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DuoPad',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['duopad_neon.ico'],
)
