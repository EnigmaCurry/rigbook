# 📻️ Rigbook

<img width="1100" height="541" alt="image" src="https://github.com/user-attachments/assets/a747aa5b-3afd-49ee-8ae7-6f626d9037e2" />


A ham radio logbook app. Log amateur radio contacts (QSOs)
with a local web UI, optionally connected to your radio via
[flrig](http://www.w1hkj.com/flrig-help/). 

The current release of Rigbook is a feature-rich logbook for operators 
engaged in POTA and/or SKCC activities. 

## Features

- Log QSO contacts with callsign, frequency, mode, signal reports, and
  more
- Auto-fill frequency and mode from your radio via flrig XMLRPC
- Everything in the header is clickable: **Rigbook** and **callsign** go
  home, **VFO frequency** opens the VFO editor with band plan, **mode**
  cycles radio modes, **UTC clock** copies the timestamp to clipboard,
  **📖** logbook, **🧭** hunting, **🌲** My Parks, and **+** adds a new QSO
- Keyboard shortcuts: `/` search, `N` new QSO, `H` hunting, `L` logbook,
  `P` parks, `T` tune radio, `M` cycle mode, `?` about, `Esc` close
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
- Hunting page — browse active Parks on the Air activators and nearby
  SKCC members on CW, filter by mode/band/distance, click to tune your
  radio and add QSOs
- Reverse Beacon Network (RBN) and HamAlert spot feeds with real-time
  aggregation, per-spotter TTL, and distance calculation
- Spots page — filterable, sortable table of all RBN/HamAlert spots
  with SKCC cross-reference, QRZ location lookup, deep-linkable
  filter URLs, and clickable callsigns/frequencies to log QSOs or
  tune your radio
- Notification system — HamAlert spots create persistent in-app
  notifications with clickable callsigns and frequencies; optional
  desktop browser notifications and popup modal alerts; SSE push
  for real-time updates
- QRZ callsign lookup with connection test button in Settings
- SKCC member number auto-lookup
- All timestamps in UTC with 24-hour format
- Light and dark themes (toggle in Settings)

## Binary Release

Pre-built binaries are available from the
[Releases](https://github.com/EnigmaCurry/rigbook/releases) page for
Linux, macOS, and Windows (amd64 and arm64).

1. Download the binary for your platform
2. Make it executable (Linux/macOS): `chmod +x rigbook-*`
3. Run it in your terminal: `./rigbook-linux-amd64` (or whichever binary you downloaded)
4. Open http://localhost:8073 in your browser

**macOS:** The binary is unsigned, so macOS will block it by default.
After downloading, remove the quarantine attribute:

```bash
xattr -d com.apple.quarantine rigbook-macos-arm64
```

Rigbook automatically opens your browser when the server starts. Use
`--no-browser` or set `RIGBOOK_NO_BROWSER=true` to disable this.

The server binds to localhost only because Rigbook has no built-in
authentication. Set `RIGBOOK_HOST` and `RIGBOOK_PORT` environment
variables to change the bind address.

## Container image

A pre-built image is available from GitHub Container Registry:

```bash
mkdir -p ${HOME}/.local/rigbook && \
podman run --rm -it --name rigbook \
  --network=host \
  -v ${HOME}/.local/rigbook:/root/.local/rigbook:Z \
  ghcr.io/enigmacurry/rigbook:latest
```

Open http://localhost:8073 in your browser. The port is bound to
localhost only because Rigbook has no built-in authentication.

## Development
### Dev Requirements

- [Python](https://www.python.org/) 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- [Node.js](https://nodejs.org/) and npm (for building the frontend)
- [just](https://github.com/casey/just) (command runner, optional but recommended)
- [flrig](http://www.w1hkj.com/flrig-help/) (optional, for radio integration)

### Dev Installation

```bash
git clone https://github.com/EnigmaCurry/rigbook.git \
          ~/git/vendor/enigmacurry/rigbook
cd ~/git/vendor/enigmacurry/rigbook

# Install all dependencies:
just deps

# Create optional "rigbook" alias in your ~/.bashrc:
alias rigbook="just -f ~/git/vendor/enigmacurry/rigbook/Justfile run"
```

### Dev Usage

```bash
# Build frontend and start the server:
just run

# Run alias from any directory:
rigbook
```

Open http://localhost:8073 in your browser. The server binds to
localhost only because Rigbook has no built-in authentication.

## First-time setup

1. Click the hamburger menu (top right) and go to **Settings**
2. Enter your callsign and grid square
3. If using flrig, configure the host and port (default: `localhost:12345`)
4. Optionally enable **RBN** and/or **HamAlert** for real-time spot data
5. Click **Save**

### Logging contacts

1. Click **+** or go to the hamburger menu and select **Add QSO**
2. Enter a callsign — the date and time auto-fill when you tab out
3. If flrig is connected, frequency and mode auto-fill from your radio
4. QRZ auto-fills name, QTH, state, country, and grid (if configured)
5. Type a POTA park reference or name to autocomplete from cached parks
6. Current timestamp will be used as QSO date/time if left blank
7. Supply a timestamp if current time is not desired
8. Click **Log QSO** to save — returns to Hunting (if from a spot) or
   Logbook (if manual)
9. Click **Cancel** to return to the previous view

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

The **Hunting** page combines POTA spots and SKCC skimmer data into a
single view with shared filters.

- Filter by **mode**, **band**, **program**, and **distance** (100mi,
  500mi, 1000mi, or unlimited)
- Distance filtering uses your grid square to calculate great-circle
  distance to activators (POTA) and closest RBN spotter (SKCC)

### POTA Spots

Active [Parks on the Air](https://pota.app/) activators, sourced from
the pota.app API.

- Cards show the activator callsign, park name, frequency, mode, band,
  grid square, QSO count, and how long ago the spot was posted
- **Click a callsign** to open the Add QSO form with prefilled data
- **Click a frequency** to tune your radio (requires flrig)
- Award emojis shown for parks you've already contacted
- Spots refresh automatically every 30 seconds

### SKCC Skimmer

When enabled in Settings (requires RBN feed), shows nearby
[SKCC](https://www.skccgroup.com/) members currently calling CQ on CW.

- Cards show callsign, SKCC number, frequency, band, home location
  (from QRZ), closest spotter distance and signal strength, and time
  since last spotted
- **Click a callsign** to open the Add QSO form with SKCC number
  prefilled and QRZ lookup triggered
- **Click a frequency** to tune your radio
- Spots persist for 10 minutes with per-spotter TTL
- The skimmer is hidden when no matching spots are found or when mode
  filter excludes CW

## POTA Parks

The **Parks** page lets you download and browse
[Parks on the Air](https://pota.app/) park data.

### Downloading parks

1. Go to **Parks** → **Cache** tab
2. Select the countries you want to cache (use the filter to find them)
3. Click **Update Parks** — progress streams as each location is fetched
4. Park data is selected and downloaded by the user and cached in SQLite

### My Parks

The default **My Parks** tab shows all parks where you've logged
contacts, with a Leaflet world map showing markers for each park.

- Sort by date, name, or QSO count
- Click a park in the list to highlight it on the map and open its popup
- Hover over parks to preview them on the map
- Map popups link to park detail pages
- Award emojis show your progress: ✅ 1, ✌️ 2, 📐 3, 🍀 4, ⭐ 5,
  🌟 10, 💎 15, 🏆 20+

### Browsing parks

- **By Country** tab shows a tree: expand a country to see its
  locations, expand a location to see its parks
- Click any park to view its detail page with name, location, grid,
  coordinates, activation stats, an OpenStreetMap embed, your personal
  QSO count with award emojis, and a log of your QSOs at that park
- Park detail pages include an **Add QSO** button that pre-fills the
  park reference
- Park detail pages are deep-linkable (`/#/parks/park/US-0008`)

### Park autocomplete on QSO form

When adding a QSO, the POTA Park field autocompletes from cached parks.
Type a reference (e.g. `US1024` or `US-1024`), park name, location, or
grid square to search. Selecting a park auto-fills the grid, country,
and state fields. The park name appears as a clickable link that opens
a detail overlay without leaving the form.

## QRZ Callsign Lookup

If you have a [QRZ.com](https://www.qrz.com/) account, Rigbook
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

## Spot Feeds (RBN and HamAlert)

Rigbook can connect to the
[Reverse Beacon Network](https://www.reversebeacon.net/) (RBN) and
[HamAlert](https://hamalert.org/) to receive real-time spot data.

### Setup

1. Go to **Settings** and find the **Reverse Beacon Network** section
2. Check **Enable RBN Feed** — your callsign is used to authenticate
3. Select feed types: **CW** (port 7000) and/or **Digital** (port 7001
   for FT8, FT4, RTTY, etc.)
4. Optionally enable **Show SKCC Skimmer on Hunting page**
5. For HamAlert, enter your username and password in the **HamAlert**
   section
6. Click **Save** — feeds connect automatically and show connection
   status

### Spots page

The **Spots** page (in the hamburger menu) shows a live table of all
cached spots from RBN and HamAlert.

- Filter by **source**, **band**, **mode**, and **callsign**
- Click column headers to sort — sorting is stable across refreshes
- When filtering to CW, an **SKCC** column and filter appear to show
  only SKCC members
- **Home Location** column shows country/state from QRZ cache, with
  rate-limited automatic lookups (burst 20, then 1/second)
- **Closest Spot** column shows distance and signal strength from the
  nearest RBN spotter to your grid square
- Band badges use color-coded labels with luminance-based text contrast
- Filter state is encoded in the URL for deep linking (e.g.
  `/#/spots?mode=CW&band=20m`)
- Cache stats show callsign count, total spots, and average
  spots per callsign
- Spots aggregate by callsign/mode with per-spotter TTL — spotter
  count decays as individual observations expire

## Notifications

Rigbook has a built-in notification system that alerts you when
HamAlert spots arrive. Notifications are stored in the database and
persist across sessions.

### Notification inbox

Go to **Notifications** in the hamburger menu, or click the envelope
icon (✉) next to the hamburger. The icon shows the unread count when
there are unread notifications.

- **Inbox** tab shows unread and read notifications, newest first
- Unread notifications are highlighted with a green left border
- **Click a callsign** to tune your radio and open the Add QSO form
- **Click a frequency** to tune your radio
- Mark individual notifications as **Read** or **Done**
- **Done** moves a notification out of the inbox to the Done tab
- **Mark All Read** clears all unread highlights at once

### Desktop notifications

Enable desktop notifications in **Settings → Notifications** to
receive browser popups when new alerts arrive. Desktop notifications
are dismissed automatically when you read the corresponding in-app
notification.

In-app notifications are always enabled regardless of this setting.

### Popup notifications

Enable **Popup notifications** in Settings to show a modal dialog
immediately when new notifications arrive. This is more intrusive but
harder to miss.

- **OK** dismisses the popup and marks notifications as read
- **Keep Unread** dismisses the popup but leaves notifications unread
- **View All** marks as read and navigates to the Notifications page
- Callsigns and frequencies are clickable in the popup

### HamAlert integration

When HamAlert is enabled and connected (configured in **Settings →
HamAlert**), every HamAlert spot automatically creates a notification
with the callsign, frequency, mode, and any trigger comments. These
appear in the notification inbox and trigger desktop/popup
notifications if enabled.

### Real-time updates

Notifications use Server-Sent Events (SSE) for real-time push — the
notification badge, inbox, and popup all update instantly without
polling. The SSE endpoint is at `/api/events/stream`.

### Test notification

Click **Send Test Notification** in Settings to create a test
notification after a 5-second delay. Use this to verify desktop and
popup notifications are working.

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

## Multiple Logbooks

Rigbook can manage multiple separate logbooks stored as individual
database files in `~/.local/rigbook/`. This is useful for keeping
contacts from different events (Field Day, POTA activations, contests)
in separate logs.

### Open a specific logbook

By default (no arguments), Rigbook opens the logbook named `rigbook`
(`~/.local/rigbook/rigbook.db`). Pass a name as a positional argument
to start with a different logbook instead. Names may contain only
letters, digits, hyphens, and underscores. The name maps to
`~/.local/rigbook/<name>.db`. If the logbook doesn't exist yet, a
welcome screen asks you to confirm creating it (or shut down).

```bash
# Open an existing logbook
rigbook field-day

# Open a new logbook (prompts to confirm creation)
rigbook winter-contest

# Open the default logbook (rigbook.db)
rigbook
```

### Copying logbooks as templates

Each logbook is a self-contained SQLite file with its own settings,
including callsign, grid, QRZ credentials, and feed configuration. You
can set up one logbook as a template and copy it to create new
logbooks that share the same configuration:

```bash
cp ~/.local/rigbook/rigbook.db ~/.local/rigbook/field-day.db
rigbook field-day
```

This avoids re-entering QRZ credentials and other settings for each
new logbook. Note that the copied logbook will also contain all the
same log entries as the original — delete any unwanted contacts after
opening the copy.

### Database picker mode

Use `--pick` to start Rigbook without loading any logbook. Instead, a
picker screen lists all `.db` files in `~/.local/rigbook/` and lets
you choose which one to open or create a new one. The hamburger menu
gains a **Close Logbook** option to return to the picker and switch
logbooks without restarting.

```bash
rigbook --pick
```

### Container / environment variable usage

For containers or environments where CLI arguments aren't convenient,
use environment variables instead:

| Variable | Description |
|---|---|
| `RIGBOOK_DB` | Logbook name to open (e.g. `field-day` → `~/.local/rigbook/field-day.db`) |
| `RIGBOOK_PICKER` | Set to `1`, `true`, or `yes` to enable picker mode |

CLI arguments take precedence over environment variables.

```bash
# Container with a specific logbook
podman run --rm -it --name rigbook \
  --network=host \
  -e RIGBOOK_DB=field-day \
  -v ${HOME}/.local/rigbook:/root/.local/rigbook:Z \
  ghcr.io/enigmacurry/rigbook:latest

# Container with picker mode
podman run --rm -it --name rigbook \
  --network=host \
  -e RIGBOOK_PICKER=1 \
  -v ${HOME}/.local/rigbook:/root/.local/rigbook:Z \
  ghcr.io/enigmacurry/rigbook:latest
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
