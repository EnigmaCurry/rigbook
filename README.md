# Guidebook

A web application template with FastAPI, SQLAlchemy, and Svelte.

## Features

- **Records**: Create, edit, and manage records with title, content, and tags
- **Multi-database**: Multiple projects with separate SQLite databases and a database picker
- **Themes**: Dark, light, amber, green, blue, and custom theme builder
- **Auto-updates**: Self-updating from GitHub releases
- **SQL Query**: Built-in SQL query interface for advanced data access
- **Notifications**: In-app notification system with SSE real-time updates
- **Auto-backup**: Automatic database backups on a configurable schedule
- **Cross-platform**: Runs on Linux, macOS, and Windows

## Quick Start

```bash
# Install dependencies
uv sync
cd frontend && npm install && cd ..

# Run
just run
```

Open http://localhost:8073 in your browser.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GUIDEBOOK_DB` | Database name to open | `guidebook` |
| `GUIDEBOOK_PICKER` | Enable database picker mode | `false` |
| `GUIDEBOOK_NO_BROWSER` | Skip opening browser | `false` |
| `GUIDEBOOK_NO_SHUTDOWN` | Disable shutdown endpoint | `false` |
| `GUIDEBOOK_HOST` | Bind address | `127.0.0.1` |
| `GUIDEBOOK_PORT` | Port | `8073` |
| `GUIDEBOOK_BROWSER_URL` | Override browser URL | |

## Development

```bash
# Frontend dev server with HMR
just dev

# Backend (in another terminal)
uv run guidebook --no-browser

# Lint and format
just check
just fix

# Tests
just test
```

## Building

```bash
# Build standalone binary
just build
```

## License

MIT
