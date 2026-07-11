# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller gimbo.spec
# Produces a folder at dist/Gimbo/ containing Gimbo(.exe) plus everything
# it needs (Qt plugins, assets/, schema.sql). Ship the whole folder.

block_cipher = None

added_files = [
    ("assets", "assets"),
    ("schema.sql", "."),
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Gimbo",
    debug=False,
    strip=False,
    upx=True,
    console=False,      # no terminal window on Windows
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Gimbo",
)
