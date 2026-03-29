# 📻️ Rigbook
<img width="3303" height="2080" alt="image" src="https://github.com/user-attachments/assets/9f40f57e-e55d-4220-93f2-83fd14028043" />


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
Switch between them with `--pick` mode or pass a name on the command
line. Copy a logbook file to use it as a template for new ones.

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

```bash
wget https://github.com/EnigmaCurry/rigbook/releases/latest/download/rigbook-macos-arm64
chmod +x rigbook-macos-arm64
# Remove the quarantine attribute:
xattr -d com.apple.quarantine rigbook-macos-arm64
./rigbook-macos-arm64
```

### Windows

Download `rigbook-windows-amd64.exe` from the
[Releases](https://github.com/EnigmaCurry/rigbook/releases) page and
run it. See the **[Windows installation
guide](https://wa7pge.com/static/rigbook/rigbook-windows-install.html)**
*(thanks WA7PGE!)* for detailed instructions.

----
----

### Android (Termux)

Experimentally, Rigbook runs on Android phones via [Termux](https://termux.dev) using
the pre-built Linux ARM64 binary inside a Debian proot environment.
The web UI is usable on phone touch screens, but Rigbook is primarily
designed as a desktop application.

```bash
# Install Termux from F-Droid, then:
pkg install proot-distro
proot-distro install debian
proot-distro login debian

# Inside Debian:
apt update && apt install -y wget
wget https://github.com/EnigmaCurry/rigbook/releases/latest/download/rigbook-linux-arm64
chmod +x rigbook-linux-arm64
```

**Important:** Android suspends background apps aggressively. Before
starting rigbook, acquire a wake lock so Termux stays alive when you
switch to the browser:

```bash
# In the debian proot (proot-distro login debian)
termux-wake-lock
./rigbook-linux-arm64
```

While termux is still running in the background, open your Android web browser and go to `http://127.0.0.1:8073` to access mobile Rigbook:


<p align="center">
  <img src="https://github.com/user-attachments/assets/e74d8446-8cfb-400d-a761-ee841b5c30c3" alt="Rigbook running on Android Pixel phone via Termux in Chrome browser" width="400"><br>
  <em>Rigbook running on Android Pixel phone via Termux in Chrome browser</em>
</p>


You can also use your phone as just the server, and access Rigbook from 
another computer's browser on the same network.  This gives you the full
desktop experience while you keep Rigbook running in your pocket. 
Set `RIGBOOK_HOST=0.0.0.0` before starting rigbook to listen on all interfaces:

```bash
# Warning: this allows any device to access your phone on port 8073 :
export RIGBOOK_HOST=0.0.0.0
termux-wake-lock
./rigbook-linux-arm64
```

Then open `http://<phone-ip>:8073` from any browser on the LAN.

**Warning:** Rigbook has no authentication or encryption — only do
this on trusted networks.

---
---

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
