# -*- mode: python ; coding: utf-8 -*-
import platform
import subprocess
from pathlib import Path

# Inject git SHA into _build_info.py if not already set (e.g. local builds)
build_info_path = Path("src/rigbook/_build_info.py")
build_info = build_info_path.read_text()
if 'BUILD_GIT_SHA = ""' in build_info:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short=8", "HEAD"], text=True
        ).strip()
        build_info = build_info.replace('BUILD_GIT_SHA = ""', f'BUILD_GIT_SHA = "{sha}"')
        build_info_path.write_text(build_info)
    except Exception:
        pass

block_cipher = None
static_dir = Path("src/rigbook/static")

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
    collect_data=["pycountry", "pyadif_file"],
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="rigbook",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
