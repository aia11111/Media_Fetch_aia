# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

customtkinter_datas = collect_data_files('customtkinter')
app_datas = [
    ('VERSION', '.'),
    ('assets/VideoDownloader.ico', 'assets'),
    ('assets/VideoDownloader.png', 'assets'),
]
gallery_dl_datas = collect_data_files('gallery_dl')
gallery_dl_hiddenimports = collect_submodules('gallery_dl')


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=customtkinter_datas + app_datas + gallery_dl_datas,
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/VideoDownloader.ico',
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
