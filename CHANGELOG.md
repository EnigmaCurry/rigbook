# Changelog

## v0.1.20

### Spots Map

- Animated flowing dashes on blue spotter→station lines
- Selected station marker shown in bright yellow
- Show station popup on spot selection via click or keyboard navigation
- Restore map view and selection when navigating away and returning
- True fullscreen maps using browser Fullscreen API (not just full-window CSS)
- Skip QRZ location lookup for portable/mobile callsigns (containing `/`)

### Map Resize

- Clamp map height to 70% of viewport to prevent drag handle going off-screen
- Reset map to 25% of viewport when toggling map on
- Fix fullscreen map blocked by inline max-height constraint

### Navigation

- Add `S` keyboard shortcut to navigate to Spots page
- Escape while focused on search bar blurs the input
- Consistent Spots/Parks button order across wide, narrow, and hamburger menu
- Consistent Notifications/Conditions order across all nav modes

### My Parks

- Move stats and map toggle above the map
- Restore map view and park selection when returning to page

## v0.1.19

### Spots Map

- Draw triangle lines between station, spotter, and QTH on the map
- Show all spotters with known grids and draw dashed lines for co-witnesses
- Scale station markers from dim gold to bright yellow based on spotter count
- Show closest spotter in bright blue, non-closest in darker blue
- Hide non-co-witnessing markers when a spot is selected
- Draw map lines via shortest path across antimeridian
- Place markers on same world copy as QTH for correct rendering
- Click spot row to zoom map to fit triangle points
- Click map markers to scroll to and select spot row
- Click park markers to select and scroll park list, click map background to deselect
- Fix My Parks map showing prime meridian / wrong location on initial load
- Default map theme follows app theme (Canvas Dark Grey for dark mode)

### Spots Table

- Reorderable, resizable columns with sort indicators
- Up/down arrow keyboard navigation for Spots and My Parks lists
- Make POTA park references clickable with park detail modal
- Show park name next to clickable POTA reference
- Confine callsign and frequency click targets to text span instead of full cell
- Fix sticky header positioning on sortable columns

### Logbook

- Show tree emoji next to callsigns with POTA park
- Rename Home Location column to Location

### Settings

- Move Save button to top of settings page below reminder
- Add QRZ Logout button to clear saved password
- Show 'unset' placeholder for QRZ password when not configured
- Key all localStorage settings by logbook name for per-logbook preferences
- Style hamqsl.com link to match Links page

### Bug Fixes

- Fix ADIF import crash ("_original_comment is an invalid keyword argument for Contact")
- Fix marker positions not updating when grid data changes
- Fix double-highlight in keyboard navigation

## v0.1.18

### QSO Form

- Fill country, state, and grid when a POTA park code is typed and field is blurred, not just on autocomplete selection
- Populate QTH from QRZ for non-portable stations on hunting prefill

## v0.1.17

### Import / Export Layout

- Import/Export page no longer scrolls — preview table is the only scrollable element
- Viewport-filling flex layout: sidebar fixed at 315px, preview fills remaining space
- Action bar spans full page width at bottom, always visible regardless of horizontal scroll
- Preview area has minimum height (~5 lines) even when empty
- Sidebar scrolls independently when content overflows
- Empty preview states centered in the available space
- Layout works correctly at all screen widths

## v0.1.16

### Import / Export Redesign

- Tab-based Import / Export page with shared preview table and action bar
- Import preview: stage an ADIF file, review all contacts before committing
- Full QSO field set in preview table (all 16 columns) with resizable columns
- Click any row to expand and see all field details plus the raw ADIF line
- ADIF header info bar above preview (click to expand raw header text)
- Import dedup: duplicates detected by UUID or callsign+timestamp
- Cancel button to clear staged import

### Comment Template

- Configurable comment template for ADIF export and import
- Select QSO fields (POTA, SKCC, Grid, etc.) with editable labels and drag-to-reorder
- Export: template fields prepended to COMMENT with configurable separator
- Import: template prefix stripped from comments, with live preview of changes
- "Suggest from file" button analyzes imported ADIF comments to auto-detect template
- Colon-optional matching (e.g. "POTA US-9331" matches "POTA: US-9331")
- Frequency KHz/MHz conversion handled in matching
- Round-trip safe: APP_RIGBOOK_COMMENT_FMT field preserves separator in exported ADIF
- Match count shown: "142 of 201 comments stripped"
- Explanatory message when no template configured or no matches found

### Import Validation

- Validate imported records for field mismatches between comments and normalized ADIF fields
- Errors tab filters to show only problematic rows
- Editable fix UI: choose comment value, field value, or type custom value
- Fixes update the contact in-place and re-strip comments client-side
- Import button disabled until all errors are resolved
- SKCC field validation: must start with a digit and be one word
- Yellow highlight and border around selected row and expander

### Logbook Table

- Draggable column resize handles on logbook table headers
- Column widths persisted to localStorage
- Auto-size columns on first load: fixed columns shrink to content, free-form columns fill space
- Sort/drag click area separated from resize handles

### Database Backup

- Manual backup button in Settings (copies DB to backups/ subdirectory)
- Auto-backup system with configurable interval (default 24h) and max backups (default 10)
- Auto-backups named with `_autobackup_` prefix, pruned automatically
- Manual backups kept indefinitely
- Last backup time stored in database for reliable scheduling
- Database file size shown in Settings
- Backup status: last auto-backup time, next due, counts

### Authentication

- Optional HTTP Basic auth (disabled by default)
- Username is callsign, password is user-configured
- Per-database password salt using database filename
- `--no-auth` CLI flag to bypass authentication
- WWW-Authenticate realm set to database name for per-logbook credentials

### Other

- Full-width export page layout with side-by-side form and preview on wide screens
- Row expander stays within viewport regardless of horizontal scroll
- Version read from package metadata instead of hardcoded
- "Shift + Scroll" horizontal shortcut added to About page
- "Clear All QSOs" in Settings Danger Zone with double confirmation
- Info logging for backups, imports, and mass deletes

## v0.1.15

### Multi-Band Filtering

- Select multiple bands simultaneously on Spots and Hunting pages
- Color-coded band badge toggle buttons replace single-select dropdown
- Filters auto-save on every change (no more Save/Clear default buttons)
- Backend accepts comma-separated band values for multi-band queries
- Backward compatible with existing saved single-band filters

### Spots Page

- Full-width layout (removed max-width cap)
- Right-aligned filters matching Hunting page style
- Narrower callsign input sized to fit placeholder text
- Hunting page auto-refreshes spots on filter change (removed Refresh button)

### Draggable Map Resize

- Draggable divider between map and list on Spots and Parks pages
- Drag handle to resize map height, persisted to localStorage
- Dragging below minimum height hides the map and toggles the button off
- Map toggle button added to Parks page
- ResizeObserver on map elements fixes tile rendering on container resize

## v0.1.14

### Map Tile Themes

- Configurable map tile theme in Settings > Appearance
- 11 built-in themes: USGS Topo/Imagery, ESRI Topo/Satellite, National Geographic, Blue Marble, NASA City Lights, Carto Dark/Light, Canvas World Dark Grey, and Default (follows app light/dark theme)
- Custom tile URL option with automatic uppercase {Z}/{X}/{Y} normalization for Leaflet
- Live map preview widget in settings with QTH marker
- Preview updates when toggling light/dark app theme in Default mode
- Default map theme is now National Geographic

### Bug Fixes

- Fix spot map showing markers that don't match the current filter
- Fix duplicate fullscreen button on Parks My Parks map

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
