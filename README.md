# 📻️ Rigbook
<img width="3934" height="2080" alt="image" src="https://github.com/user-attachments/assets/4072cda0-2e87-48de-a16e-e99c8b889e1c" />


A ham radio logbook app. Log your QSOs with a local web UI, optionally
controlling your radio via [flrig](http://www.w1hkj.org/flrig-help).

The current release of Rigbook is a feature-rich logbook for operators
engaged in POTA and/or SKCC activities.

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
The logbook picker is shown by default on startup; pass a name on the
command line to open a specific logbook directly. Switch between
logbooks from the header link.

**Layout** — Dual-pane mode on wide screens with a draggable divider.
Light and dark themes. Keyboard shortcuts for all major actions.

## Install

Pre-built binaries are available from the
[Releases](https://github.com/EnigmaCurry/rigbook/releases) page.
Run the binary to start the server on localhost, and the page will open in your web browser automatically.

### Linux

```bash
# Download the binary for your architecture (amd64 or arm64):
wget https://github.com/EnigmaCurry/rigbook/releases/latest/download/rigbook-linux-amd64
chmod +x rigbook-linux-amd64
./rigbook-linux-amd64
```

### macOS

Download `rigbook-macos-universal.pkg` from the
[Releases](https://github.com/EnigmaCurry/rigbook/releases) page.
This package supports both Apple Silicon and Intel Macs.

Before opening the installer, remove the quarantine attribute (the app
is not signed with an Apple developer certificate):

```bash
xattr -cr ~/Downloads/rigbook-macos-universal.pkg
```

Then open the `.pkg` file and follow the installer prompts to install
Rigbook into `/Applications`. It launches as an app in your web
browser (no terminal window).

> The release also includes standalone `rigbook-macos-arm64` and
> `rigbook-macos-intel` binaries. These are used by the built-in
> updater and can also be run directly from the command line if you
> prefer.

### Windows

Download `rigbook-windows-amd64.exe` from the
[Releases](https://github.com/EnigmaCurry/rigbook/releases) page and
run it. See the **[Windows installation
guide](https://wa7pge.com/static/rigbook/rigbook-windows-install.html)**
*(thanks WA7PGE!)* for detailed instructions.

### Android (Termux)

See [TERMUX.md](TERMUX.md) for instructions on running Rigbook on Android via Termux.

### Container

```bash
mkdir -p ${HOME}/.local/rigbook && \
podman run --rm -it --name rigbook \
  --network=host \
  -v ${HOME}/.local/rigbook:/root/.local/rigbook:Z \
  ghcr.io/enigmacurry/rigbook:latest
```

### Updating

Rigbook has a built-in self-updater. Go to **Settings → Updates** and
enable "Check for new Rigbook releases on GitHub." When a new version
is available, a notification appears with an **Apply Update** button.
Rigbook downloads the new binary, swaps it in place, and restarts
automatically.

The updater works with official builds from GitHub Releases. If the
binary directory is not writable, Rigbook shows a download link
instead.

### Environment variables

| Variable | Description |
|---|---|
| `RIGBOOK_DB` | Logbook name (e.g. `field-day` opens `~/.local/rigbook/field-day.db`) |
| `RIGBOOK_PICKER` | `true` to start in logbook picker mode |
| `RIGBOOK_NO_BROWSER` | `true` to skip opening the browser |
| `RIGBOOK_NO_SHUTDOWN` | `true` to disable the shutdown endpoint and auto-shutdown |
| `RIGBOOK_HOST` | Bind address (default: `127.0.0.1`) |
| `RIGBOOK_PORT` | Port (default: `8073`) |
| `RIGBOOK_BROWSER_URL` | Override the URL opened in the browser (e.g. `https://rigbook.local`) |

## Getting started

1. Open http://localhost:8073
2. The welcome screen will guide you through entering your callsign and grid square
3. Optionally configure flrig, QRZ, RBN, and HamAlert connections in **Settings**
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
