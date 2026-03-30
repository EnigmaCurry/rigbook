# Build metadata — overwritten at build time (GitHub Actions or local PyInstaller).
# Local dev (non-PyInstaller) runs retain these defaults.
BUILD_ORIGIN_REPO = ""        # e.g. "EnigmaCurry/rigbook"
BUILD_GITHUB_ACTIONS = False  # True only when built by GitHub Actions
BUILD_GIT_SHA = ""            # Short git SHA at build time
