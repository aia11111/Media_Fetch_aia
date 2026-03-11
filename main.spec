# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

customtkinter_datas = [
    ('c:/users/zipsh/appdata/local/programs/python/python314/lib/site-packages/customtkinter', 'customtkinter/'),
]
gallery_dl_datas = collect_data_files('gallery_dl')
gallery_dl_hiddenimports = collect_submodules('gallery_dl')


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=customtkinter_datas + gallery_dl_datas,
    hiddenimports=['gui', 'downloader', *gallery_dl_hiddenimports],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)
