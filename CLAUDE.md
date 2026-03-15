# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Rigbook is a ham radio logbook web application. It provides a local FastAPI backend serving a Svelte frontend for logging amateur radio contacts (QSOs). It integrates with flrig via XMLRPC to auto-populate radio state (frequency, mode) into the log form.

## Tech Stack

- **Backend**: Python, FastAPI, SQLite (via aiosqlite/SQLAlchemy), uvicorn
- **Frontend**: Svelte (built and served as static files by FastAPI)
- **Tooling**: uv (package manager), ruff (linter/formatter)
- **Radio integration**: flrig XMLRPC interface

## Project Structure

```
rigbook/
├── src/rigbook/          # Python package
│   ├── __init__.py
│   ├── main.py           # FastAPI app, uvicorn entry point
│   ├── db.py             # SQLite database (models, connection)
│   ├── routes/           # API route modules
│   │   ├── contacts.py   # CRUD for QSO log entries
│   │   └── settings.py   # App settings (callsign, grid)
│   └── flrig.py          # XMLRPC client for flrig
├── frontend/             # Svelte app
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── pyproject.toml
└── CLAUDE.md
```

## Data Storage

Database and config stored in `~/.local/rigbook/rigbook.db` (XDG-compatible). Created automatically on first run.

## Key Commands

```bash
# Setup
uv sync                          # Install Python dependencies
cd frontend && npm install        # Install frontend dependencies

# Development
uv run rigbook                    # Run the server
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

### QSO Contact Fields
- `call` — their callsign (required)
- `freq` — frequency in MHz (auto-filled from flrig, not user-editable)
- `mode` — operating mode (auto-filled from flrig)
- `rst_sent` / `rst_recv` — signal reports
- `pota_park` — POTA park reference
- `name` — operator name
- `qth` — city/location
- `state` / `country` — location details
- `grid` — Maidenhead grid square
- `comments` / `notes` — free text
- `timestamp` — UTC datetime of contact

### Settings
- `my_callsign` — operator's own callsign
- `my_grid` — operator's own grid square

## Architecture Notes

- The Svelte frontend is built to static files and served by FastAPI's `StaticFiles` mount at `/`. API routes are under `/api/`.
- flrig integration is best-effort: if flrig is not running, the frequency/mode fields are left blank and the form still works. The frontend polls a `/api/flrig/status` endpoint to get current VFO state.
- All timestamps stored in UTC.
