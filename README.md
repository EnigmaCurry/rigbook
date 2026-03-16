# Rigbook

A ham radio logbook web application. Log amateur radio contacts (QSOs)
with a local web UI, optionally connected to your radio via
[flrig](http://www.w1hkj.com/flrig-help/).

## Features

- Log QSO contacts with callsign, frequency, mode, signal reports, and
  more
- Auto-fill frequency and mode from your radio via flrig XMLRPC
- Click the VFO display in the header to change your radio's frequency
- Country and state autocomplete (all ISO countries and subdivisions)
- Mode autocomplete from your radio's supported modes
- Sortable log table with click-to-edit
- ADIF export and import
- Hunting page — browse active Parks on the Air activators, filter by
  mode/band, click to tune your radio
- SKCC and POTA park tracking
- All timestamps in UTC
- Light and dark themes (toggle in Settings)

## Requirements

- [Python](https://www.python.org/) 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- [Node.js](https://nodejs.org/) and npm (for building the frontend)
- [just](https://github.com/casey/just) (command runner, optional but recommended)
- [flrig](http://www.w1hkj.com/flrig-help/) (optional, for radio integration)

## Installation

```bash
git clone https://github.com/EnigmaCurry/rigbook.git
cd rigbook

# Install all dependencies
just deps

```

## Usage

```bash
# Build frontend and start the server
just run

```

Open http://localhost:8073 in your browser.

### First-time setup

1. Click the hamburger menu (top right) and go to **Settings**
2. Enter your callsign and grid square
3. If using flrig, configure the host and port (default: `localhost:12345`)
4. Click **Save**

### Logging contacts

1. Click **Add QSO** or go to the hamburger menu and select **Add QSO**
2. Fill in the required fields (marked with *)
3. If flrig is connected, frequency and mode auto-fill from your radio
4. Click **Log QSO** to save — the form stays open for the next contact
5. Click **Cancel** to return to the log view

### Editing contacts

Click any row in the log table to load it into the form for editing.
The URL updates to a deep link (`/#/log/123`) that you can bookmark or
share. Click **Save Edit** to save changes, **Delete** to remove, or
**Cancel** to discard.

### Sorting

Click any column header in the log table to sort. Click again to reverse
the sort order.

## Connecting to flrig

[flrig](http://www.w1hkj.com/flrig-help/) provides remote control of
your radio via XMLRPC.

1. Install and start flrig, connected to your radio
2. flrig listens on port 12345 by default
3. In Rigbook settings, set the **flrig Host** and **flrig Port** (defaults
   to `localhost:12345`)
4. The header will show a radio emoji with the current VFO frequency when
   connected:
   - **Connected:** shows the current frequency (click to change it)
   - **Disconnected:** shows a red X indicator
5. When adding a QSO, the frequency and mode fields auto-fill from flrig
6. The mode field autocompletes with modes your radio supports

If flrig is not running, everything still works — just enter frequency and
mode manually.

## Hunting

The **Hunting** page shows a live grid of active
[Parks on the Air](https://pota.app/) activators, sourced from the
pota.app API.

- Cards show the activator callsign, park name, frequency, mode, band,
  grid square, QSO count, and how long ago the spot was posted
- Filter by **mode** (CW, SSB, FT8, etc.) or **band** (20m, 40m, etc.)
- **Click a card** to tune your radio to that spot's frequency and mode
  (requires flrig)
- Spots refresh automatically every 30 seconds

## QRZ Callsign Lookup

If you have a [QRZ.com](https://www.qrz.com/) XML subscription, Rigbook
can auto-fill contact details when you enter a callsign.

1. Go to **Settings** and enter your **QRZ Password**
2. When you type a callsign in the Add QSO form, Rigbook looks it up
   after a short delay
3. From a blank form: fills name, QTH, state, country, and grid
4. From a hunting spot: only fills the operator's name (POTA data takes
   priority for location fields)
5. Results are cached for 24 hours — clear the cache from Settings

## SKCC

[SKCC](https://www.skccgroup.com/) member numbers are auto-populated
from the callsign. Rigbook fetches the SKCC member list and caches it
for 24 hours. No configuration needed.

## ADIF Export / Import

Rigbook supports the [ADIF](https://www.adif.org/) (Amateur Data
Interchange Format) standard for exchanging logbook data.

1. Go to **Export / Import** in the hamburger menu
2. **Export:** Click **Download ADIF** to download your entire log as a
   `.adi` file
3. **Import:** Click **Choose ADIF File** to import contacts from an
   existing `.adi` file

Frequency is automatically converted between KHz (Rigbook) and MHz (ADIF
standard).

## Data storage

The database is stored at `~/.local/rigbook/rigbook.db` (SQLite). It is
created automatically on first run.

## Development

```bash
# In one terminal, run the backend
just run

# In another terminal, run the frontend dev server with hot reload
just dev

# Lint and format
just check
just fix

# Run tests
just test
```

### Available just recipes

```
just              # Show all recipes
just deps         # Install all dependencies
just run          # Build frontend and start server
just build        # Build frontend only
just dev          # Frontend dev server with HMR
just test         # Run tests
just check        # Lint and format check
just fix          # Auto-fix lint and formatting
just config <CS>  # Set your callsign
just config-grid <GS>  # Set your grid square
just config-show  # Show current settings
```

## License

MIT
