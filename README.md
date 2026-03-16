# Rigbook

A ham radio logbook web application. Log amateur radio contacts (QSOs)
with a local web UI, optionally connected to your radio via
[flrig](http://www.w1hkj.com/flrig-help/).

## Features

- Log QSO contacts with callsign, frequency, mode, signal reports, and
  more
- Auto-fill frequency and mode from your radio via flrig XMLRPC
- Everything in the header is clickable: **Rigbook** goes to Hunting,
  **callsign** opens Logbook, **VFO frequency** opens the band plan tuner,
  **mode** cycles radio modes, **UTC clock** copies the timestamp to
  clipboard, and **+** adds a new QSO
- Keyboard shortcuts: `/` search, `N` new QSO, `H` hunting, `L` logbook,
  `T` tune radio, `M` cycle mode, `?` about, `Esc` close
- Country and state autocomplete (all ISO countries and subdivisions),
  with automatic normalization of codes (US → United States, UT → Utah)
- Mode autocomplete from your radio's supported modes
- POTA park autocomplete — search by reference, name, location, or grid
  with auto-fill of country, state, and grid square
- Parks browser — download and cache park data by country, browse parks
  in a tree by country/location, view park details with OpenStreetMap
  embed, personal QSO count, and award emojis
- Sortable log table with click-to-edit
- ADIF export and import
- Hunting page — browse active Parks on the Air activators, filter by
  mode/band, click to tune your radio (spots cached server-side for 30s)
- QRZ callsign lookup with connection test button in Settings
- SKCC member number auto-lookup
- All timestamps in UTC with 24-hour format
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

1. Click **+** or go to the hamburger menu and select **Add QSO**
2. Enter a callsign — the date and time auto-fill when you tab out
3. If flrig is connected, frequency and mode auto-fill from your radio
4. QRZ auto-fills name, QTH, state, country, and grid (if configured)
5. Type a POTA park reference or name to autocomplete from cached parks
6. Click the clock button (🕓) to update the timestamp to now
7. Click **Log QSO** to save — the form clears for the next contact
8. Click **Cancel** to return to the previous view

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

## POTA Parks

The **Parks** page lets you download and browse
[Parks on the Air](https://pota.app/) park data.

### Downloading parks

1. Go to **Parks** → **Download** tab
2. Select the countries you want to cache (use the filter to find them)
3. Click **Update Parks** — progress streams as each location is fetched
4. Park data is cached in SQLite with a 24-hour TTL

### Browsing parks

- **By Country** tab shows a tree: expand a country to see its
  locations, expand a location to see its parks
- Click any park to view its detail page with name, location, grid,
  coordinates, activation stats, an OpenStreetMap embed, and your
  personal QSO count with award emojis (🥇 1, 🥈 2, ⭐ 5, 🌟 10,
  💎 15, 🏆 20+)
- Park detail pages are deep-linkable (`/#/parks/park/US-0008`)

### Park autocomplete on QSO form

When adding a QSO, the POTA Park field autocompletes from cached parks.
Type a reference (e.g. `US1024` or `US-1024`), park name, location, or
grid square to search. Selecting a park auto-fills the grid, country,
and state fields. The park name appears as a clickable link that opens
a detail overlay without leaving the form.

## QRZ Callsign Lookup

If you have a [QRZ.com](https://www.qrz.com/) XML subscription, Rigbook
can auto-fill contact details when you enter a callsign.

1. Go to **Settings**, enter your callsign first, then set your
   **QRZ Password**
2. Click **Test QRZ Connection** to verify it works
3. When you type a callsign in the Add QSO form, Rigbook looks it up
   on blur
4. From a blank form: fills name, QTH, state, country, and grid
5. From a hunting spot: only fills the operator's name (POTA data takes
   priority for location fields)
6. Country codes are normalized to full names (US → United States)
7. State abbreviations are normalized to full names (UT → Utah)
8. Results are cached for 24 hours — clear the cache from Settings
9. The QRZ password is never exposed through the API

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
