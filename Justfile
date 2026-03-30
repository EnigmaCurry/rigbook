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
run *ARGS: _check-uv build
    uv run rigbook {{ ARGS }}

# Build the frontend
build: _check-node
    @test -d frontend/node_modules || { echo "Error: frontend dependencies not installed. Run 'just deps' first."; exit 1; }
    cd frontend && npm run build

# Build a standalone binary with PyInstaller
build-binary: _check-uv build
    uv sync --group build
    uv run pyinstaller rigbook.spec

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

# Delete the database
[confirm("This will delete ~/.local/rigbook/rigbook.db. Are you sure? (y/N)")]
clean:
    rm -f ~/.local/rigbook/rigbook.db
    @echo "Database deleted."
