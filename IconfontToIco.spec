# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller IconfontToIco.spec

a = Analysis(
    ["src/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("ai_icon", "ai_icon"),
        ("output_icons/draw.ico", "output_icons"),
    ],
    hiddenimports=["fitz"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pandas", "numpy", "openpyxl", "matplotlib", "scipy"],
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
    name="IconfontToIco",
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
    icon="output_icons/draw.ico",
)
