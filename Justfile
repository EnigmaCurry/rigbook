# Rigbook - Ham Radio Logbook

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
    uv run rigbook {{ ARGS }}

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
    @hash=$(find src/rigbook -type f -name '*.py' 2>/dev/null | sort | xargs cat | cat - rigbook.spec .build-frontend.stamp 2>/dev/null | sha256sum | cut -d' ' -f1); \
    if [ -f .build-binary.stamp ] && [ "$(cat .build-binary.stamp)" = "$hash" ]; then \
        echo "binary: up to date"; \
    else \
        uv sync --group build && uv run pyinstaller rigbook.spec && echo "$hash" > .build-binary.stamp; \
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

# Set your callsign
config callsign: _check-curl
    curl -s -X PUT http://localhost:8073/api/settings/my_callsign \
        -H 'Content-Type: application/json' \
        -d '{"value": "{{callsign}}"}'
    @echo

# Set your grid square
config-grid grid: _check-curl
    curl -s -X PUT http://localhost:8073/api/settings/my_grid \
        -H 'Content-Type: application/json' \
        -d '{"value": "{{grid}}"}'
    @echo

# Show current settings
config-show: _check-curl
    @curl -s http://localhost:8073/api/settings | python -m json.tool

# Reset local dev branch to match remote
reset-dev:
    git fetch origin
    git checkout dev
    git reset --hard origin/dev

# Remove build artifacts and stamp files
clean:
    rm -rf dist/ build/
    rm -f .build-*.stamp
    @echo "Build artifacts cleaned."

