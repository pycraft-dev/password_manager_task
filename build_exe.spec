# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для менеджера паролей (Windows)."""

from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "assets" / "icon.ico"), "assets"),
        (str(ROOT / "assets" / "icon.png"), "assets"),
        (str(ROOT / "translations.json"), "."),
        (str(ROOT / "VERSION"), "."),
    ],
    hiddenimports=["PIL._tkinter_finder", "customtkinter"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PasswordManager",
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
    icon=str(ROOT / "assets" / "icon.ico"),
)
