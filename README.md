# 📻️ Rigbook

<img width="2412" height="1149" alt="image" src="https://github.com/user-attachments/assets/f7fe58fd-9c74-4c7e-8972-7cd305a80ea2" />


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

## Install

Pre-built binaries are available from the
[Releases](https://github.com/EnigmaCurry/rigbook/releases) page for
Linux, macOS, and Windows.

**Linux:**
```bash
chmod +x rigbook-linux-amd64
sudo mv rigbook-linux-amd64 /usr/local/bin/rigbook
```

**macOS:**
```bash
xattr -d com.apple.quarantine rigbook-macos-arm64
chmod +x rigbook-macos-arm64
sudo mv rigbook-macos-arm64 /usr/local/bin/rigbook
```

**Windows:**
```powershell
Move-Item rigbook-windows-amd64.exe "$env:LOCALAPPDATA\Microsoft\WindowsApps\rigbook.exe"
```

## Run

```bash
rigbook
```

Rigbook starts a background server and opens your browser automatically.
Run it again to reopen the browser. The same logbook is never opened
twice — if a newer version is installed, the old server is restarted
automatically.

Rigbook binds to `127.0.0.1` (localhost) with no authentication. It is
only accessible from your own machine.

```bash
rigbook --quit               # Stop the default logbook
```

Open additional logbooks on different ports:

```bash
rigbook field-day --port 9000
rigbook field-day --quit     # Stop it
```

Stop everything:

```bash
rigbook --quit-all
```

### All CLI options

```
rigbook                      # Open default logbook (background server + browser)
rigbook field-day             # Open a named logbook
rigbook --port 9000           # Use a specific port (default: 8073)
rigbook --list                # List running logbook processes
rigbook --quit                # Stop the default logbook
rigbook --quit field-day      # Stop a named logbook
rigbook --quit-all            # Stop all running logbooks
rigbook --server              # Run in the foreground (for debugging)
rigbook --server field-day    # Foreground server with a named logbook
rigbook --pick                # Foreground server with logbook picker UI
```

### Container

The container runs in foreground server mode (`--server`):

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
| `RIGBOOK_HOST` | Bind address (default: `127.0.0.1`) |
| `RIGBOOK_PORT` | Port (default: `8073`) |

## Getting started

1. Run `rigbook` — your browser opens automatically
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
