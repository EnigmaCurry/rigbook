"""Self-update: download latest release binary and restart in-place."""

import logging
import os
import platform
import stat
import subprocess
import sys
import tempfile
import threading
import time

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from importlib.metadata import version

router = APIRouter(prefix="/api/update", tags=["update"])

logger = logging.getLogger("rigbook.update")

GITHUB_REPO = os.environ.get("RIGBOOK_GITHUB_REPO", "EnigmaCurry/rigbook")


def _spawn_and_exit(exe_path: str) -> None:
    """Launch the new binary as a detached process and exit.

    os.execv won't work for PyInstaller binaries because it replaces the
    process while the old temp dir (/tmp/_MEI...) is being torn down,
    causing the new process to fail finding shared libraries.  Instead,
    spawn a fully independent child and then shut down cleanly.
    """

    def _do():
        time.sleep(1)  # let the HTTP response flush
        env = os.environ.copy()
        # Clear all PyInstaller env vars so the new process unpacks fresh
        for key in list(env):
            if key.startswith("_MEI") or key.startswith("_PYI"):
                env.pop(key)
        # Remove old temp dir from LD_LIBRARY_PATH / DYLD_LIBRARY_PATH
        old_meipass = getattr(sys, "_MEIPASS", "")
        for ldvar in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
            if ldvar in env and old_meipass:
                paths = [p for p in env[ldvar].split(os.pathsep) if not p.startswith(old_meipass)]
                if paths:
                    env[ldvar] = os.pathsep.join(paths)
                else:
                    env.pop(ldvar)
        subprocess.Popen(
            [exe_path] + sys.argv[1:],
            env=env,
            start_new_session=True,
        )
        logger.info("Spawned new process, shutting down...")
        os._exit(0)

    threading.Thread(target=_do, daemon=True).start()


def _asset_name() -> str:
    """Return the GitHub release asset name for this platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        arch = "arm64" if machine in ("aarch64", "arm64") else "amd64"
        return f"rigbook-linux-{arch}"
    elif system == "darwin":
        return "rigbook-macos-arm64"
    elif system == "windows":
        arch = "amd64"
        return f"rigbook-windows-{arch}.exe"
    else:
        raise RuntimeError(f"Unsupported platform: {system} {machine}")


def _is_github_binary() -> bool:
    """Check if the running binary looks like a GitHub release build.

    GitHub release assets are named like rigbook-linux-amd64, rigbook-macos-arm64,
    rigbook-windows-amd64.exe.  A locally-built PyInstaller binary is just 'rigbook'.
    """
    if not getattr(sys, "frozen", False):
        return False
    name = os.path.basename(sys.executable)
    # Strip .exe for comparison
    stem = name.removesuffix(".exe")
    return stem.startswith("rigbook-") and stem.count("-") >= 2


def _current_executable() -> str:
    """Return the path to the currently running binary."""
    if getattr(sys, "frozen", False) and _is_github_binary():
        return sys.executable
    raise RuntimeError("Self-update is only supported for official GitHub release binaries")


@router.get("/platform")
async def get_platform_info():
    """Return platform info and whether self-update is supported."""
    frozen = getattr(sys, "frozen", False)
    github_binary = _is_github_binary()
    try:
        asset = _asset_name()
    except RuntimeError:
        asset = None
    return {
        "frozen": frozen,
        "supported": frozen and github_binary and asset is not None,
        "platform": platform.system().lower(),
        "arch": platform.machine().lower(),
        "asset": asset,
        "executable": sys.executable if frozen else None,
    }


@router.post("/apply")
async def apply_update():
    """Download the latest release binary and restart."""
    if not getattr(sys, "frozen", False) or not _is_github_binary():
        raise HTTPException(
            400, "Self-update only supported for official GitHub release binaries"
        )

    current = version("rigbook")
    asset_name = _asset_name()
    exe_path = _current_executable()

    # Fetch latest release info
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers={"Accept": "application/vnd.github+json"},
                timeout=10,
            )
            resp.raise_for_status()
            release = resp.json()
    except Exception as e:
        logger.error("Failed to fetch release info: %s", e)
        raise HTTPException(502, "Failed to fetch release info from GitHub")

    latest = release["tag_name"].lstrip("v")
    if latest == current:
        return JSONResponse({"status": "up_to_date", "version": current})

    # Find the asset download URL
    download_url = None
    for asset in release.get("assets", []):
        if asset["name"] == asset_name:
            download_url = asset["browser_download_url"]
            break

    if not download_url:
        raise HTTPException(
            404,
            f"No binary found for this platform ({asset_name}) in release v{latest}",
        )

    # Download to a temp file next to the current executable
    exe_dir = os.path.dirname(exe_path)
    logger.info("Downloading %s from v%s ...", asset_name, latest)

    try:
        fd, tmp_path = tempfile.mkstemp(dir=exe_dir, prefix="rigbook-update-")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            async with client.stream("GET", download_url, timeout=120) as stream:
                stream.raise_for_status()
                for chunk in stream.iter_raw():
                    os.write(fd, chunk)
        os.close(fd)
    except Exception as e:
        logger.error("Download failed: %s", e)
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise HTTPException(502, f"Failed to download update: {e}")

    # Make executable on unix
    if platform.system() != "Windows":
        os.chmod(tmp_path, os.stat(tmp_path).st_mode | stat.S_IXUSR | stat.S_IXGRP)

    # Swap binaries — rename running binary out of the way first.
    # On both Linux and Windows, overwriting a running binary fails
    # (ETXTBSY on Linux, lock on Windows).
    backup_path = exe_path + ".backup"
    try:
        if os.path.exists(backup_path):
            os.unlink(backup_path)

        os.rename(exe_path, backup_path)
        os.rename(tmp_path, exe_path)
    except Exception as e:
        logger.error("Failed to swap binary: %s", e)
        # Try to restore from backup
        try:
            if not os.path.exists(exe_path) and os.path.exists(backup_path):
                os.rename(backup_path, exe_path)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise HTTPException(500, f"Failed to install update: {e}")

    logger.info("Update installed: v%s -> v%s, restarting...", current, latest)
    _spawn_and_exit(exe_path)

    return {
        "status": "restarting",
        "old_version": current,
        "new_version": latest,
    }


