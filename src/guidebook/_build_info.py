# Build metadata — overwritten at build time (GitHub Actions or local PyInstaller).
# Local dev (non-PyInstaller) runs retain these defaults.
BUILD_ORIGIN_REPO = ""  # e.g. "EnigmaCurry/guidebook"
BUILD_GITHUB_ACTIONS = False  # True only when built by GitHub Actions
BUILD_GIT_SHA = ""  # Short git SHA at build time


def _detect_git_sha() -> str:
    """Get git SHA from the source checkout when not running a frozen binary."""
    import sys

    if getattr(sys, "frozen", False) or BUILD_GIT_SHA:
        return BUILD_GIT_SHA
    try:
        import os
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=os.path.dirname(__file__) or None,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


GIT_SHA = _detect_git_sha() or BUILD_GIT_SHA
