# 📻️ Rigbook

<img width="2502" height="1113" alt="image" src="https://github.com/user-attachments/assets/666965e7-0d12-48bc-9f8a-fc96dcd7a9c3" />


A ham radio logbook app. Log your QSOs with a local web UI, optionally
connected to your radio via [flrig](http://www.w1hkj.com/flrig-help/).

The current release of Rigbook is a feature-rich logbook for operators
engaged in POTA and/or SKCC activities.

**[Windows installation guide](https://wa7pge.com/static/rigbook/rigbook-windows-install.html)** *(thanks WA7PGE!)*

## Features

**Logging** — Log QSOs with callsign, frequency, mode, signal reports,
POTA park, SKCC number, and more. Auto-fill frequency/mode from flrig,
callsign details from QRZ, and SKCC numbers from the member list.
Country and state autocomplete with code normalization. Sortable,
column-reorderable, resizable log table with click-to-edit. Unsaved
changes are protected with field-level highlighting. Global search
across all fields.

**Radio control** — Connect to flrig for live VFO display, frequency
tuning, and mode cycling from the header bar. Band plan overlay in the
VFO editor. Simulated radio mode for testing without hardware.

**POTA** — Download and browse Parks on the Air data by
country/location. Park autocomplete on the QSO form with auto-fill of
grid, country, and state. Park detail pages with OpenStreetMap embed,
activation stats, and personal QSO history. My Parks view with award
tracking and an interactive map.

**Hunting** — Browse active POTA activators and nearby SKCC members on
CW in a single filterable view. Click to tune your radio and log a QSO.

**Spots** — Live RBN and HamAlert spot table with filtering by source,
band, mode, callsign, and SKCC membership. Closest spotter
distance/SNR, QRZ home location, POTA activator cross-reference,
worked-today greying, and saveable default filters. Interactive map
showing spotter-station-you triangles with animated flow lines.
Keyboard navigation with arrow keys.

**Notifications** — HamAlert spots create persistent in-app
notifications with optional desktop browser popups and modal alerts.
Real-time SSE push. Clickable callsigns and frequencies throughout.

**Band conditions** — Solar flux, sunspot number, A/K indices, X-ray
flux, geomagnetic field, solar wind, and HF/VHF propagation from
hamqsl.com.

**ADIF** — Export and import ADIF files with customizable filters,
duplicate detection, and a comment template system for structured fields
with round-trip safety.

**Multiple logbooks** — Each logbook is a separate SQLite database.
Switch between them with `--pick` mode or pass a name on the command
line. Copy a logbook file to use it as a template for new ones.

**Layout** — Dual-pane mode on wide screens with a draggable divider.
Light and dark themes. Keyboard shortcuts for all major actions.
Optional HTTP Basic Authentication.

## Install

Pre-built binaries are available from the
[Releases](https://github.com/EnigmaCurry/rigbook/releases) page for
Linux, macOS, and Windows.

```bash
# Download, make executable, and run:
chmod +x rigbook-linux-amd64
./rigbook-linux-amd64
```

Rigbook opens your browser automatically. Use `--no-browser` to disable.
The server binds to localhost only (no built-in authentication by
default). Set `RIGBOOK_HOST` and `RIGBOOK_PORT` to change.

**macOS:** Remove the quarantine attribute first:
`xattr -d com.apple.quarantine rigbook-macos-arm64`

### Container

```bash
mkdir -p ${HOME}/.local/rigbook && \
podman run --rm -it --name rigbook \
  --network=host \
  -v ${HOME}/.local/rigbook:/root/.local/rigbook:Z \
  ghcr.io/enigmacurry/rigbook:latest
```

### Environment variables

| Variable | Description |
|---|---|
| `RIGBOOK_DB` | Logbook name (e.g. `field-day` opens `~/.local/rigbook/field-day.db`) |
| `RIGBOOK_PICKER` | `true` to start in logbook picker mode |
| `RIGBOOK_NO_BROWSER` | `true` to skip opening the browser |
| `RIGBOOK_HOST` | Bind address (default: `127.0.0.1`) |
| `RIGBOOK_PORT` | Port (default: `8073`) |

## Getting started

1. Open http://localhost:8073
2. Go to **Settings** — enter your callsign and grid square
3. Optionally configure flrig, QRZ, RBN, and HamAlert connections
4. Click **+** to log your first QSO

## Development

```bash
git clone https://github.com/EnigmaCurry/rigbook.git
cd rigbook
just deps          # Install all dependencies
just run           # Build frontend and start server
just dev           # Frontend dev server with HMR
just test          # Run tests
just check         # Lint and format check
just fix           # Auto-fix lint and formatting
```

Data is stored in `~/.local/rigbook/` (SQLite). Automatic backups are
configurable in Settings.

## License

MIT
