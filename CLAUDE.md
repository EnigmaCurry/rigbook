# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Guidebook is a web application template providing a local FastAPI backend serving a Svelte frontend. It includes multi-database management, theme system, auto-updates, and a notification system.

## Tech Stack

- **Backend**: Python, FastAPI, SQLite (via aiosqlite/SQLAlchemy), uvicorn
- **Frontend**: Svelte (built and served as static files by FastAPI)
- **Tooling**: uv (package manager), ruff (linter/formatter)

## Project Structure

```
guidebook/
├── src/guidebook/        # Python package
│   ├── __init__.py
│   ├── main.py           # FastAPI app, uvicorn entry point
│   ├── db.py             # SQLite database (models, connection)
│   ├── sse.py            # Server-Sent Events
│   └── routes/           # API route modules
│       ├── records.py    # CRUD for records
│       ├── settings.py   # App settings
│       ├── logbooks.py   # Database management
│       ├── notifications.py
│       ├── query.py      # SQL query interface
│       ├── global_settings.py
│       └── update.py     # Self-update
├── frontend/             # Svelte app
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── pyproject.toml
└── CLAUDE.md
```

## Data Storage

Database and config stored in `~/.local/guidebook/` (XDG-compatible). Created automatically on first run.

## Key Commands

```bash
# Setup
uv sync                          # Install Python dependencies
cd frontend && npm install        # Install frontend dependencies

# Development
uv run guidebook                  # Run the server
cd frontend && npm run dev        # Frontend dev server (with HMR proxy to backend)
cd frontend && npm run build      # Build frontend for production

# Code quality
uv run ruff check .               # Lint
uv run ruff format .              # Format
uv run ruff check --fix .         # Auto-fix lint issues
uv run pytest                     # Run tests
uv run pytest tests/test_foo.py::test_name  # Single test
```

## Data Model

### Record Fields
- `title` — record title (required)
- `content` — record content (optional)
- `tags` — comma-separated tags (optional)
- `timestamp` — UTC datetime
- `updated_at` — last modification time

### Settings
- Per-project and global settings with fallback
- Theme customization (presets and custom)

## Architecture Notes

- The Svelte frontend is built to static files and served by FastAPI's `StaticFiles` mount at `/`. API routes are under `/api/`.
- All timestamps stored in UTC.
- Multi-database system: one `.db` per project + shared `__global.db`.
- Auto-update mechanism downloads from GitHub releases.
