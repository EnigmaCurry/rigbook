# Guidebook - Web Application Template
build_test_repo := "EnigmaCurry/guidebook-build-test"

# Show available recipes
@default:
    just --list

_check-uv:
    @command -v uv >/dev/null 2>&1 || { echo "Error: uv is not installed. Install it from https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }

_check-node:
    @command -v node >/dev/null 2>&1 || { echo "Error: node is not installed. Install it from https://nodejs.org/"; exit 1; }
    @command -v npm >/dev/null 2>&1 || { echo "Error: npm is not installed. It should come with node — reinstall from https://nodejs.org/"; exit 1; }

_check-curl:
    @command -v curl >/dev/null 2>&1 || { echo "Error: curl is not installed. Install it with your package manager (e.g. apt install curl)"; exit 1; }

# Install all dependencies
deps: _check-uv _check-node
    uv sync
    cd frontend && npm install

# Run the server (builds frontend first)
run *ARGS: _check-uv build-frontend
    uv run guidebook {{ ARGS }}

# Build the frontend (skips if sources unchanged)
build-frontend: _check-node
    @test -d frontend/node_modules || { echo "Error: frontend dependencies not installed. Run 'just deps' first."; exit 1; }
    @hash=$(find frontend/src frontend/index.html frontend/package.json frontend/vite.config.js -type f 2>/dev/null | sort | xargs cat | sha256sum | cut -d' ' -f1); \
    if [ -f .build-frontend.stamp ] && [ "$(cat .build-frontend.stamp)" = "$hash" ]; then \
        echo "frontend: up to date"; \
    else \
        cd frontend && npm run build && cd .. && echo "$hash" > .build-frontend.stamp; \
    fi

# Build a standalone binary with PyInstaller (skips if sources unchanged)
build-binary: _check-uv build-frontend
    @hash=$(find src/guidebook -type f -name '*.py' 2>/dev/null | sort | xargs cat | cat - guidebook.spec .build-frontend.stamp 2>/dev/null | sha256sum | cut -d' ' -f1); \
    if [ -f .build-binary.stamp ] && [ "$(cat .build-binary.stamp)" = "$hash" ]; then \
        echo "binary: up to date"; \
    else \
        uv sync --group build && uv run pyinstaller guidebook.spec && echo "$hash" > .build-binary.stamp; \
    fi

# Build everything (frontend + binary)
build: build-frontend build-binary

# Run frontend dev server with HMR
dev: _check-node
    @test -d frontend/node_modules || { echo "Error: frontend dependencies not installed. Run 'just deps' first."; exit 1; }
    cd frontend && npm run dev

# Run tests
test: _check-uv
    uv run pytest

# Lint and format check
check: _check-uv
    uv run ruff check .
    uv run ruff format --check .

# Auto-fix lint and formatting
fix: _check-uv
    uv run ruff check --fix .
    uv run ruff format .

# Show current settings
config-show: _check-curl
    @curl -s http://localhost:8073/api/settings | python -m json.tool

# Reset local dev branch to match remote
reset-dev:
    git fetch origin
    git checkout dev
    git reset --hard origin/dev

# Print the next .devN version for test releases (e.g. 0.1.0.dev3)
next-dev-version:
    #!/usr/bin/env bash
    set -euo pipefail
    BASE=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
    EXISTING=$(gh release list --repo {{ build_test_repo }} --json tagName --limit 100 --jq '.[].tagName' 2>/dev/null || true)
    MAX=-1
    for tag in $EXISTING; do
        if [[ "$tag" =~ ^v${BASE}\.dev([0-9]+)$ ]]; then
            N=${BASH_REMATCH[1]}
            (( N > MAX )) && MAX=$N
        fi
    done
    echo "${BASE}.dev$(( MAX + 1 ))"

# Remove build artifacts and stamp files
clean:
    rm -rf dist/ build/
    rm -f .build-*.stamp
    @echo "Build artifacts cleaned."
