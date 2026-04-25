# -*- mode: python ; coding: utf-8 -*-
import platform
import subprocess
from pathlib import Path

# Inject git SHA into _build_info.py for the build, always using current HEAD.
# The original file is restored after PyInstaller reads it so dev runs stay clean.
build_info_path = Path("src/guidebook/_build_info.py")
build_info_original = build_info_path.read_text()
try:
    sha = subprocess.check_output(
        ["git", "rev-parse", "--short=8", "HEAD"], text=True
    ).strip()
    import atexit
    build_info_path.write_text(
        build_info_original.replace('BUILD_GIT_SHA = ""', f'BUILD_GIT_SHA = "{sha}"')
    )
    atexit.register(build_info_path.write_text, build_info_original)
except Exception:
    pass

block_cipher = None
static_dir = Path("src/guidebook/static")

a = Analysis(
    ["build_entry.py"],
    pathex=[],
    binaries=[],
    datas=[(str(static_dir), "static")] if static_dir.is_dir() else [],
    hiddenimports=[
        "aiosqlite",
        "greenlet",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.sqlite.aiosqlite",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest"]
    + (["uvloop"] if platform.system() == "Windows" else []),
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="guidebook",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=platform.system() != "Windows",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="guidebook.ico" if Path("guidebook.ico").exists() else None,
)
