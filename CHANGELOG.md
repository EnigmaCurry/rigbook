# Changelog

## v0.1.13

### Spot Map

- Interactive spot map with spotter and home location markers
- Triangle selection showing spotter-to-spot-to-home geometry
- Hover/click interaction linking map markers to spots table rows
- Translucent map popups
- Click handler on home location markers
- Use POTA park grid for map center/distance when spot is a POTA activator
- Map toggle button with localStorage persistence
- Spots header and map are sticky, only table scrolls

### Logbook

- Sticky column headers on logbook table
- `updated_at` column on QSO log, initialized from timestamp for existing records
- Home/End and PgUp/PgDn keyboard shortcuts for scrolling logbook entries
- Keyboard shortcuts documented on About page

### QSO Form

- Show missing required fields indicator on QSO form
- Highlight required fields red when empty
- Disable SKCC validated button when SKCC field is blank
- Fix skcc_exch not sent when creating new QSO

### Parks Page

- Move cache stats to Cache tab, add personal park stats to My Parks tab
- Make Parks page header and map sticky, only park list scrolls
- Set minimum zoom level on My Parks map
- Fix By Country tab tree to fill available height
- Fix Cache tab program list to fill available height

### Other

- Fix logbook_right setting not loading on Settings page (#47)
- Add CHANGELOG.md section to GitHub release notes

## v0.1.12

### Settings Page

- Masonry grid layout for settings sections
- Changed sections highlighted with accent border when modified
- Unsaved changes reminder with pulsing Save button
- Interactive grid square map picker (🌍 button) — nearly fullscreen modal

### QSO Form Protection

- Block page navigation when QSO form has unsaved changes
- Preserve edit form state when switching between dual right-pane pages
- Fix hash change handler overwriting editId during dual pane switches

### Band Conditions

- Stale data warning when last update exceeds 20 minutes

### Server Shutdown

- Shutdown page shows 💤 favicon and "Close this tab" title on all shutdown paths (including decline pending logbook and delete logbook)
- Server force-kills after 1 second to avoid hanging on SSE connections
- Consolidated shutdown state handling into setShutdownState/clearShutdownState

## v0.1.11

### Dual-Pane Layout

- Support multiple right-pane pages: Hunting, Spots, Parks, Notifications, and Conditions
- Nav buttons show merged icons (e.g. 📖🧭) indicating which page is paired with the logbook
- Draggable divider between panes with position saved to localStorage (clamped 10%-90%)
- Option to place the logbook on the right side (Settings > Appearance)
- Layout gracefully collapses to single-pane on narrow screens without losing form data

### QSO Form Protection

- Unsaved form changes block spot clicks and radio tuning with alert messages
- Changed fields highlighted with accent-colored left border (both Add and Edit modes)
- VFO polling no longer overwrites user-edited frequency and mode fields
- Auto-filled data from QRZ, SKCC, and POTA lookups does not trigger false dirty state
- Callsign log filter defaults to showing previous contacts for the entered call

### Logbook Table

- Draggable column reordering with order persisted to localStorage
- Sort column and direction persisted to localStorage

### Spots Page

- Already-worked callsign/band/mode combinations are greyed out
- POTA activator cross-reference: spots matching active POTA activators show a 🌲 icon
- Clicking a POTA-flagged spot prefills the QSO form with park data
- Closest spotter column now shows the spotter's callsign
- Saveable default filters with reactive Save/Clear button
- Spot cache is purged when a source (RBN or HamAlert) is disabled

### SKCC Skimmer

- POTA activator cross-reference with 🌲 icon and park data prefill
- Skimmer is hidden when all spot sources are disabled

### Parks Page

- My Parks map renders correctly on initial load (fixed race condition)
- QSO form park is shown on the map with a green marker, even if not yet logged
- Park list refreshes after logging, editing, or deleting a QSO
- Park list fills remaining vertical space

### Band Conditions (New)

- New Conditions page (🌤️) with solar and HF/VHF propagation data from N0NBH/hamqsl.com
- Solar flux, sunspots, A/K indices, X-ray, geomagnetic field, solar wind, signal noise
- HF band conditions for 80m-10m rated Good/Fair/Poor for day and night
- VHF conditions including aurora and E-skip
- 10-minute server-side cache, 30-second client polling
- Available as a dual-pane view alongside the logbook

### Settings

- New POTA enable/disable toggle
- New band conditions enable/disable toggle
- New simulated flrig mode (CW, USB, LSB, RTTY, FT8) for testing without hardware
- Clicking callsign in nav bar goes to Settings
- Clicking Rigbook title goes to dual/hunting home page
- Reconnect button on shutdown page

## v0.1.10

- Sticky default filters for Spots page with Save/Clear default button

## v0.1.9

- Add `flrig_enabled` setting — flrig is now disabled by default
- Use 127.0.0.1 as default flrig host instead of localhost

## v0.1.8

- Change HamAlert credential labels to Telnet Username/Password for clarity
- Link to WA7PGE Windows installation guide in README

## v0.1.7

### Multiple Logbooks

- Support for multiple separate logbooks stored as individual SQLite databases
- Open a specific logbook by name: `rigbook field-day`
- Database picker mode (`--pick`) to choose or create logbooks from a UI
- Copy logbooks as templates to share settings across events
- Delete logbook from Settings with confirmation
- Shutdown server button in Settings
- Environment variables for container/headless usage: `RIGBOOK_DB`, `RIGBOOK_PICKER`, `RIGBOOK_NO_BROWSER`
- Close Logbook menu option in picker mode

## v0.1.6

### Notifications

- In-app notification system for HamAlert spots
- Notification inbox with unread/read/done states
- Desktop browser notifications (optional, requires permission)
- Popup modal notifications (optional, more intrusive)
- Real-time push via Server-Sent Events (SSE)
- Unread count badge on notification icon
- Mark All Read, individual Read/Done actions
- Clickable callsigns and frequencies in notifications
- Test notification button in Settings
- Refresh worked-today state after editing a QSO

## v0.1.5

- Cache SKCC Skimmer data over 10-minute window with stable TTL snapshots

## v0.1.4

### Reverse Beacon Network and Spots

- RBN and HamAlert spot feed integration with real-time aggregation
- Spots page with filterable, sortable table of all cached spots
- SKCC cross-reference column and filter
- QRZ location lookup with rate limiting
- Closest spotter distance calculation from user grid square
- Band badges with color-coded labels
- Deep-linkable filter URLs
- SKCC Skimmer on Hunting page showing nearby SKCC members on CW

### POTA Parks

- Park search autocomplete by reference, name, location, or grid
- Unique state autocompletion per country

## v0.1.3

- DXCC entity field for countries
- POTA program filter on Hunting page
- Sticky spotter filters on Hunting page

## v0.1.2

- Fix rootless Podman volume permissions
- README improvements for development and setup

## v0.1.1

- Bind Docker container to localhost only
- Use host network for Docker to access flrig

## v0.1.0

Initial release.

- Log QSO contacts with callsign, frequency, mode, signal reports, and more
- Auto-fill frequency and mode from radio via flrig XMLRPC
- Country and state autocomplete with normalization
- POTA park field
- SKCC member number field
- Sortable log table with click-to-edit
- Dark theme
- SQLite database at `~/.local/rigbook/rigbook.db`
- FastAPI backend serving built Svelte frontend
