<script>
  import { onMount, onDestroy, createEventDispatcher, tick } from "svelte";
  import { TILE_THEMES, resolveTileConfig } from "./mapTiles.js";
  import { storageGet, storageSet } from "./storage.js";
  import { THEMES, THEME_NAMES, applyThemeVars, applyCustomThemeVars, generateCustomTheme } from "./themes.js";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";
  import GridMap from "./GridMap.svelte";
  import "vanilla-colorful/hex-color-picker.js";

  let showGridPicker = false;

  export let logbookName = "";
  export let pickerMode = false;
  export let needsSetup = false;
  export let initialTab = null;
  export let highlightSection = null;
  export let clientCount = 0;

  const dispatch = createEventDispatcher();

  let my_callsign = "";
  let my_grid = "";
  let default_rst = "599";
  let qrz_username = "";
  let qrz_password = "";
  let hasQrzPassword = false;
  let pota_enabled = false;
  let solar_enabled = false;
  let update_check_enabled = true;
  let updateCheckResult = null;
  let updateChecking = false;
  let updateSupported = false;
  let updateNotWritable = false;
  let updateApplying = false;
  let updateApplyError = "";
  let updateCustomRepo = false;
  let updateGithubRepo = "";
  let updateBuildRepo = "";
  let updateBuildSha = "";
  let updateOfficialBuild = false;
  let flrig_enabled = false;
  let flrig_simulate = false;
  let flrig_host = "127.0.0.1";
  let flrig_port = "12345";
  let logbook_right = false;
  let wide_breakpoint = "1200";
  let wide_mode_enabled = true;
  let theme = "dark";
  let themeContrast = 50;
  let themeBrightness = 50;
  let themeHue = 0;
  let themeSaturation = 50;
  let themeMode = "preset"; // "preset" or "custom"
  let customBg = "#24252b";
  let customText = "#eaeaea";
  let customAccent = "#00ff88";
  let customVfo = "#00ccff";
  let map_theme = "natgeo";
  let map_custom_url = "";
  let custom_header = "";

  // Spot map color presets
  const MAP_COLOR_PRESETS = {
    "aurora":      { label: "Aurora Borealis",  qth: "#ff4444", station: "#00ff88", spotter: "#00ccff", secondary: "#7744aa", strokes: { qth: "black", station: "black", spotter: "black", secondary: "white" } },
    "coral-reef":  { label: "Coral Reef",       qth: "#ff4488", station: "#ffaa55", spotter: "#44ddcc", secondary: "#2288aa", strokes: { qth: "black", station: "black", spotter: "black", secondary: "white" } },
    "sunset":      { label: "Sunset Ridge",     qth: "#ff2255", station: "#ffbb00", spotter: "#00ccff", secondary: "#8844cc", strokes: { qth: "white", station: "black", spotter: "black", secondary: "white" } },
    "deep-sea":    { label: "Deep Sea",         qth: "#ff3355", station: "#00eebb", spotter: "#4488ff", secondary: "#cc44ff", strokes: { qth: "white", station: "black", spotter: "white", secondary: "black" } },
    "volcano":     { label: "Volcano",          qth: "#ff0000", station: "#ffdd00", spotter: "#00bbff", secondary: "#aa55ff", strokes: { qth: "white", station: "black", spotter: "black", secondary: "white" } },
    "glacier":     { label: "Glacier",          qth: "#ff4466", station: "#00ffcc", spotter: "#4499ff", secondary: "#ddaa00", strokes: { qth: "white", station: "black", spotter: "white", secondary: "black" } },
    "savanna":     { label: "Savanna",          qth: "#ff3333", station: "#ddcc00", spotter: "#33bbaa", secondary: "#cc66ff", strokes: { qth: "white", station: "black", spotter: "black", secondary: "black" } },
    "midnight":    { label: "Midnight Pass",    qth: "#ff3366", station: "#bb88ff", spotter: "#00ddff", secondary: "#ffaa00", strokes: { qth: "white", station: "white", spotter: "black", secondary: "black" } },
    "tundra":      { label: "Tundra",           qth: "#ff5544", station: "#44eedd", spotter: "#ffcc33", secondary: "#aa66ff", strokes: { qth: "black", station: "black", spotter: "black", secondary: "white" } },
    "desert":      { label: "Desert Mesa",      qth: "#ff2200", station: "#ffcc00", spotter: "#44ccbb", secondary: "#dd55aa", strokes: { qth: "white", station: "black", spotter: "black", secondary: "black" } },
  };
  const MAP_COLOR_PRESET_NAMES = Object.keys(MAP_COLOR_PRESETS);

  let spotMapColorMode = "preset"; // "preset" or "custom"
  let spotMapPreset = "aurora";
  let spotMapQth = MAP_COLOR_PRESETS.aurora.qth;
  let spotMapStation = MAP_COLOR_PRESETS.aurora.station;
  let spotMapSpotter = MAP_COLOR_PRESETS.aurora.spotter;
  let spotMapSecondary = MAP_COLOR_PRESETS.aurora.secondary;
  let spotMapStrokeQth = "black";
  let spotMapStrokeStation = "black";
  let spotMapStrokeSpotter = "black";
  let spotMapStrokeSecondary = "white";
  let default_page = "log";
  let qrzStatus = null; // { ok, error?, username? }
  let qrzChecking = false;

  // RBN settings
  let sql_query_enabled = false;
  let rbn_enabled = false;
  let rbn_host = "telnet.reversebeacon.net";
  let rbn_feed_cw = true;
  let rbn_feed_digital = false;
  let skcc_skimmer_enabled = false;
  let skcc_skimmer_distance = "500";
  let rbn_idle_timeout_enabled = true;
  let rbn_idle_timeout_minutes = "720";

  // HamAlert settings
  let hamalert_enabled = false;
  let hamalert_host = "hamalert.org";
  let hamalert_port = "7300";
  let hamalert_username = "";
  let hamalert_password = "";
  let hasHamalertPassword = false;

  // Global settings state
  let global_my_callsign = "";
  let global_my_grid = "";
  let global_default_rst = "599";
  let global_qrz_username = "";
  let global_qrz_password = "";
  let global_hasQrzPassword = false;
  let global_hamalert_username = "";
  let global_hamalert_password = "";
  let global_hasHamalertPassword = false;
  let global_flrig_enabled = false;
  let global_flrig_simulate = false;
  let global_flrig_host = "127.0.0.1";
  let global_flrig_port = "12345";
  let global_default_pick_mode = true;
  let global_default_port = "8073";
  let global_default_logbook_name = "rigbook";
  let global_open_browser_on_startup = true;
  let global_auto_shutdown_delay = "300";
  let global_browser_url_override = "";
  let availableLogbooks = [];
  let globalSettingsLoaded = false;

  // Track which per-logbook settings are from global defaults
  let settingSources = {};
  // Store global default values for use as placeholders
  let globalPlaceholders = {};

  const validTabs = ["station", "features", "appearance", "updates", "system", "global"];
  let activeTab = (initialTab && validTabs.includes(initialTab)) ? initialTab : "station";
  let settingsLoaded = false;

  $: if (initialTab && validTabs.includes(initialTab)) activeTab = initialTab;
  $: if (needsSetup) activeTab = "station";
  $: if (highlightSection && settingsLoaded) {
    tick().then(() => {
      const el = document.querySelector(`[data-section="${highlightSection}"]`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
        el.classList.add("highlight-flash");
        el.addEventListener("animationend", () => el.classList.remove("highlight-flash"), { once: true });
      }
      highlightSection = null;
    });
  }

  let updateCheckLoaded = false;
  $: if (settingsLoaded && !updateCheckLoaded) {
    updateCheckLoaded = true;
    if (update_check_enabled) loadUpdateCheck();
  }

  // Desktop notifications
  let desktopNotifPermission = typeof Notification !== "undefined" ? Notification.permission : "denied";
  let desktopNotifEnabled = storageGet("desktop_notifications_enabled") === "true";
  let popupNotifEnabled = false;
  let testPending = false;

  // Map preview
  let previewEl;
  let previewMap;
  let previewMapEl; // track which DOM node the map was created on
  let previewTileLayer;
  let previewLayers = [];

  function gridToLatLon(grid) {
    if (!grid || grid.length < 4) return null;
    const g = grid.toUpperCase();
    const lonField = g.charCodeAt(0) - 65;
    const latField = g.charCodeAt(1) - 65;
    const lonSq = parseInt(g[2]);
    const latSq = parseInt(g[3]);
    let lon = lonField * 20 - 180 + lonSq * 2 + 1;
    let lat = latField * 10 - 90 + latSq * 1 + 0.5;
    if (grid.length >= 6) {
      const lonSub = g.charCodeAt(4) - 65;
      const latSub = g.charCodeAt(5) - 65;
      lon = lonField * 20 - 180 + lonSq * 2 + lonSub * (2/24) + (1/24);
      lat = latField * 10 - 90 + latSq * 1 + latSub * (1/24) + (1/48);
    }
    return { lat, lon };
  }

  function clearPreviewLayers() {
    for (const l of previewLayers) {
      if (previewMap) previewMap.removeLayer(l);
    }
    previewLayers = [];
  }

  function previewDot(ll, color, border, size = 10) {
    const half = Math.round(size / 2);
    const icon = L.divIcon({
      className: "",
      html: `<div style="width:${size}px;height:${size}px;background:${color};border-radius:50%;border:2px solid ${border};"></div>`,
      iconSize: [size, size],
      iconAnchor: [half, half],
    });
    return L.marker(ll, { icon, interactive: false });
  }

  function previewApproxDot(ll, color, size = 12) {
    const half = Math.round(size / 2);
    const qColor = spotMapStrokeStation === "white" ? "#fff" : "#000";
    const icon = L.divIcon({
      className: "",
      html: `<div style="width:${size}px;height:${size}px;background:${color}88;border:2px dashed ${color};border-radius:50%;display:flex;align-items:center;justify-content:center"><span style="color:${qColor};font-size:${Math.max(size-2,8)}px;font-weight:bold;line-height:1">?</span></div>`,
      iconSize: [size, size],
      iconAnchor: [half, half],
    });
    return L.marker(ll, { icon, interactive: false });
  }

  function strokeRgba(strokeName) {
    return strokeName === "white" ? "rgba(255,255,255,0.85)" : "rgba(0,0,0,0.85)";
  }

  function previewLabel(ll, text, color, strokeName) {
    const stroke = strokeRgba(strokeName);
    const icon = L.divIcon({
      className: "marker-label",
      html: `<span style="color:${color};font-size:11px;font-weight:bold;white-space:nowrap;paint-order:stroke fill;-webkit-text-stroke:3px ${stroke};text-shadow:0 0 4px ${stroke}">${text}</span>`,
      iconSize: [0, 0],
      iconAnchor: [0, 16],
    });
    return L.marker(ll, { icon, interactive: false });
  }

  function darkenColor(hex, factor = 0.5) {
    const h = hex.replace("#", "");
    const r = Math.round(parseInt(h.slice(0, 2), 16) * factor);
    const g = Math.round(parseInt(h.slice(2, 4), 16) * factor);
    const b = Math.round(parseInt(h.slice(4, 6), 16) * factor);
    return `#${r.toString(16).padStart(2,"0")}${g.toString(16).padStart(2,"0")}${b.toString(16).padStart(2,"0")}`;
  }

  function distLabel(from, to, color, strokeName, t = 0.5) {
    const mi = Math.round(haversineMi(from, to));
    const mid = [from[0] + (to[0] - from[0]) * t, from[1] + (to[1] - from[1]) * t];
    const stroke = strokeRgba(strokeName);
    const icon = L.divIcon({
      className: "distance-label",
      html: `<span style="color:${color};font-size:11px;font-weight:bold;white-space:nowrap;paint-order:stroke fill;-webkit-text-stroke:3px ${stroke};text-shadow:0 0 4px ${stroke}">${mi} mi</span>`,
      iconSize: [0, 0],
    });
    return L.marker(mid, { icon, interactive: false });
  }

  function updatePreview() {
    if (!previewEl) return;
    const tiles = resolveTileConfig(map_theme, map_custom_url);
    const pos = gridToLatLon(effectiveSetting(my_grid, "my_grid"));
    const center = pos ? [pos.lat, pos.lon] : [39, -98];
    // Reinitialize if the DOM node changed (tab switch destroys/recreates it)
    if (previewMap && previewMapEl !== previewEl) {
      previewMap.remove();
      previewMap = null;
      previewTileLayer = null;
      previewLayers = [];
    }
    const isNew = !previewMap;
    if (isNew) {
      previewMap = L.map(previewEl, {
        scrollWheelZoom: true, zoomControl: true,
        dragging: true, doubleClickZoom: false,
        attributionControl: false,
      });
      previewMapEl = previewEl;
      previewMap.setView(center, 4); // temporary; fitBounds below
    }
    if (previewTileLayer) previewMap.removeLayer(previewTileLayer);
    previewTileLayer = L.tileLayer(tiles.url, {
      attribution: tiles.attribution,
      maxZoom: tiles.maxZoom,
    }).addTo(previewMap);

    clearPreviewLayers();

    const qthBorder = darkenColor(spotMapQth);
    const staBorder = darkenColor(spotMapStation);
    const sptBorder = darkenColor(spotMapSpotter);
    const secBorder = darkenColor(spotMapSecondary);

    const qthLL = pos ? [pos.lat, pos.lon] : center;

    // --- Single triangle: QTH ↔ Station ↔ Spotter, with one secondary ---
    const staLL = [qthLL[0] + 5, qthLL[1] + 8];
    const sptLL = [qthLL[0] + 1, qthLL[1] + 5];
    const secLL = [qthLL[0] - 1, qthLL[1] + 10];

    const layers = [];
    function add(...items) { for (const l of items) layers.push(l); }

    // Bullseye helper for exact stations
    function exactDot(ll, size = 11) {
      const half = Math.round(size / 2);
      const qColor = spotMapStrokeStation === "white" ? "#fff" : "#000";
      const icon = L.divIcon({
        className: "",
        html: `<div style="width:${size}px;height:${size}px;background:${spotMapStation};border:2px solid ${staBorder};border-radius:50%;display:flex;align-items:center;justify-content:center"><span style="color:${qColor};font-size:${Math.max(size-5,6)}px;font-weight:bold;line-height:1">@</span></div>`,
        iconSize: [size, size],
        iconAnchor: [half, half],
      });
      return L.marker(ll, { icon, interactive: false });
    }

    // Lines
    add(
      L.polyline([secLL, staLL], { color: spotMapSecondary, weight: 2, opacity: 0.4, dashArray: "4 6" }),
      L.polyline([sptLL, staLL], { color: spotMapSpotter, weight: 2, opacity: 0.6, dashArray: "6 4" }),
      L.polyline([staLL, qthLL], { color: spotMapStation, weight: 2, opacity: 0.6, dashArray: "6 4" }),
      L.polyline([qthLL, sptLL], { color: spotMapSpotter, weight: 2, opacity: 0.6, dashArray: "2 16", lineCap: "round" }),
    );

    // Triangle dots + labels
    add(
      exactDot(staLL, 12),
      previewDot(sptLL, spotMapSpotter, sptBorder, 10),
      previewDot(secLL, spotMapSecondary, secBorder, 8),
    );

    const callLabel = effectiveSetting(my_callsign.trim(), "my_callsign", "QTH").toUpperCase();
    add(
      previewLabel(staLL, "W1AW", spotMapStation, spotMapStrokeStation),
      previewLabel(sptLL, "K3LR", spotMapSpotter, spotMapStrokeSpotter),
      previewLabel(secLL, "VE3NEA", spotMapSecondary, spotMapStrokeSecondary),
      distLabel(sptLL, staLL, spotMapSpotter, spotMapStrokeSpotter, 0.33),
      distLabel(staLL, qthLL, spotMapStation, spotMapStrokeStation, 0.5),
    );

    // --- Scattered unconnected dots (no lines, no labels) ---
    // Exact stations with bullseye
    add(
      exactDot([qthLL[0] - 5, qthLL[1] - 4], 10),
      exactDot([qthLL[0] + 7, qthLL[1] - 6], 11),
      exactDot([qthLL[0] + 2, qthLL[1] + 14], 10),
      exactDot([qthLL[0] - 3, qthLL[1] - 9], 12),
    );
    // Approximate stations
    add(
      previewApproxDot([qthLL[0] - 6, qthLL[1] + 6], spotMapStation, 11),
      previewApproxDot([qthLL[0] + 4, qthLL[1] - 11], spotMapStation, 10),
    );
    // Primary spotters
    add(
      previewDot([qthLL[0] + 6, qthLL[1] + 11], spotMapSpotter, sptBorder, 9),
      previewDot([qthLL[0] - 4, qthLL[1] - 6], spotMapSpotter, sptBorder, 9),
      previewDot([qthLL[0] + 8, qthLL[1] + 4], spotMapSpotter, sptBorder, 10),
    );
    // Secondary spotters
    add(
      previewDot([qthLL[0] - 7, qthLL[1] + 2], spotMapSecondary, secBorder, 8),
      previewDot([qthLL[0] + 3, qthLL[1] - 5], spotMapSecondary, secBorder, 8),
    );

    // --- QTH dot + label (on top) ---
    add(previewDot(qthLL, spotMapQth, qthBorder, 14));
    add(previewLabel(qthLL, callLabel, spotMapQth, spotMapStrokeQth));

    for (const l of layers) {
      l.addTo(previewMap);
      previewLayers.push(l);
    }

    // On first render, fit the map to show all points
    // Delay until container has its final size (tab switch starts at zero dimensions)
    if (isNew) {
      const allPoints = previewLayers
        .filter(l => l instanceof L.Marker)
        .map(l => { const ll = l.getLatLng(); return [ll.lat, ll.lng]; });
      setTimeout(() => {
        if (previewMap) {
          previewMap.invalidateSize();
          previewMap.fitBounds(allPoints, { padding: [20, 20] });
        }
      }, 50);
    }
  }

  function haversineMi(a, b) {
    const R = 3958.8;
    const dLat = (b[0] - a[0]) * Math.PI / 180;
    const dLon = (b[1] - a[1]) * Math.PI / 180;
    const lat1 = a[0] * Math.PI / 180;
    const lat2 = b[0] * Math.PI / 180;
    const h = Math.sin(dLat/2)**2 + Math.cos(lat1)*Math.cos(lat2)*Math.sin(dLon/2)**2;
    return Math.round(R * 2 * Math.asin(Math.sqrt(h)));
  }

  $: if (settingsLoaded && previewEl) {
    map_theme, map_custom_url, spotMapQth, spotMapStation, spotMapSpotter, spotMapSecondary;
    updatePreview();
  }


  // Shutdown
  let noShutdown = false;
  let disableShutdown = false;
  let autoShutdownOnDisconnect = false;
  let shutdownInMenu = false;

  // Backup
  let backupMessage = "";
  let backupMessageType = "";
  let backingUp = false;
  let dbInfo = null;
  let backupStatus = null;
  let autoBackupEnabled = true;
  let autoBackupHours = 24;
  let autoBackupMax = 10;
  let backupSaveTimer = null;
  let backupSettingsReady = false;

  async function loadDbInfo() {
    try {
      const res = await fetch("/api/settings/backup/db-info");
      if (res.ok) dbInfo = await res.json();
    } catch { /* ignore */ }
  }

  async function loadBackupStatus() {
    try {
      const res = await fetch("/api/settings/backup/status");
      if (res.ok) {
        backupStatus = await res.json();
        autoBackupEnabled = backupStatus.auto_enabled;
        autoBackupHours = backupStatus.interval_hours;
        autoBackupMax = backupStatus.max_backups;
        await tick();
        backupSettingsReady = true;
      }
    } catch { /* ignore */ }
  }

  function formatSize(bytes) {
    if (!bytes) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function timeAgo(iso) {
    if (!iso) return "never";
    const d = new Date(iso);
    const now = new Date();
    const mins = Math.floor((now - d) / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  }

  function formatDue(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const now = new Date();
    if (d <= now) return "now";
    const mins = Math.floor((d - now) / 60000);
    if (mins < 60) return `in ${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `in ${hrs}h`;
    const days = Math.floor(hrs / 24);
    return `in ${days}d`;
  }

  async function saveAutoBackupSettings() {
    if (!backupSettingsReady) return;  // not yet loaded — skip spurious saves
    clearTimeout(backupSaveTimer);
    backupSaveTimer = setTimeout(async () => {
      try {
        await Promise.all([
          fetch("/api/settings/auto_backup_enabled", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: autoBackupEnabled ? "true" : "false" }),
          }),
          fetch("/api/settings/auto_backup_hours", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: String(autoBackupHours) }),
          }),
          fetch("/api/settings/auto_backup_max", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: String(autoBackupMax) }),
          }),
        ]);
        loadBackupStatus();
      } catch { /* ignore */ }
    }, 300);
  }

  async function performBackup() {
    backingUp = true;
    backupMessage = "";
    try {
      const res = await fetch("/api/settings/backup", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        const sizeKB = (data.size / 1024).toFixed(1);
        backupMessage = `Saved to ${data.path} (${sizeKB} KB)`;
        backupMessageType = "success";
      } else {
        const data = await res.json().catch(() => null);
        backupMessage = data?.detail || "Backup failed";
        backupMessageType = "error";
      }
    } catch (e) {
      backupMessage = `Backup failed: ${e.message}`;
      backupMessageType = "error";
    }
    backingUp = false;
  }

  // Danger zone
  let dangerConfirmName = "";
  let qsoCount = 0;
  let deleteError = "";
  let deleting = false;
  let clearing = false;
  let clearError = "";

  async function clearAllContacts() {
    if (dangerConfirmName !== logbookName) {
      clearError = "Name does not match";
      return;
    }
    let count = "all";
    try {
      const res = await fetch("/api/contacts/");
      if (res.ok) { const data = await res.json(); count = data.length; }
    } catch {}
    if (!confirm(`Are you sure you want to delete ${count} QSOs from "${logbookName}"? This cannot be undone.`)) {
      return;
    }
    clearError = "";
    clearing = true;
    try {
      const res = await fetch("/api/contacts/all", { method: "DELETE" });
      if (res.ok) {
        const data = await res.json();
        clearError = `Deleted ${data.deleted} contacts.`;
      } else {
        const data = await res.json().catch(() => null);
        clearError = data?.detail || "Failed to clear contacts";
      }
    } catch {
      clearError = "Failed to clear contacts";
    }
    clearing = false;
  }

  async function deleteLogbook() {
    if (dangerConfirmName !== logbookName) {
      deleteError = "Name does not match";
      return;
    }
    if (!confirm(`Are you sure you want to permanently delete "${logbookName}"? This cannot be undone.`)) {
      return;
    }
    deleteError = "";
    deleting = true;
    try {
      const res = await fetch("/api/logbooks/delete", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: logbookName }),
      });
      if (res.ok) {
        const data = await res.json();
        dispatch("deleted", { shutdown: data.shutdown });
      } else {
        const data = await res.json();
        deleteError = data.detail || "Failed to delete logbook";
      }
    } catch {
      deleteError = "Failed to delete logbook";
    }
    deleting = false;
  }

  function disconnectOthers() {
    const others = clientCount - 1;
    if (!confirm(`Disconnect ${others} other client${others !== 1 ? "s" : ""}? It may take up to 30s to process this request.`)) return;
    dispatch("disconnect-others");
  }

  async function shutdownServer() {
    if (!confirm("Are you sure you want to shut down the Rigbook server?")) return;
    dispatch("shutdown-pending");
    try {
      const res = await fetch("/api/logbooks/shutdown", { method: "POST" });
      if (res.ok) {
        dispatch("shutdown");
        dispatch("deleted", { shutdown: true });
      }
    } catch {
      dispatch("shutdown");
      dispatch("deleted", { shutdown: true });
    }
  }

  async function enableDesktopNotifications() {
    if (typeof Notification === "undefined") return;
    const perm = await Notification.requestPermission();
    desktopNotifPermission = perm;
    if (perm === "granted") {
      desktopNotifEnabled = true;
      storageSet("desktop_notifications_enabled", "true");
    }
  }

  function disableDesktopNotifications() {
    desktopNotifEnabled = false;
    storageSet("desktop_notifications_enabled", "false");
  }

  async function sendTestNotification() {
    // Ensure permission is granted before testing
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      const perm = await Notification.requestPermission();
      desktopNotifPermission = perm;
      if (perm === "granted") {
        desktopNotifEnabled = true;
        storageSet("desktop_notifications_enabled", "true");
      }
    }
    testPending = true;
    try {
      await fetch("/api/notifications/test", { method: "POST" });
    } catch {}
    setTimeout(() => { testPending = false; }, 5000);
  }

  // Feed connection status
  let spotStatus = { rbn: { connected: false, enabled: false, idle_stopped: false }, hamalert: { connected: false, enabled: false } };
  let spotStatusInterval;

  async function onThemeChange() {
    applyThemeVars(theme, themeContrast, themeBrightness, themeHue, themeSaturation);
    storageSet("rigbook-theme", theme);
    await saveSetting("theme", theme);
    await saveSetting("theme_mode", "preset");
    dispatch("saved");
    if (map_theme === "default") updatePreview();
  }


  function applyCurrentTheme() {
    if (themeMode === "preset") {
      applyThemeVars(theme, themeContrast, themeBrightness, themeHue, themeSaturation);
    } else {
      applyCustomThemeVars(customBg, customText, customAccent, customVfo, themeContrast, themeBrightness, themeHue, themeSaturation);
    }
  }

  function broadcastThemePreview(key, value) {
    fetch(`/api/settings/theme-preview?key=${encodeURIComponent(key)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    }).catch(() => {});
  }

  function onContrastInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_contrast", String(themeContrast));
  }
  async function onContrastCommit() {
    applyCurrentTheme();
    await saveSetting("theme_contrast", String(themeContrast));
    dispatch("saved");
  }

  function onBrightnessInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_brightness", String(themeBrightness));
  }
  async function onBrightnessCommit() {
    applyCurrentTheme();
    await saveSetting("theme_brightness", String(themeBrightness));
    dispatch("saved");
  }

  function onHueInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_hue", String(themeHue));
  }
  async function onHueCommit() {
    applyCurrentTheme();
    await saveSetting("theme_hue", String(themeHue));
    dispatch("saved");
  }

  function onSaturationInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_saturation", String(themeSaturation));
  }
  async function onSaturationCommit() {
    applyCurrentTheme();
    await saveSetting("theme_saturation", String(themeSaturation));
    dispatch("saved");
  }

  async function resetSliders() {
    themeContrast = 50;
    themeBrightness = 50;
    themeHue = 0;
    themeSaturation = 50;
    applyCurrentTheme();
    await Promise.all([
      saveSetting("theme_contrast", "50"),
      saveSetting("theme_brightness", "50"),
      saveSetting("theme_hue", "0"),
      saveSetting("theme_saturation", "50"),
    ]);
    dispatch("saved");
  }

  async function onThemeModeChange() {
    if (themeMode === "preset") {
      applyThemeVars(theme, themeContrast, themeBrightness, themeHue, themeSaturation);
      storageSet("rigbook-theme", theme);
      await saveSetting("theme_mode", "preset");
    } else {
      applyCustomThemeVars(customBg, customText, customAccent, customVfo, themeContrast, themeBrightness, themeHue, themeSaturation);
      storageSet("rigbook-theme", "custom");
      await saveSetting("theme_mode", "custom");
      await saveCustomColors();
    }
    dispatch("saved");
    if (map_theme === "default") updatePreview();
  }

  function onCustomColorInput() {
    applyCustomThemeVars(customBg, customText, customAccent, customVfo, themeContrast, themeBrightness, themeHue, themeSaturation);
    storageSet("rigbook-theme", "custom");
  }

  async function onCustomColorCommit() {
    onCustomColorInput();
    await saveCustomColors();
    dispatch("saved");
    if (map_theme === "default") updatePreview();
  }

  function onCustomColorChange() {
    onCustomColorCommit();
  }

  async function saveCustomColors() {
    const colors = JSON.stringify({ bg: customBg, text: customText, accent: customAccent, vfo: customVfo });
    await saveSetting("custom_theme_colors", colors);
  }

  let colorDragging = false;

  function colorPicker(node, { getValue, setValue }) {
    node.setAttribute("color", getValue());
    const onChange = (e) => { setValue(e.detail.value); onCustomColorInput(); };
    const onDown = () => { colorDragging = true; };
    const onUp = () => { if (colorDragging) { colorDragging = false; onCustomColorCommit(); } };
    node.addEventListener("color-changed", onChange);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchend", onUp);
    node.addEventListener("mousedown", onDown);
    node.addEventListener("touchstart", onDown);
    return {
      update({ getValue }) { node.setAttribute("color", getValue()); },
      destroy() {
        node.removeEventListener("color-changed", onChange);
        window.removeEventListener("mouseup", onUp);
        window.removeEventListener("touchend", onUp);
        node.removeEventListener("mousedown", onDown);
        node.removeEventListener("touchstart", onDown);
      },
    };
  }

  // --- Spot map color pickers ---
  let mapColorDragging = false;

  function mapColorPicker(node, { getValue, setValue }) {
    node.setAttribute("color", getValue());
    const onChange = (e) => { setValue(e.detail.value); updatePreview(); };
    const onDown = () => { mapColorDragging = true; };
    const onUp = () => { if (mapColorDragging) { mapColorDragging = false; saveSpotMapColors(); } };
    node.addEventListener("color-changed", onChange);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchend", onUp);
    node.addEventListener("mousedown", onDown);
    node.addEventListener("touchstart", onDown);
    return {
      update({ getValue }) { node.setAttribute("color", getValue()); },
      destroy() {
        node.removeEventListener("color-changed", onChange);
        window.removeEventListener("mouseup", onUp);
        window.removeEventListener("touchend", onUp);
        node.removeEventListener("mousedown", onDown);
        node.removeEventListener("touchstart", onDown);
      },
    };
  }

  function applyMapPreset(name) {
    const p = MAP_COLOR_PRESETS[name];
    if (!p) return;
    spotMapQth = p.qth;
    spotMapStation = p.station;
    spotMapSpotter = p.spotter;
    spotMapSecondary = p.secondary;
    spotMapStrokeQth = p.strokes.qth;
    spotMapStrokeStation = p.strokes.station;
    spotMapStrokeSpotter = p.strokes.spotter;
    spotMapStrokeSecondary = p.strokes.secondary;
  }

  async function onMapColorModeChange() {
    if (spotMapColorMode === "preset") {
      applyMapPreset(spotMapPreset);
    }
    updatePreview();
    await saveSpotMapColors();
  }

  async function onMapPresetChange() {
    applyMapPreset(spotMapPreset);
    updatePreview();
    await saveSpotMapColors();
  }

  function onMapColorInput() {
    updatePreview();
  }

  async function onMapColorCommit() {
    updatePreview();
    await saveSpotMapColors();
  }

  async function saveSpotMapColors() {
    const colors = JSON.stringify({
      mode: spotMapColorMode,
      preset: spotMapPreset,
      qth: spotMapQth, station: spotMapStation, spotter: spotMapSpotter, secondary: spotMapSecondary,
      strokeQth: spotMapStrokeQth, strokeStation: spotMapStrokeStation,
      strokeSpotter: spotMapStrokeSpotter, strokeSecondary: spotMapStrokeSecondary,
    });
    await saveSetting("spot_map_colors", colors);
    dispatch("saved");
  }

  let qrzCacheStats = null;
  let skccCacheStats = null;
  let solarCacheStats = null;

  async function fetchCacheStats() {
    try {
      const [qrzRes, skccRes, solarRes] = await Promise.all([
        fetch("/api/qrz/cache/stats"),
        fetch("/api/skcc/cache/stats"),
        fetch("/api/solar/cache/stats"),
      ]);
      if (qrzRes.ok) qrzCacheStats = await qrzRes.json();
      if (skccRes.ok) skccCacheStats = await skccRes.json();
      if (solarRes.ok) solarCacheStats = await solarRes.json();
    } catch {}
  }

  async function clearExpiredCache() {
    try {
      await Promise.all([
        fetch("/api/qrz/cache/expired", { method: "DELETE" }),
        fetch("/api/skcc/cache/expired", { method: "DELETE" }),
      ]);
      await fetchCacheStats();
    } catch {}
  }

  async function clearCache() {
    try {
      await Promise.all([
        fetch("/api/qrz/cache", { method: "DELETE" }),
        fetch("/api/skcc/cache", { method: "DELETE" }),
        fetch("/api/solar/cache", { method: "DELETE" }),
      ]);
      qrzCacheStats = null;
      skccCacheStats = null;
      solarCacheStats = null;
      await fetchCacheStats();
    } catch {}
  }

  $: stripCallsign = () => { my_callsign = my_callsign.replace(/\s/g, ""); };
  $: stripGrid = () => { my_grid = my_grid.replace(/[^A-Za-z0-9]/g, ""); };

  function normalizeGrid(g) {
    // Maidenhead: AA99aa — pos 0-1 letters, 2-3 digits, 4-5 letters
    let out = "";
    for (let i = 0; i < g.length && out.length < 6; i++) {
      const c = g[i];
      const pos = out.length;
      if (pos < 2) {
        if (/[A-Ra-r]/.test(c)) out += c.toUpperCase();
      } else if (pos < 4) {
        if (/[0-9]/.test(c)) out += c;
      } else {
        if (/[A-Xa-x]/.test(c)) out += c.toLowerCase();
      }
    }
    return out;
  }

  // --- Auto-save helpers ---

  async function saveSetting(key, value) {
    await fetch(`/api/settings/${key}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    });
    // Re-check source: if saved value is blank, it may fall back to global
    try {
      const res = await fetch(`/api/settings/${key}`);
      if (res.ok) {
        const data = await res.json();
        settingSources[key] = data.source || "logbook";
        if (data.source === "global" && data.value) {
          globalPlaceholders[key] = data.value;
        } else {
          delete globalPlaceholders[key];
        }
      }
    } catch {}
    settingSources = settingSources;
    globalPlaceholders = globalPlaceholders;
  }

  /** Return the effective value for a setting: local value, global placeholder, or fallback. */
  function effectiveSetting(localValue, key, fallback = "") {
    return localValue || globalPlaceholders[key] || fallback;
  }

  const dirtyFields = new Set();
  const debounceTimers = {};

  function markDirty(key) {
    dirtyFields.add(key);
    clearTimeout(debounceTimers[key]);
    debounceTimers[key] = setTimeout(() => {
      if (dirtyFields.has(key) && fieldSavers[key]) {
        dirtyFields.delete(key);
        fieldSavers[key]();
      }
    }, 2000);
  }

  async function flushPending() {
    for (const key of dirtyFields) {
      if (fieldSavers[key]) await fieldSavers[key]();
    }
    dirtyFields.clear();
  }

  async function switchTab(tab) {
    await flushPending();
    activeTab = tab;
    window.location.hash = `/settings/${tab}`;
  }

  // --- Masonry layout action ---
  // Distributes child sections into two columns, placing each in the shorter column.
  // Runs once on mount and on window resize only — no MutationObserver.
  function masonry(node) {
    let col1, col2;
    const MIN_WIDTH = 640;

    function collectSections() {
      const direct = [...node.querySelectorAll(":scope > .settings-section")];
      const inCols = col1 ? [...col1.querySelectorAll(":scope > .settings-section"), ...col2.querySelectorAll(":scope > .settings-section")] : [];
      return [...direct, ...inCols];
    }

    function teardownColumns() {
      if (col1 && col1.parentNode === node) {
        const sections = collectSections();
        for (const s of sections) node.appendChild(s);
        if (col1.parentNode === node) node.removeChild(col1);
        if (col2.parentNode === node) node.removeChild(col2);
      }
    }

    function layout() {
      const width = node.parentElement?.offsetWidth || node.offsetWidth;

      if (width < MIN_WIDTH) {
        teardownColumns();
        return;
      }

      const sections = collectSections();
      if (!sections.length) return;

      // Move sections back to node temporarily for measurement
      for (const s of sections) node.appendChild(s);
      if (col1 && col1.parentNode === node) {
        node.removeChild(col1);
        node.removeChild(col2);
      }

      if (!col1) {
        col1 = document.createElement("div");
        col1.className = "masonry-col";
        col2 = document.createElement("div");
        col2.className = "masonry-col";
      }

      const heights = sections.map(s => s.offsetHeight);

      let h1 = 0, h2 = 0;
      const assign1 = [], assign2 = [];
      for (let i = 0; i < sections.length; i++) {
        if (h1 <= h2) {
          assign1.push(sections[i]);
          h1 += heights[i];
        } else {
          assign2.push(sections[i]);
          h2 += heights[i];
        }
      }

      for (const s of assign1) col1.appendChild(s);
      for (const s of assign2) col2.appendChild(s);
      node.appendChild(col1);
      node.appendChild(col2);
    }

    const raf = requestAnimationFrame(layout);
    const onResize = () => requestAnimationFrame(layout);
    window.addEventListener("resize", onResize);

    return {
      destroy() {
        cancelAnimationFrame(raf);
        window.removeEventListener("resize", onResize);
        teardownColumns();
      },
    };
  }

  async function restartFeeds() {
    await fetch("/api/spots/restart", { method: "POST" });
    setTimeout(fetchSpotStatus, 2000);
  }


  // --- Per-field auto-save handlers ---

  const fieldSavers = {
    my_callsign: async () => {
      await saveSetting("my_callsign", my_callsign.trim().toUpperCase());
      dispatch("saved");
    },
    my_grid: async () => {
      my_grid = normalizeGrid(my_grid.trim());
      await saveSetting("my_grid", my_grid);
      dispatch("saved");
    },
    default_rst: async () => {
      await saveSetting("default_rst", default_rst.trim());
    },
    qrz_username: async () => {
      await saveSetting("qrz_username", qrz_username.trim().toUpperCase());
      dispatch("saved");
    },
    flrig_host: async () => {
      if (flrig_enabled && flrig_host.trim() && flrig_port.trim()) {
        await saveSetting("flrig_host", flrig_host.trim());
        dispatch("saved");
      }
    },
    flrig_port: async () => {
      if (flrig_enabled && flrig_host.trim() && flrig_port.trim()) {
        await saveSetting("flrig_port", flrig_port.trim());
        dispatch("saved");
      }
    },
    wide_breakpoint: async () => {
      await saveSetting("wide_breakpoint", wide_mode_enabled ? String(wide_breakpoint) : "0");
      dispatch("saved");
    },
    map_custom_url: async () => {
      await saveSetting("map_custom_url", map_custom_url.trim());
      dispatch("saved");
    },
    custom_header: async () => {
      await saveSetting("custom_header", custom_header.trim());
      dispatch("saved");
    },
    rbn_host: async () => {
      await saveSetting("rbn_host", rbn_host.trim());
      await restartFeeds();
      dispatch("saved");
    },
    skcc_skimmer_distance: async () => {
      await saveSetting("skcc_skimmer_distance", skcc_skimmer_distance.trim() || "500");
      dispatch("saved");
    },
    rbn_idle_timeout_minutes: async () => {
      await saveSetting("rbn_idle_timeout_minutes", rbn_idle_timeout_enabled ? (rbn_idle_timeout_minutes.trim() || "720") : "0");
      await restartFeeds();
      dispatch("saved");
    },
    hamalert_host: async () => {
      await saveSetting("hamalert_host", hamalert_host.trim());
      if (hamalert_enabled && hamalertFieldsFilled()) await restartFeeds();
      dispatch("saved");
    },
    hamalert_port: async () => {
      await saveSetting("hamalert_port", hamalert_port.trim());
      if (hamalert_enabled && hamalertFieldsFilled()) await restartFeeds();
      dispatch("saved");
    },
    hamalert_username: async () => {
      await saveSetting("hamalert_username", hamalert_username.trim());
      if (hamalert_enabled && hamalertFieldsFilled()) await restartFeeds();
      dispatch("saved");
    },
  };

  function onCallsignInput() {
    stripCallsign();
    markDirty("my_callsign");
  }

  function onGridInput() {
    my_grid = normalizeGrid(my_grid.slice(0, 6));
    markDirty("my_grid");
  }

  function onDefaultRstInput() {
    markDirty("default_rst");
  }

  function onFieldKeydown(e) {
    if (e.key === "Enter") e.target.blur();
  }

  async function onFieldBlur(key) {
    clearTimeout(debounceTimers[key]);
    if (dirtyFields.has(key) && fieldSavers[key]) {
      dirtyFields.delete(key);
      await fieldSavers[key]();
    }
  }

  async function onPotaEnabledChange() {
    await saveSetting("pota_enabled", pota_enabled ? "true" : "false");
    dispatch("saved");
  }

  async function onSolarEnabledChange() {
    await saveSetting("solar_enabled", solar_enabled ? "true" : "false");
    dispatch("saved");
  }

  async function onSqlQueryEnabledChange() {
    await saveSetting("sql_query_enabled", sql_query_enabled ? "true" : "false");
    dispatch("saved");
  }

  async function onUpdateCheckEnabledChange() {
    await saveGlobalSetting("update_check_enabled", update_check_enabled ? "true" : "false");
    if (update_check_enabled) {
      await fetchUpdateCheck();
    } else {
      updateCheckResult = null;
    }
    dispatch("saved");
  }

  async function onFlrigEnabledChange() {
    await saveSetting("flrig_enabled", flrig_enabled ? "true" : "false");
    dispatch("saved");
  }

  async function onFlrigSimulateChange() {
    await saveSetting("flrig_simulate", flrig_simulate ? "true" : "false");
    dispatch("saved");
  }

  function onFlrigHostInput() {
    markDirty("flrig_host");
  }

  function onFlrigPortInput() {
    markDirty("flrig_port");
  }

  async function onLogbookRightChange() {
    await saveSetting("logbook_right", logbook_right ? "true" : "false");
    dispatch("saved");
  }

  async function onWideModeEnabledChange() {
    if (wide_mode_enabled) {
      await saveSetting("wide_breakpoint", String(wide_breakpoint));
    } else {
      await saveSetting("wide_breakpoint", "0");
    }
    dispatch("saved");
  }

  function onWideBreakpointInput() {
    markDirty("wide_breakpoint");
  }

  async function onMapThemeChange() {
    await saveSetting("map_theme", map_theme);
    dispatch("saved");
  }

  async function onDefaultPageChange() {
    await saveSetting("default_page", default_page);
    dispatch("saved");
  }

  function onMapCustomUrlInput() {
    markDirty("map_custom_url");
  }

  function onCustomHeaderInput() {
    markDirty("custom_header");
  }

  async function onRbnEnabledChange() {
    await saveSetting("rbn_enabled", rbn_enabled ? "true" : "false");
    await restartFeeds();
    dispatch("saved");
  }

  async function onRbnFeedCwChange() {
    const rbnFeeds = [rbn_feed_cw ? "cw" : "", rbn_feed_digital ? "digital" : ""].filter(Boolean).join(",");
    await saveSetting("rbn_feeds", rbnFeeds || "cw");
    await restartFeeds();
    dispatch("saved");
  }

  async function onRbnFeedDigitalChange() {
    const rbnFeeds = [rbn_feed_cw ? "cw" : "", rbn_feed_digital ? "digital" : ""].filter(Boolean).join(",");
    await saveSetting("rbn_feeds", rbnFeeds || "cw");
    await restartFeeds();
    dispatch("saved");
  }

  function onRbnHostInput() {
    markDirty("rbn_host");
  }

  async function onSkccSkimmerEnabledChange() {
    await saveSetting("skcc_skimmer_enabled", skcc_skimmer_enabled ? "true" : "false");
    await restartFeeds();
    dispatch("saved");
  }

  function onSkccSkimmerDistanceInput() {
    markDirty("skcc_skimmer_distance");
  }

  async function onRbnIdleTimeoutEnabledChange() {
    if (rbn_idle_timeout_enabled && !rbn_idle_timeout_minutes.trim()) {
      rbn_idle_timeout_minutes = "12";
    }
    await saveSetting("rbn_idle_timeout_minutes", rbn_idle_timeout_enabled ? (rbn_idle_timeout_minutes.trim() || "720") : "0");
    await restartFeeds();
    dispatch("saved");
  }

  function onRbnIdleTimeoutHoursInput() {
    markDirty("rbn_idle_timeout_minutes");
  }

  function hamalertFieldsFilled() {
    return hamalert_host.trim() && hamalert_port.trim() && hamalert_username.trim() && hasHamalertPassword;
  }

  async function onHamalertEnabledChange() {
    await saveSetting("hamalert_enabled", hamalert_enabled ? "true" : "false");
    if (hamalertFieldsFilled()) {
      await restartFeeds();
    }
    dispatch("saved");
  }

  function onHamalertHostInput() {
    markDirty("hamalert_host");
  }

  function onHamalertPortInput() {
    markDirty("hamalert_port");
  }

  function onHamalertUsernameInput() {
    markDirty("hamalert_username");
  }

  async function loginQrz() {
    if (!qrz_password.trim()) return;
    await saveSetting("qrz_password", qrz_password.trim());
    hasQrzPassword = true;
    qrz_password = "";
    await checkQrz();
  }

  async function loginHamalert() {
    if (!hamalert_password.trim()) return;
    await saveSetting("hamalert_password", hamalert_password.trim());
    hasHamalertPassword = true;
    hamalert_password = "";
    if (hamalert_enabled && hamalertFieldsFilled()) {
      await restartFeeds();
    }
    dispatch("saved");
  }

  async function fetchSpotStatus() {
    try {
      const res = await fetch("/api/spots/status");
      if (res.ok) spotStatus = await res.json();
    } catch {}
  }

  async function fetchSettings() {
    try {
      const res = await fetch("/api/settings/");
      if (res.ok) {
        const data = await res.json();
        settingSources = {};
        globalPlaceholders = {};
        for (const s of data) {
          if (s.source) settingSources[s.key] = s.source;
          const isGlobal = s.source === "global";
          // Text fields: show global defaults as placeholders, not values
          if (s.key === "my_callsign") { if (isGlobal) { globalPlaceholders.my_callsign = s.value; my_callsign = ""; } else my_callsign = s.value || ""; }
          if (s.key === "my_grid") { if (isGlobal) { globalPlaceholders.my_grid = s.value; my_grid = ""; } else my_grid = s.value || ""; }
          if (s.key === "default_rst") { if (isGlobal) { globalPlaceholders.default_rst = s.value; default_rst = ""; } else default_rst = s.value || "599"; }
          if (s.key === "flrig_host") { if (isGlobal) { globalPlaceholders.flrig_host = s.value; flrig_host = ""; } else flrig_host = s.value || "127.0.0.1"; }
          if (s.key === "flrig_port") { if (isGlobal) { globalPlaceholders.flrig_port = s.value; flrig_port = ""; } else flrig_port = s.value || "12345"; }
          if (s.key === "hamalert_username") { if (isGlobal) { globalPlaceholders.hamalert_username = s.value; hamalert_username = ""; } else hamalert_username = s.value || ""; }
          // Boolean/password fields: inherit global value normally
          if (s.key === "qrz_username") { if (isGlobal) { globalPlaceholders.qrz_username = s.value; qrz_username = ""; } else qrz_username = s.value || ""; }
          if (s.key === "qrz_password") hasQrzPassword = !!s.value && s.value !== "";
          if (s.key === "pota_enabled") pota_enabled = s.value !== "false";
          if (s.key === "solar_enabled") solar_enabled = s.value === "true";
          if (s.key === "sql_query_enabled") sql_query_enabled = s.value === "true";
          if (s.key === "update_check_enabled") update_check_enabled = s.value !== "false";
          if (s.key === "flrig_enabled") flrig_enabled = s.value === "true";
          if (s.key === "flrig_simulate") flrig_simulate = s.value === "true";
          if (s.key === "rbn_enabled") rbn_enabled = s.value === "true";
          if (s.key === "rbn_host") rbn_host = s.value || "telnet.reversebeacon.net";
          if (s.key === "rbn_feeds") {
            const feeds = (s.value || "cw").split(",").map(f => f.trim().toLowerCase());
            rbn_feed_cw = feeds.includes("cw");
            rbn_feed_digital = feeds.includes("digital");
          }
          if (s.key === "skcc_skimmer_enabled") skcc_skimmer_enabled = s.value === "true";
          if (s.key === "skcc_skimmer_distance") skcc_skimmer_distance = s.value || "500";
          if (s.key === "rbn_idle_timeout_minutes") {
            const v = parseFloat(s.value);
            if (v > 0) {
              rbn_idle_timeout_enabled = true;
              rbn_idle_timeout_minutes = s.value;
            } else {
              rbn_idle_timeout_enabled = false;
              rbn_idle_timeout_minutes = "12";
            }
          }
          if (s.key === "hamalert_enabled") hamalert_enabled = s.value === "true";
          if (s.key === "hamalert_host") hamalert_host = s.value || "hamalert.org";
          if (s.key === "hamalert_port") hamalert_port = s.value || "7300";
          if (s.key === "hamalert_username") hamalert_username = s.value || "";
          if (s.key === "hamalert_password") hasHamalertPassword = !!s.value && s.value !== "";
          if (s.key === "wide_breakpoint") {
            if (s.value === "0") {
              wide_mode_enabled = false;
              wide_breakpoint = "1200";
            } else {
              wide_mode_enabled = true;
              wide_breakpoint = s.value || "1500";
            }
          }
          if (s.key === "logbook_right") logbook_right = s.value === "true";
          if (s.key === "map_theme") map_theme = s.value || "default";
          if (s.key === "map_custom_url") map_custom_url = s.value || "";
          if (s.key === "spot_map_colors") {
            try {
              const c = JSON.parse(s.value);
              if (c.mode) spotMapColorMode = c.mode;
              if (c.preset && MAP_COLOR_PRESETS[c.preset]) spotMapPreset = c.preset;
              if (c.qth) spotMapQth = c.qth;
              if (c.station) spotMapStation = c.station;
              if (c.spotter) spotMapSpotter = c.spotter;
              if (c.secondary) spotMapSecondary = c.secondary;
              if (c.strokeQth) spotMapStrokeQth = c.strokeQth;
              if (c.strokeStation) spotMapStrokeStation = c.strokeStation;
              if (c.strokeSpotter) spotMapStrokeSpotter = c.strokeSpotter;
              if (c.strokeSecondary) spotMapStrokeSecondary = c.strokeSecondary;
            } catch {}
          }
          if (s.key === "custom_header") custom_header = s.value || "";
          if (s.key === "default_page") default_page = s.value || "log";
          if (s.key === "theme") theme = s.value || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
          if (s.key === "theme_contrast") { const v = parseInt(s.value); themeContrast = isNaN(v) ? 50 : v; }
          if (s.key === "theme_brightness") { const v = parseInt(s.value); themeBrightness = isNaN(v) ? 50 : v; }
          if (s.key === "theme_hue") { const v = parseInt(s.value); themeHue = isNaN(v) ? 0 : v; }
          if (s.key === "theme_saturation") { const v = parseInt(s.value); themeSaturation = isNaN(v) ? 50 : v; }
          if (s.key === "theme_mode") themeMode = s.value || "preset";
          if (s.key === "custom_theme_colors") {
            try {
              const c = JSON.parse(s.value);
              if (c.bg) customBg = c.bg;
              if (c.text) customText = c.text;
              if (c.accent) customAccent = c.accent;
              if (c.vfo) customVfo = c.vfo;
            } catch {}
          }
          if (s.key === "popup_notifications_enabled") popupNotifEnabled = s.value === "true";
        }
      }
      settingsLoaded = true;
    } catch {}
  }

  async function fetchLogbookList() {
    try {
      const res = await fetch("/api/logbooks/");
      if (res.ok) availableLogbooks = (await res.json()).map(d => d.name);
    } catch {}
  }

  async function fetchGlobalSettings() {
    try {
      const res = await fetch("/api/global-settings/");
      if (res.ok) {
        const data = await res.json();
        for (const s of data) {
          if (s.key === "my_callsign") global_my_callsign = s.value || "";
          if (s.key === "my_grid") global_my_grid = s.value || "";
          if (s.key === "default_rst") global_default_rst = s.value || "599";
          if (s.key === "qrz_username") global_qrz_username = s.value || "";
          if (s.key === "qrz_password") global_hasQrzPassword = !!s.value && s.value !== "";
          if (s.key === "hamalert_username") global_hamalert_username = s.value || "";
          if (s.key === "hamalert_password") global_hasHamalertPassword = !!s.value && s.value !== "";
          if (s.key === "flrig_enabled") global_flrig_enabled = s.value === "true";
          if (s.key === "flrig_simulate") global_flrig_simulate = s.value === "true";
          if (s.key === "flrig_host") global_flrig_host = s.value || "127.0.0.1";
          if (s.key === "flrig_port") global_flrig_port = s.value || "12345";
          if (s.key === "default_pick_mode") global_default_pick_mode = s.value !== "false";
          if (s.key === "default_port") global_default_port = s.value || "8073";
          if (s.key === "default_logbook_name") global_default_logbook_name = s.value || "rigbook";
          if (s.key === "open_browser_on_startup") global_open_browser_on_startup = s.value !== "false";
          if (s.key === "auto_shutdown_delay") global_auto_shutdown_delay = s.value || "300";
          if (s.key === "browser_url_override") global_browser_url_override = s.value || "";
          if (s.key === "shutdown_in_menu") shutdownInMenu = s.value === "true";
          if (s.key === "auto_shutdown_on_disconnect") autoShutdownOnDisconnect = s.value === "true";
          if (s.key === "disable_shutdown") disableShutdown = s.value === "true";
          if (s.key === "update_check_enabled") update_check_enabled = s.value !== "false";
        }
        globalSettingsLoaded = true;
      }
    } catch {}
  }

  async function saveGlobalSetting(key, value) {
    await fetch(`/api/global-settings/${key}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    });
    // Re-fetch per-logbook settings so placeholders and fallbacks update
    await fetchSettings();
    dispatch("saved");
  }

  async function loadUpdateCheck() {
    try {
      const res = await fetch("/api/update-check");
      if (res.ok) updateCheckResult = await res.json();
    } catch {}
    try {
      const res = await fetch("/api/update/platform");
      if (res.ok) {
        const data = await res.json();
        updateSupported = (data.supported && data.writable) || false;
        updateNotWritable = data.supported && !data.writable;
        updateBuildRepo = data.build_origin_repo || "";
        updateBuildSha = data.build_git_sha || "";
        updateGithubRepo = data.github_repo || "";
        updateOfficialBuild = data.build_github_actions || false;
        updateCustomRepo = !!updateBuildRepo && updateBuildRepo !== "EnigmaCurry/rigbook";
      }
    } catch {}
  }

  async function skipUpdate() {
    try {
      const res = await fetch("/api/update-check/skip", { method: "POST" });
      if (res.ok && updateCheckResult) {
        updateCheckResult.update_skipped = true;
        updateCheckResult = updateCheckResult; // trigger reactivity
      }
    } catch {}
  }

  function confirmAndApplyUpdate() {
    if (!updateCheckResult) return;
    if (confirm(`Update Rigbook from v${updateCheckResult.current} to v${updateCheckResult.latest}? The server will restart.`)) {
      applyUpdate();
    }
  }

  async function applyUpdate() {
    updateApplying = true;
    updateApplyError = "";
    try {
      const res = await fetch("/api/update/apply", { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        updateApplyError = data.detail || "Update failed";
        updateApplying = false;
        return;
      }
      if (data.status === "up_to_date") {
        updateApplyError = "Already up to date";
        updateApplying = false;
        return;
      }
      // Server is restarting — poll until it comes back
      await new Promise(r => setTimeout(r, 2000));
      for (let i = 0; i < 30; i++) {
        try {
          const check = await fetch("/api/version");
          if (check.ok) {
            window.location.reload();
            return;
          }
        } catch {}
        await new Promise(r => setTimeout(r, 1000));
      }
      updateApplyError = "Server did not come back after update — check manually";
      updateApplying = false;
    } catch (e) {
      updateApplyError = "Update failed: " + e.message;
      updateApplying = false;
    }
  }

  async function fetchUpdateCheck() {
    updateChecking = true;
    try {
      const res = await fetch("/api/update-check?bust=true");
      if (res.ok) updateCheckResult = await res.json();
    } catch {}
    updateChecking = false;
  }

  function formatTimeAgo(epochSecs) {
    const diff = Math.floor(Date.now() / 1000 - epochSecs);
    if (diff < 5) return "just now";
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  function formatTimeUntil(epochSecs) {
    const diff = Math.floor(epochSecs - Date.now() / 1000);
    if (diff <= 0) return "soon";
    if (diff < 60) return `in ${diff}s`;
    if (diff < 3600) return `in ${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `in ${Math.floor(diff / 3600)}h`;
    return `in ${Math.floor(diff / 86400)}d`;
  }

  async function logoutQrz() {
    try {
      await fetch("/api/settings/qrz_password", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: "" }),
      });
      hasQrzPassword = false;
      qrzStatus = null;
      qrz_password = "";
    } catch {}
  }

  async function checkQrz() {
    qrzChecking = true;
    qrzStatus = null;
    try {
      const res = await fetch("/api/qrz/status");
      if (res.ok) qrzStatus = await res.json();
    } catch {
      qrzStatus = { ok: false, error: "Request failed" };
    }
    qrzChecking = false;
  }

  async function fetchQsoCount() {
    try {
      const res = await fetch("/api/contacts/");
      if (res.ok) { const data = await res.json(); qsoCount = data.length; }
    } catch {}
  }

  async function fetchNoShutdown() {
    try {
      const res = await fetch("/api/version");
      if (res.ok) {
        const data = await res.json();
        noShutdown = !!data.no_shutdown;
        await tick();
        window.dispatchEvent(new Event("resize"));
      }
    } catch {}
  }

  async function toggleDisableShutdown() {
    await saveGlobalSetting("disable_shutdown", disableShutdown ? "true" : "false");
    await fetchNoShutdown();
  }

  onMount(() => {
    fetchSettings();
    fetchGlobalSettings();
    fetchLogbookList();
    fetchSpotStatus();
    fetchQsoCount();
    loadDbInfo();
    loadBackupStatus();
    fetchNoShutdown();
    fetchCacheStats();
    spotStatusInterval = setInterval(fetchSpotStatus, 5000);
  });

  onDestroy(() => {
    clearInterval(spotStatusInterval);
    flushPending();
  });
</script>

<div class="settings">
  <h2>Settings <span class="autosave-hint">(are saved automatically on change)</span></h2>

  {#if needsSetup}
    <p class="setup-hint">Enter your callsign and grid square to get started.</p>
  {/if}

  <div class="tab-bar">
    <button class="tab" class:active={activeTab === "station"} on:click={() => switchTab("station")}>Station</button>
    <button class="tab" class:active={activeTab === "features"} on:click={() => switchTab("features")}>Features</button>
    <button class="tab" class:active={activeTab === "appearance"} on:click={() => switchTab("appearance")}>Appearance</button>
    <button class="tab" class:active={activeTab === "updates"} on:click={() => switchTab("updates")}>Updates</button>
    <button class="tab" class:active={activeTab === "system"} on:click={() => switchTab("system")}>System</button>
    <button class="tab" class:active={activeTab === "global"} on:click={() => switchTab("global")}>Global</button>
  </div>

  {#if activeTab === "station"}
  <div class="tab-content" use:masonry>
  <section class="settings-section" data-section="station">
    <h3>Station</h3>
    <div class="setting-row">
      <label for="my_callsign">My Callsign{#if needsSetup && !my_callsign.trim()} <span class="required">*</span>{/if}{#if settingSources.my_callsign === "global"} <span class="global-hint">(global default)</span>{/if}</label>
      <input id="my_callsign" type="text" bind:value={my_callsign} on:input={onCallsignInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("my_callsign")} maxlength="10" autocomplete="off" style="text-transform: uppercase; max-width: 7rem" class:input-required={needsSetup && !my_callsign.trim()} placeholder={globalPlaceholders.my_callsign || ""} />
    </div>
    <div class="setting-row">
      <label for="my_grid">My Grid Square{#if needsSetup && !my_grid.trim()} <span class="required">*</span>{/if}{#if settingSources.my_grid === "global"} <span class="global-hint">(global default)</span>{/if}</label>
      <div class="grid-input-row">
        <input id="my_grid" type="text" bind:value={my_grid} on:input={onGridInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("my_grid")} autocomplete="off" maxlength="6" style="max-width: 7rem" class:input-required={needsSetup && !my_grid.trim()} placeholder={globalPlaceholders.my_grid || ""} />
        <button type="button" class="grid-picker-btn" on:click={() => showGridPicker = !showGridPicker} title="Pick from map">🌍</button>
      </div>
      {#if showGridPicker}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
        <div class="grid-picker-overlay" on:click|self={() => showGridPicker = false} on:keydown={e => e.key === "Escape" && (showGridPicker = false)} tabindex="0">
          <div class="grid-picker-modal">
            <div class="grid-picker-header">
              <span>Grid Square</span>
              <button type="button" class="grid-picker-close" on:click={() => showGridPicker = false}>✕</button>
            </div>
            <GridMap bind:value={my_grid} on:select={async () => { showGridPicker = false; await fieldSavers.my_grid(); }} />
          </div>
        </div>
      {/if}
    </div>
    <div class="setting-row">
      <label for="default_rst">Default RST</label>
      <input id="default_rst" type="text" bind:value={default_rst} on:input={onDefaultRstInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("default_rst")} autocomplete="off" style="max-width: 7rem" placeholder={globalPlaceholders.default_rst || ""} />
    </div>
  </section>

  <section class="settings-section">
    <h3>QRZ</h3>
    <div class="setting-row">
      <label for="rb-qrz-acct">QRZ Account{#if settingSources.qrz_username === "global"} <span class="global-hint">(global default)</span>{/if}</label>
      <input id="rb-qrz-acct" type="text" bind:value={qrz_username} on:input={() => markDirty("qrz_username")} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("qrz_username")} autocomplete="nope" data-1p-ignore data-lpignore="true" data-form-type="other" style="text-transform: uppercase; max-width: 10rem" placeholder={globalPlaceholders.qrz_username || global_qrz_username || effectiveSetting(my_callsign, "my_callsign")} />
      <span class="hint">Defaults to My Callsign if blank</span>
    </div>
    <div class="setting-row">
      <label for="rb-qrz-key">{hasQrzPassword ? "Change QRZ Password" : "QRZ Password"}</label>
      <input id="rb-qrz-key" type="text" class="secret-field" bind:value={qrz_password} autocomplete="new-password" data-1p-ignore data-lpignore="true" data-form-type="other" placeholder={hasQrzPassword ? "Leave blank to keep current" : "unset"} style="min-width: 8ch" />
    </div>
    <div class="setting-row">
      {#if qrz_password.trim()}<button type="button" class="check-now-btn" on:click={loginQrz}>Login</button>{/if}
      <span class="hint">{#if hasQrzPassword}Leave blank to remain unchanged{:else}Your QRZ account password{/if}</span>
    </div>
    {#if hasQrzPassword}
      <div class="setting-row qrz-status-row">
        <button class="theme-toggle" on:click={checkQrz} disabled={qrzChecking}>
          {qrzChecking ? "Checking..." : "Test QRZ Connection"}
        </button>
        <button class="theme-toggle" on:click={logoutQrz}>Logout</button>
        {#if qrzStatus}
          {#if qrzStatus.ok}
            <span class="qrz-ok">Connected as {qrzStatus.username}</span>
          {:else}
            <span class="qrz-error">{qrzStatus.error}</span>
          {/if}
        {/if}
      </div>
    {/if}
  </section>

  <section class="settings-section">
    <h3>flrig Connection</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={flrig_enabled} on:change={onFlrigEnabledChange} />
        Enable flrig
      </label>
    </div>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={flrig_simulate} on:change={onFlrigSimulateChange} disabled={!flrig_enabled} />
        Simulate flrig (no real radio)
      </label>
    </div>
    <div class="setting-row">
      <label for="flrig_host">flrig Host</label>
      <input id="flrig_host" type="text" bind:value={flrig_host} on:input={onFlrigHostInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("flrig_host")} autocomplete="off" disabled={!flrig_enabled || flrig_simulate} style="max-width: 7rem" placeholder={globalPlaceholders.flrig_host || ""} />
    </div>
    <div class="setting-row">
      <label for="flrig_port">flrig Port</label>
      <input id="flrig_port" type="text" bind:value={flrig_port} on:input={onFlrigPortInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("flrig_port")} autocomplete="off" inputmode="numeric" disabled={!flrig_enabled || flrig_simulate} style="max-width: 7rem" placeholder={globalPlaceholders.flrig_port || ""} />
    </div>
  </section>
  </div>
  {/if}

  {#if activeTab === "features"}
  <div class="tab-content" use:masonry>
  <section class="settings-section">
    <h3>Parks on the Air (POTA)</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={pota_enabled} on:change={onPotaEnabledChange} />
        Enable POTA
      </label>
    </div>
  </section>

  <section class="settings-section">
    <h3>Solar / Band Conditions</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={solar_enabled} on:change={onSolarEnabledChange} />
        Enable band conditions (N0NBH / hamqsl.com)
      </label>
    </div>
  </section>

  <section class="settings-section">
    <h3>SQL Query (read-only view)</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={sql_query_enabled} on:change={onSqlQueryEnabledChange} />
        Enable SQL query page
      </label>
    </div>
  </section>

  <section class="settings-section">
    <h3>Notifications</h3>
    <div class="setting-row toggle-row">
      {#if desktopNotifPermission === "denied"}
        <span class="hint">Desktop notifications blocked by browser. Allow notifications for this site in your browser settings.</span>
      {:else if desktopNotifPermission === "granted" && desktopNotifEnabled}
        <span style="font-size:0.85rem; color:var(--accent);">Desktop notifications are enabled</span>
        <button class="theme-toggle" on:click={disableDesktopNotifications}>Disable</button>
      {:else if desktopNotifPermission === "granted" && !desktopNotifEnabled}
        <span style="font-size:0.85rem; color:var(--text-muted);">Desktop notifications are disabled</span>
        <button class="theme-toggle" on:click={() => { desktopNotifEnabled = true; storageSet("desktop_notifications_enabled", "true"); }}>Enable</button>
      {:else}
        <button class="theme-toggle" on:click={enableDesktopNotifications}>Enable Desktop Notifications</button>
      {/if}
    </div>
    <p class="hint">In-app notifications are always enabled. Desktop notifications show browser popups when new alerts arrive.</p>
    <div class="setting-row toggle-row" style="margin-top: 0.5rem;">
      <label>
        <input type="checkbox" bind:checked={popupNotifEnabled} on:change={async () => { await saveSetting("popup_notifications_enabled", popupNotifEnabled ? "true" : "false"); dispatch("saved"); }} />
        Popup notifications
      </label>
    </div>
    <p class="hint">Show a modal dialog immediately when new notifications arrive. Harder to miss, but more intrusive.</p>
    <div class="setting-row toggle-row" style="margin-top: 0.5rem;">
      <button class="theme-toggle" on:click={sendTestNotification} disabled={testPending}>
        {testPending ? "Sending in 5s..." : "Send Test Notification"}
      </button>
    </div>
  </section>

  <section class="settings-section">
    <h3>Reverse Beacon Network (RBN)</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={rbn_enabled} on:change={onRbnEnabledChange} />
        Enable RBN Feed
      </label>
      <span class="conn-status">
        <span class="dot" class:green={spotStatus.rbn.connected} class:yellow={spotStatus.rbn.idle_stopped} class:red={spotStatus.rbn.enabled && !spotStatus.rbn.connected && !spotStatus.rbn.idle_stopped} class:off={!spotStatus.rbn.enabled}></span>
        {#if !spotStatus.rbn.enabled}Disabled{:else if spotStatus.rbn.idle_stopped}Idle — paused{:else if spotStatus.rbn.connected}Connected{:else}Connecting...{/if}
      </span>
    </div>
    <div class="setting-row toggle-row">
      <label><input type="checkbox" bind:checked={rbn_feed_cw} on:change={onRbnFeedCwChange} disabled={!rbn_enabled} /> CW (port 7000)</label>
      <label><input type="checkbox" bind:checked={rbn_feed_digital} on:change={onRbnFeedDigitalChange} disabled={!rbn_enabled} /> Digital (port 7001)</label>
    </div>
    <div class="setting-row">
      <label for="rbn_host">RBN Host</label>
      <input id="rbn_host" type="text" bind:value={rbn_host} on:input={onRbnHostInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("rbn_host")} autocomplete="off" disabled={!rbn_enabled} />
    </div>
    <div class="setting-row toggle-row">
      <label><input type="checkbox" bind:checked={skcc_skimmer_enabled} on:change={onSkccSkimmerEnabledChange} disabled={!rbn_enabled} /> Show SKCC Skimmer on Hunting page</label>
    </div>
    <div class="setting-row">
      <label for="skcc_distance">SKCC Skimmer max distance (miles)</label>
      <input id="skcc_distance" type="text" bind:value={skcc_skimmer_distance} on:input={onSkccSkimmerDistanceInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("skcc_skimmer_distance")} autocomplete="off" inputmode="numeric" disabled={!rbn_enabled || !skcc_skimmer_enabled} style="max-width: 7rem" />
    </div>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={rbn_idle_timeout_enabled} on:change={onRbnIdleTimeoutEnabledChange} disabled={!rbn_enabled} />
        Disconnect RBN when no web clients are connected to Rigbook
      </label>
    </div>
    <div class="setting-row">
      <label for="rbn_idle_timeout">Idle timeout (minutes)</label>
      <input id="rbn_idle_timeout" type="text" bind:value={rbn_idle_timeout_minutes} on:input={onRbnIdleTimeoutHoursInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("rbn_idle_timeout_minutes")} autocomplete="off" inputmode="numeric" disabled={!rbn_enabled || !rbn_idle_timeout_enabled} style="max-width: 7rem" />
    </div>
    <p class="hint">Uses {my_callsign.trim().toUpperCase() || "your callsign"} to authenticate.</p>
  </section>

  <section class="settings-section">
    <h3>HamAlert</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={hamalert_enabled} on:change={onHamalertEnabledChange} />
        Enable HamAlert Feed
      </label>
      <span class="conn-status">
        <span class="dot" class:green={spotStatus.hamalert.connected} class:red={spotStatus.hamalert.enabled && !spotStatus.hamalert.connected} class:off={!spotStatus.hamalert.enabled}></span>
        {#if !spotStatus.hamalert.enabled}Disabled{:else if spotStatus.hamalert.connected}Connected{:else}Connecting...{/if}
      </span>
    </div>
    <div class="setting-row">
      <label for="hamalert_host">Host</label>
      <input id="hamalert_host" type="text" bind:value={hamalert_host} on:input={onHamalertHostInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("hamalert_host")} autocomplete="off" disabled={!hamalert_enabled} />
    </div>
    <div class="setting-row">
      <label for="hamalert_port">Port</label>
      <input id="hamalert_port" type="text" bind:value={hamalert_port} on:input={onHamalertPortInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("hamalert_port")} autocomplete="off" inputmode="numeric" disabled={!hamalert_enabled} />
    </div>
    <div class="setting-row">
      <label for="hamalert_username">Telnet Username</label>
      <input id="hamalert_username" type="text" bind:value={hamalert_username} on:input={onHamalertUsernameInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("hamalert_username")} autocomplete="off" disabled={!hamalert_enabled} placeholder={globalPlaceholders.hamalert_username || ""} />
    </div>
    <div class="setting-row">
      <label for="hamalert_password">{hasHamalertPassword ? "Change Telnet Password" : "Telnet Password"}</label>
      <div class="grid-input-row">
        <input id="hamalert_password" type="text" class="secret-field" bind:value={hamalert_password} autocomplete="off" disabled={!hamalert_enabled} placeholder={hasHamalertPassword ? "Leave blank to keep current" : ""} />
        <button type="button" class="theme-toggle" on:click={loginHamalert} disabled={!hamalert_password.trim()}>Login</button>
      </div>
    </div>
  </section>
  </div>
  {/if}

  {#if activeTab === "appearance"}
  <div class="tab-content" use:masonry>
  <section class="settings-section">
    <h3>Maps</h3>
    <div class="map-preview" bind:this={previewEl}></div>
    <div class="setting-row">
      <label for="map_theme">Map Tiles</label>
      <select id="map_theme" bind:value={map_theme} on:change={onMapThemeChange}>
        {#each TILE_THEMES as t}
          <option value={t.value}>{t.label}</option>
        {/each}
      </select>
    </div>
    {#if map_theme === "custom"}
      <div class="setting-row">
        <label for="map_custom_url">Tile URL</label>
        <input id="map_custom_url" type="text" bind:value={map_custom_url} on:input={onMapCustomUrlInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("map_custom_url")} placeholder="https://&#123;s&#125;.tile.example.com/&#123;z&#125;/&#123;x&#125;/&#123;y&#125;.png" />
      </div>
    {/if}
    <div class="setting-row toggle-row">
      <label>Colors</label>
      <div class="theme-mode-switch">
        <button class="mode-btn" class:active={spotMapColorMode === "preset"} on:click={() => { spotMapColorMode = "preset"; onMapColorModeChange(); }}>Preset</button>
        <button class="mode-btn" class:active={spotMapColorMode === "custom"} on:click={() => { spotMapColorMode = "custom"; onMapColorModeChange(); }}>Custom</button>
      </div>
    </div>
    {#if spotMapColorMode === "preset"}
    <div class="setting-row">
      <label for="map_color_preset">Color Preset</label>
      <select id="map_color_preset" bind:value={spotMapPreset} on:change={onMapPresetChange}>
        {#each MAP_COLOR_PRESET_NAMES as name}
          <option value={name}>{MAP_COLOR_PRESETS[name].label}</option>
        {/each}
      </select>
    </div>
    {:else}
    <div class="color-pickers spot-map-colors">
      <div class="color-picker-group">
        <label>QTH</label>
        <hex-color-picker use:mapColorPicker={{ getValue: () => spotMapQth, setValue: (v) => { spotMapQth = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={spotMapQth} on:input={onMapColorInput} on:blur={onMapColorCommit} maxlength="7" />
        <select class="stroke-select" bind:value={spotMapStrokeQth} on:change={onMapColorCommit}><option value="black">Black outline</option><option value="white">White outline</option></select>
      </div>
      <div class="color-picker-group">
        <label>Station</label>
        <hex-color-picker use:mapColorPicker={{ getValue: () => spotMapStation, setValue: (v) => { spotMapStation = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={spotMapStation} on:input={onMapColorInput} on:blur={onMapColorCommit} maxlength="7" />
        <select class="stroke-select" bind:value={spotMapStrokeStation} on:change={onMapColorCommit}><option value="black">Black outline</option><option value="white">White outline</option></select>
      </div>
      <div class="color-picker-group">
        <label>Spotter</label>
        <hex-color-picker use:mapColorPicker={{ getValue: () => spotMapSpotter, setValue: (v) => { spotMapSpotter = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={spotMapSpotter} on:input={onMapColorInput} on:blur={onMapColorCommit} maxlength="7" />
        <select class="stroke-select" bind:value={spotMapStrokeSpotter} on:change={onMapColorCommit}><option value="black">Black outline</option><option value="white">White outline</option></select>
      </div>
      <div class="color-picker-group">
        <label>2nd Spotter</label>
        <hex-color-picker use:mapColorPicker={{ getValue: () => spotMapSecondary, setValue: (v) => { spotMapSecondary = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={spotMapSecondary} on:input={onMapColorInput} on:blur={onMapColorCommit} maxlength="7" />
        <select class="stroke-select" bind:value={spotMapStrokeSecondary} on:change={onMapColorCommit}><option value="black">Black outline</option><option value="white">White outline</option></select>
      </div>
    </div>
    {/if}
  </section>
  <section class="settings-section">
    <h3>Theme</h3>
    <p class="hint">Theme changes sync live to all open windows. Try opening Rigbook side-by-side in another window to preview your changes on any page.</p>
    <div class="setting-row toggle-row">
      <label>Mode</label>
      <div class="theme-mode-switch">
        <button class="mode-btn" class:active={themeMode === "preset"} on:click={() => { themeMode = "preset"; onThemeModeChange(); }}>Preset</button>
        <button class="mode-btn" class:active={themeMode === "custom"} on:click={() => { themeMode = "custom"; onThemeModeChange(); }}>Custom</button>
      </div>
    </div>
    {#if themeMode === "preset"}
    <div class="setting-row">
      <label for="theme_select">Theme</label>
      <select id="theme_select" bind:value={theme} on:change={onThemeChange}>
        {#each THEME_NAMES as t}
          <option value={t}>{THEMES[t].label}{t !== "dark" && t !== "light" ? ` (${THEMES[t].base})` : ""}</option>
        {/each}
      </select>
      <button class="contrast-reset" on:click={resetSliders} disabled={themeContrast === 50 && themeBrightness === 50 && themeHue === 0 && themeSaturation === 50}>Reset Sliders</button>
    </div>
    {:else}
    <div class="color-pickers">
      <div class="color-picker-group">
        <label>Background</label>
        <hex-color-picker use:colorPicker={{ getValue: () => customBg, setValue: (v) => { customBg = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={customBg} on:input={onCustomColorInput} on:blur={onCustomColorCommit} maxlength="7" />
      </div>
      <div class="color-picker-group">
        <label>Text</label>
        <hex-color-picker use:colorPicker={{ getValue: () => customText, setValue: (v) => { customText = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={customText} on:input={onCustomColorInput} on:blur={onCustomColorCommit} maxlength="7" />
      </div>
      <div class="color-picker-group">
        <label>Accent</label>
        <hex-color-picker use:colorPicker={{ getValue: () => customAccent, setValue: (v) => { customAccent = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={customAccent} on:input={onCustomColorInput} on:blur={onCustomColorCommit} maxlength="7" />
      </div>
      <div class="color-picker-group">
        <label>VFO</label>
        <hex-color-picker use:colorPicker={{ getValue: () => customVfo, setValue: (v) => { customVfo = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={customVfo} on:input={onCustomColorInput} on:blur={onCustomColorCommit} maxlength="7" />
      </div>
    </div>
    {/if}
    <div class="slider-pair">
      <div class="slider-group">
        <label for="contrast_slider">Contrast <span class="slider-value">{themeContrast}</span></label>
        <div class="slider-control">
          <input id="contrast_slider" type="range" min="40" max="60" bind:value={themeContrast} on:input={onContrastInput} on:change={onContrastCommit} />
        </div>
      </div>
      <div class="slider-group">
        <label for="brightness_slider">Brightness <span class="slider-value">{themeBrightness}</span></label>
        <div class="slider-control">
          <input id="brightness_slider" type="range" min="40" max="60" bind:value={themeBrightness} on:input={onBrightnessInput} on:change={onBrightnessCommit} />
        </div>
      </div>
    </div>
    <div class="slider-pair">
      <div class="slider-group">
        <label for="hue_slider">Hue Shift <span class="slider-value">{themeHue}°</span></label>
        <div class="slider-control">
          <input id="hue_slider" type="range" min="0" max="360" bind:value={themeHue} on:input={onHueInput} on:change={onHueCommit} class="hue-range" />
        </div>
      </div>
      <div class="slider-group">
        <label for="saturation_slider">Saturation <span class="slider-value">{themeSaturation}</span></label>
        <div class="slider-control">
          <input id="saturation_slider" type="range" min="0" max="100" bind:value={themeSaturation} on:input={onSaturationInput} on:change={onSaturationCommit} />
        </div>
      </div>
    </div>
  </section>
  <section class="settings-section" data-section="content">
    <h3>Content</h3>
    <div class="setting-row">
      <label for="custom_header">Custom Header</label>
      <input id="custom_header" type="text" bind:value={custom_header} on:input={onCustomHeaderInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("custom_header")} autocomplete="off" placeholder={my_callsign.trim().toUpperCase() || "Callsign"} />
      <span class="hint">Replaces the callsign in the header. Leave blank to show your callsign.</span>
    </div>
    <div class="setting-row">
      <label for="default_page">Home Page</label>
      <select id="default_page" bind:value={default_page} on:change={onDefaultPageChange}>
        <option value="log">Logbook / Hunting</option>
        <option value="hunting">Hunting</option>
        <option value="spots">Spots</option>
        <option value="parks">Parks</option>
        <option value="notifications">Notifications</option>
        <option value="conditions">Conditions</option>
      </select>
    </div>
  </section>
  <section class="settings-section">
    <h3>Wide Mode</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={wide_mode_enabled} on:change={onWideModeEnabledChange} />
        Wide Mode
      </label>
    </div>
    <div class="setting-row">
      <label for="wide_breakpoint">Breakpoint: {wide_breakpoint}px</label>
      <input id="wide_breakpoint" type="range" min="1200" max="2500" step="50" bind:value={wide_breakpoint} on:input={onWideBreakpointInput} on:change={() => onFieldBlur("wide_breakpoint")} disabled={!wide_mode_enabled} />
    </div>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={logbook_right} on:change={onLogbookRightChange} disabled={!wide_mode_enabled} />
        Logbook on right side
      </label>
    </div>
  </section>
  </div>
  {/if}

  {#if activeTab === "updates"}
  <div class="tab-content" use:masonry>
  <section class="settings-section">
    <h3>Update Checker</h3>
    {#if updateOfficialBuild}
      <div class="setting-row toggle-row">
        <label>
          <input type="checkbox" bind:checked={update_check_enabled} on:change={onUpdateCheckEnabledChange} />
          Check for new Rigbook releases on GitHub
        </label>
      </div>
      {#if update_check_enabled && updateCheckResult}
        <div class="update-status">
          <div>Current version: <strong>v{updateCheckResult.current}</strong>{#if updateBuildSha}
            (<a href="https://github.com/{updateGithubRepo}/commit/{updateBuildSha}" target="_blank" rel="noopener" class="sha-link">{updateBuildSha}</a>){/if}
          {#if updateCheckResult.is_dev}
            — Development version — update checker is disabled
          {:else if updateCheckResult.is_exact}
            — You're running the latest version
          {:else if updateCheckResult.latest && !updateCheckResult.update_available}
            — You're ahead of the latest release (v{updateCheckResult.latest})
          {:else if !updateCheckResult.latest}
            — Unable to check for updates
          {/if}
          </div>
          {#if updateCheckResult.update_available && !updateCheckResult.update_skipped}
            <div><span class="update-available">Update available: v{updateCheckResult.latest}</span></div>
            <div class="update-actions">
              {#if updateSupported}
                <button class="check-now-btn apply-update-btn" on:click={confirmAndApplyUpdate} disabled={updateApplying}>
                  {updateApplying ? "Updating…" : "Apply Update"}
                </button>
                <button class="check-now-btn" on:click={skipUpdate}>Skip</button>
              {:else}
                <a href={updateCheckResult.url} target="_blank" rel="noopener" class="update-available">Download</a>
                {#if updateNotWritable}
                  <span class="update-error">In-app update unavailable: no write permission to the binary location</span>
                {/if}
              {/if}
              {#if updateApplyError}
                <span class="update-error">{updateApplyError}</span>
              {/if}
            </div>
          {:else if updateCheckResult.update_skipped}
            <div>v{updateCheckResult.latest} available (skipped)</div>
            <div class="update-actions">
              {#if updateSupported}
                <button class="check-now-btn apply-update-btn" on:click={confirmAndApplyUpdate} disabled={updateApplying}>
                  {updateApplying ? "Updating…" : "Apply Update"}
                </button>
              {:else}
                <a href={updateCheckResult.url} target="_blank" rel="noopener" class="update-available">Download</a>
                {#if updateNotWritable}
                  <span class="update-error">In-app update unavailable: no write permission to the binary location</span>
                {/if}
              {/if}
              {#if updateApplyError}
                <span class="update-error">{updateApplyError}</span>
              {/if}
            </div>
          {/if}
        </div>
        <div class="update-check-meta">
          {#if updateCheckResult.checked_at}
            Checked {formatTimeAgo(updateCheckResult.checked_at)}{#if updateCheckResult.next_check_at}, next check {formatTimeUntil(updateCheckResult.next_check_at)}{/if}
          {/if}
          <button class="check-now-btn" on:click={fetchUpdateCheck} disabled={updateChecking}>
            {updateChecking ? "Checking…" : "Check now"}
          </button>
        </div>
      {/if}
      {#if updateCustomRepo}
        <div class="update-custom-repo-warning">
          Warning: using custom update source <a href="https://github.com/{updateBuildRepo}" target="_blank" rel="noopener"><strong>{updateBuildRepo}</strong></a>
        </div>
      {/if}
    {:else}
      <div class="update-status">
        Version: <strong>v{updateCheckResult?.current || '...'}</strong>{#if updateBuildSha}
          (<a href="https://github.com/{updateGithubRepo}/commit/{updateBuildSha}" target="_blank" rel="noopener" class="sha-link">{updateBuildSha}</a>){/if}
      </div>
      <p class="hint">Update checking is disabled for local builds.</p>
    {/if}
  </section>
  </div>
  {/if}

  {#if activeTab === "system"}
  <div class="tab-content" use:masonry>

  <section class="settings-section">
    <h3>Backup</h3>
    {#if dbInfo}
      <p class="hint">Database: {dbInfo.path} ({formatSize(dbInfo.size)})</p>
      <p class="hint">Backups: {dbInfo.directory}</p>
    {/if}
    <div class="setting-row">
      <button on:click={performBackup} disabled={backingUp}>
        {backingUp ? "Backing up..." : "Backup Now"}
      </button>
    </div>
    {#if backupMessage}
      <p class="hint" class:danger-error={backupMessageType === "error"} style={backupMessageType === "success" ? "color: var(--accent)" : ""}>{backupMessage}</p>
    {/if}
    <div class="setting-row toggle-row">
      <label class="toggle-label">
        <input type="checkbox" bind:checked={autoBackupEnabled} on:change={saveAutoBackupSettings} />
        Auto-backup
      </label>
    </div>
    {#if autoBackupEnabled}
      <div class="setting-row">
        <label>Interval (hours)</label>
        <input type="number" min="1" max="720" bind:value={autoBackupHours} on:input={saveAutoBackupSettings} style="width: 5rem" />
      </div>
      <div class="setting-row">
        <label>Keep max</label>
        <input type="number" min="1" max="100" bind:value={autoBackupMax} on:input={saveAutoBackupSettings} style="width: 5rem" />
      </div>
    {/if}
    {#if backupStatus}
      <p class="hint">
        {#if backupStatus.auto_enabled}
          Last auto-backup: {timeAgo(backupStatus.last_backup)} — Next: {formatDue(backupStatus.next_due)}
        {:else}
          Auto-backup disabled
        {/if}
        {#if backupStatus.auto_backup_count > 0 || backupStatus.manual_backup_count > 0}
          — {backupStatus.auto_backup_count} auto, {backupStatus.manual_backup_count} manual
        {/if}
      </p>
    {/if}
  </section>

  {#if !noShutdown}
  <section class="settings-section">
    <h3>Shutdown</h3>
    <p class="hint">Connected clients: {clientCount}</p>
    {#if clientCount > 1}
      <div class="setting-row">
        <button class="warning-btn" on:click={disconnectOthers}>Disconnect all other clients</button>
      </div>
    {/if}
    <div class="setting-row">
      <button class="danger-btn" on:click={shutdownServer}>Shutdown Now</button>
    </div>
  </section>
  {/if}

  {#if logbookName}
    <section class="settings-section danger-zone">
      <h3>Danger Zone</h3>
      <div class="setting-row">
        <label for="danger-confirm">Type <strong>{logbookName}</strong> to enable the Danger Zone</label>
        <input id="danger-confirm" type="text" bind:value={dangerConfirmName} placeholder={logbookName} autocomplete="off" />
      </div>
      <div class="danger-separator"></div>
      <p class="danger-text">Delete all QSOs from <strong>{logbookName}</strong> but keep the logbook and settings.</p>
      {#if clearError}
        <p class="danger-error">{clearError}</p>
      {/if}
      <div class="setting-row">
        <button class="danger-btn" on:click={clearAllContacts} disabled={clearing || dangerConfirmName !== logbookName || qsoCount === 0}>
          {clearing ? "Clearing..." : qsoCount === 0 ? "No QSOs to clear" : "Clear All QSOs"}
        </button>
      </div>
      <div class="danger-separator"></div>
      <p class="danger-text">Permanently delete the logbook <strong>{logbookName}</strong> and all its data. This cannot be undone.</p>
      {#if deleteError}
        <p class="danger-error">{deleteError}</p>
      {/if}
      <div class="setting-row">
        <button class="danger-btn" on:click={deleteLogbook} disabled={deleting || dangerConfirmName !== logbookName}>
          {deleting ? "Deleting..." : "Delete Logbook"}
        </button>
      </div>
    </section>
  {/if}
  </div>
  {/if}

  {#if activeTab === "global"}
  <p class="hint">Global defaults are used when a per-logbook setting is not set. Changes here apply across all logbooks.</p>
  <div class="tab-content" use:masonry>

  <section class="settings-section">
    <h3>Station Defaults</h3>
    <div class="setting-row">
      <label for="global_my_callsign">Default Callsign</label>
      <input id="global_my_callsign" type="text" bind:value={global_my_callsign} on:blur={() => saveGlobalSetting("my_callsign", global_my_callsign.trim().toUpperCase())} maxlength="10" autocomplete="off" style="text-transform: uppercase; max-width: 7rem" />
    </div>
    <div class="setting-row">
      <label for="global_my_grid">Default Grid Square</label>
      <input id="global_my_grid" type="text" bind:value={global_my_grid} on:input={() => { global_my_grid = normalizeGrid(global_my_grid.slice(0, 6)); }} on:blur={() => { global_my_grid = normalizeGrid(global_my_grid.trim()); saveGlobalSetting("my_grid", global_my_grid); }} autocomplete="off" maxlength="6" style="max-width: 7rem" />
    </div>
    <div class="setting-row">
      <label for="global_default_rst">Default RST</label>
      <input id="global_default_rst" type="text" bind:value={global_default_rst} on:blur={() => saveGlobalSetting("default_rst", global_default_rst.trim())} maxlength="3" autocomplete="off" style="max-width: 4rem" />
    </div>
  </section>

  <section class="settings-section">
    <h3>Default Credentials</h3>
    <div class="setting-row">
      <label for="rb-def-qrz-acct">Default QRZ Account</label>
      <input id="rb-def-qrz-acct" type="text" bind:value={global_qrz_username} on:blur={() => saveGlobalSetting("qrz_username", global_qrz_username.trim().toUpperCase())} autocomplete="nope" data-1p-ignore data-lpignore="true" data-form-type="other" style="text-transform: uppercase; max-width: 14rem" />
      <span class="hint">Defaults to Default Callsign if blank</span>
    </div>
    <div class="setting-row">
      <label>Default QRZ Password</label>
      {#if global_hasQrzPassword}
        <span class="hint">Saved</span>
        <button class="check-now-btn" on:click={async () => { await saveGlobalSetting("qrz_password", ""); global_hasQrzPassword = false; global_qrz_password = ""; }}>Clear</button>
      {:else}
        <input id="rb-def-qrz-key" type="text" class="secret-field" bind:value={global_qrz_password} placeholder="QRZ password" autocomplete="new-password" data-1p-ignore data-lpignore="true" data-form-type="other" style="max-width: 14rem" />
        <button class="check-now-btn" on:click={async () => { if (global_qrz_password.trim()) { await saveGlobalSetting("qrz_password", global_qrz_password.trim()); global_hasQrzPassword = true; global_qrz_password = ""; } }}>Save</button>
      {/if}
    </div>
    <div class="setting-row">
      <label for="rb-def-ha-acct">Default HamAlert Account</label>
      <input id="rb-def-ha-acct" type="text" bind:value={global_hamalert_username} on:blur={() => saveGlobalSetting("hamalert_username", global_hamalert_username.trim())} autocomplete="nope" data-1p-ignore data-lpignore="true" data-form-type="other" style="max-width: 14rem" />
    </div>
    <div class="setting-row">
      <label>Default HamAlert Password</label>
      {#if global_hasHamalertPassword}
        <span class="hint">Saved</span>
        <button class="check-now-btn" on:click={async () => { await saveGlobalSetting("hamalert_password", ""); global_hasHamalertPassword = false; global_hamalert_password = ""; }}>Clear</button>
      {:else}
        <input id="rb-def-ha-key" type="text" class="secret-field" bind:value={global_hamalert_password} placeholder="HamAlert password" autocomplete="new-password" data-1p-ignore data-lpignore="true" data-form-type="other" style="max-width: 14rem" />
        <button class="check-now-btn" on:click={async () => { if (global_hamalert_password.trim()) { await saveGlobalSetting("hamalert_password", global_hamalert_password.trim()); global_hasHamalertPassword = true; global_hamalert_password = ""; } }}>Save</button>
      {/if}
    </div>
  </section>

  <section class="settings-section">
    <h3>Default Radio Connection</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={global_flrig_enabled} on:change={() => saveGlobalSetting("flrig_enabled", global_flrig_enabled ? "true" : "false")} />
        Default Enable flrig
      </label>
    </div>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={global_flrig_simulate} on:change={() => saveGlobalSetting("flrig_simulate", global_flrig_simulate ? "true" : "false")} />
        Default Simulate flrig
      </label>
    </div>
    <div class="setting-row">
      <label for="global_flrig_host">Default flrig Host</label>
      <input id="global_flrig_host" type="text" bind:value={global_flrig_host} on:blur={() => saveGlobalSetting("flrig_host", global_flrig_host.trim())} autocomplete="off" style="max-width: 12rem" />
    </div>
    <div class="setting-row">
      <label for="global_flrig_port">Default flrig Port</label>
      <input id="global_flrig_port" type="text" bind:value={global_flrig_port} on:blur={() => saveGlobalSetting("flrig_port", global_flrig_port.trim())} autocomplete="off" style="max-width: 6rem" />
    </div>
  </section>

  <section class="settings-section">
    <h3>Logbook</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={global_default_pick_mode} on:change={() => saveGlobalSetting("default_pick_mode", global_default_pick_mode ? "true" : "false")} />
        Ask which logbook to open on start
      </label>
    </div>
    <div class="setting-row">
      <label for="global_default_logbook">Default Logbook Name</label>
      {#if availableLogbooks.length > 0}
        <select id="global_default_logbook" bind:value={global_default_logbook_name} on:change={() => saveGlobalSetting("default_logbook_name", global_default_logbook_name)} style="max-width: 14rem">
          {#each availableLogbooks as name}
            <option value={name}>{name}</option>
          {/each}
        </select>
      {:else}
        <span class="hint">No logbooks exist yet</span>
      {/if}
      <span class="hint">Logbook opened when running rigbook without arguments</span>
    </div>
  </section>

  <section class="settings-section">
    <h3>Network</h3>
    <div class="setting-row">
      <label for="global_default_port">Default Port</label>
      <input id="global_default_port" type="text" bind:value={global_default_port} on:blur={() => saveGlobalSetting("default_port", global_default_port.trim())} autocomplete="off" style="max-width: 6rem" />
    </div>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={global_open_browser_on_startup} on:change={() => saveGlobalSetting("open_browser_on_startup", global_open_browser_on_startup ? "true" : "false")} />
        Open browser on startup (unless <code>--no-browser</code> argument given)
      </label>
    </div>
    <div class="setting-row">
      <label for="global_browser_url">Browser URL Override</label>
      <input id="global_browser_url" type="text" bind:value={global_browser_url_override} on:blur={() => saveGlobalSetting("browser_url_override", global_browser_url_override.trim())} autocomplete="off" placeholder="e.g. https://rigbook.local" style="max-width: 20rem" disabled={!global_open_browser_on_startup} />
      <span class="hint">Custom URL opened in browser on startup (for proxies/TLS). Leave blank for http://127.0.0.1:{global_default_port || "8073"}.</span>
    </div>
  </section>

  <section class="settings-section">
    <h3>Cache</h3>
    <p class="hint">Cached data: QRZ callsign lookups, SKCC member list. Clearing forces fresh lookups on next use.</p>
    {#if qrzCacheStats || skccCacheStats || solarCacheStats}
    <div class="cache-stats-grid">
      {#if qrzCacheStats}
      <div class="cache-stat-card">
        <h4>QRZ</h4>
        <div class="stat-row"><span class="stat-label">Cached lookups</span><span class="stat-value">{qrzCacheStats.valid_entries}</span></div>
        <div class="stat-row"><span class="stat-label">Found</span><span class="stat-value">{qrzCacheStats.found_entries}</span></div>
        <div class="stat-row"><span class="stat-label">Not found</span><span class="stat-value">{qrzCacheStats.not_found_entries}</span></div>
        <div class="stat-row"><span class="stat-label">Expired</span><span class="stat-value">{qrzCacheStats.expired_entries}</span></div>
        <div class="stat-row"><span class="stat-label">TTL</span><span class="stat-value">{Math.round(qrzCacheStats.ttl_seconds / 86400)}d</span></div>
      </div>
      {/if}
      {#if skccCacheStats}
      <div class="cache-stat-card">
        <h4>SKCC</h4>
        <div class="stat-row"><span class="stat-label">Cached members</span><span class="stat-value">{skccCacheStats.valid_entries.toLocaleString()}</span></div>
        <div class="stat-row"><span class="stat-label">Expired</span><span class="stat-value">{skccCacheStats.expired_entries.toLocaleString()}</span></div>
        <div class="stat-row"><span class="stat-label">TTL</span><span class="stat-value">{Math.round(skccCacheStats.ttl_seconds / 3600)}h</span></div>
      </div>
      {/if}
      {#if solarCacheStats}
      <div class="cache-stat-card">
        <h4>Solar (HamQSL)</h4>
        <div class="stat-row"><span class="stat-label">Status</span><span class="stat-value">{solarCacheStats.cached ? "Cached" : "Empty"}</span></div>
        {#if solarCacheStats.age_seconds != null}
        <div class="stat-row"><span class="stat-label">Age</span><span class="stat-value">{solarCacheStats.age_seconds < 60 ? solarCacheStats.age_seconds + "s" : Math.round(solarCacheStats.age_seconds / 60) + "m"}</span></div>
        {/if}
        <div class="stat-row"><span class="stat-label">TTL</span><span class="stat-value">{Math.round(solarCacheStats.ttl_seconds / 60)}m</span></div>
      </div>
      {/if}
    </div>
    {/if}
    <div class="setting-row toggle-row">
      <button class="theme-toggle" on:click={clearExpiredCache}>Clear Expired Only</button>
      <button class="theme-toggle" on:click={clearCache}>Clear All Cache</button>
    </div>
  </section>

  <section class="settings-section">
    <h3>Shutdown</h3>
    <div class="setting-row toggle-row">
      <label class="toggle-label">
        <input type="checkbox" bind:checked={disableShutdown} on:change={toggleDisableShutdown} />
        Disable shutdown
      </label>
    </div>
    <div class="setting-row toggle-row">
      <label class="toggle-label">
        <input type="checkbox" bind:checked={autoShutdownOnDisconnect} on:change={() => saveGlobalSetting("auto_shutdown_on_disconnect", autoShutdownOnDisconnect ? "true" : "false")} disabled={disableShutdown} />
        Shutdown automatically when no clients are connected
      </label>
    </div>
    <div class="setting-row">
      <label for="global_shutdown_delay">Shutdown delay (seconds)</label>
      <input id="global_shutdown_delay" type="number" min="5" bind:value={global_auto_shutdown_delay} on:blur={() => { const v = Math.max(5, parseInt(global_auto_shutdown_delay) || 300); global_auto_shutdown_delay = String(v); saveGlobalSetting("auto_shutdown_delay", String(v)); }} autocomplete="off" style="max-width: 5rem" disabled={disableShutdown || !autoShutdownOnDisconnect} />
    </div>
    <p class="hint">Shuts down the server after {global_auto_shutdown_delay} consecutive seconds with no connected clients.</p>
    <div class="setting-row toggle-row">
      <label class="toggle-label">
        <input type="checkbox" bind:checked={shutdownInMenu} on:change={() => { saveGlobalSetting("shutdown_in_menu", shutdownInMenu ? "true" : "false"); }} disabled={disableShutdown} />
        Add Shutdown action to the main menu
      </label>
    </div>
  </section>
  </div>
  {/if}
</div>

<style>
  .settings {
  }

  .cache-stats-grid {
    display: flex;
    gap: 1rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
  }
  .cache-stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.6rem 1rem;
    min-width: 10rem;
    color: var(--text);
  }
  .cache-stat-card h4 {
    margin: 0 0 0.4rem 0;
    font-size: 0.85rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .stat-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    font-size: 0.85rem;
    padding: 0.1rem 0;
  }
  .stat-label {
    color: var(--text-muted);
  }
  .stat-value {
    font-weight: 600;
    color: var(--text);
  }

  .tab-bar {
    display: flex;
    gap: 0;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border);
  }

  .tab {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text);
    padding: 0.5rem 0.5rem;
    font-size: 0.8rem;
    font-weight: bold;
    cursor: pointer;
    font-family: inherit;
  }

  .tab:hover {
    background: var(--accent);
    color: var(--accent-text);
    font-weight: bold;
  }

  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }

  .tab.active:hover {
    background: var(--accent);
    color: var(--accent-text);
  }

  .tab-content {
    display: flex;
    flex-wrap: wrap;
    gap: 0 1rem;
  }

  /* Single-column fallback (no masonry columns created) */
  .tab-content > :global(.settings-section) {
    width: 100%;
  }

  :global(.masonry-col) {
    flex: 1;
    min-width: 0;
  }

  h2 {
    color: var(--accent);
    font-size: 1.2rem;
    margin: 0 0 1rem 0;
  }

  .autosave-hint {
    font-size: 0.7rem;
    font-weight: normal;
    color: var(--text-muted);
  }

  .map-preview {
    height: 300px;
    border-radius: 4px;
    border: 1px solid var(--border);
    margin-top: 0.75rem;
    margin-bottom: 0.75rem;
  }

  .spot-map-colors {
    margin-top: 0.75rem;
  }

  .stroke-select {
    font-size: 0.7rem;
    padding: 0.15rem 0.3rem;
    width: 5.5rem;
  }

  :global(.qth-label) {
    background: rgba(0, 0, 0, 0.7);
    color: #fff;
    border: none;
    font-size: 0.7rem;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 3px;
    box-shadow: none;
  }
  :global(.qth-label::before) {
    display: none;
  }

  .settings-section {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
  }
  .settings-section:global(.highlight-flash) {
    animation: highlight-pulse 1.5s ease-out;
  }
  @keyframes highlight-pulse {
    0%, 10% { border-color: var(--accent); box-shadow: 0 0 8px color-mix(in srgb, var(--accent) 40%, transparent); }
    30% { border-color: var(--border); box-shadow: none; }
    50%, 60% { border-color: var(--accent); box-shadow: 0 0 8px color-mix(in srgb, var(--accent) 40%, transparent); }
    100% { border-color: var(--border); box-shadow: none; }
  }

  h3 {
    color: var(--accent);
    font-size: 0.9rem;
    margin: 0 0 0.75rem 0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .setting-row {
    margin-bottom: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .grid-input-row {
    display: flex;
    gap: 0.25rem;
  }
  .grid-input-row input {
    flex: 1;
  }
  .grid-picker-btn {
    background: var(--bg-card);
    border: 1px solid var(--border-input);
    border-radius: 3px;
    cursor: pointer;
    font-size: 1rem;
    padding: 0 0.4rem;
  }
  .grid-picker-btn:hover {
    border-color: var(--accent);
  }
  .grid-picker-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }
  .grid-picker-modal {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem;
    width: 95vw;
    height: 90vh;
    overflow: auto;
  }
  .grid-picker-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
    font-weight: bold;
  }
  .grid-picker-close {
    background: none;
    border: none;
    color: var(--text);
    font-size: 1.2rem;
    cursor: pointer;
  }
  .grid-picker-close:hover {
    color: var(--accent);
  }


  label {
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  input:not([type="range"]):not([type="checkbox"]), select {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 0.4rem 0.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    border-radius: 3px;
    width: 100%;
    max-width: 20rem;
  }

  input:not([type="range"]):not([type="checkbox"]):focus, select:focus {
    outline: none;
    border-color: var(--accent);
  }

  input[type="range"] {
    width: 100%;
    max-width: 20rem;
    accent-color: var(--accent);
  }

  input:disabled, select:disabled {
    opacity: 0.4;
  }

  input[type="checkbox"] {
    accent-color: var(--accent);
  }

  .color-pickers {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }

  @media (max-width: 360px) {
    .color-pickers {
      grid-template-columns: 1fr;
    }
  }

  .color-picker-group {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.4rem;
  }

  .color-picker-group label {
    font-size: 0.8rem;
    color: var(--text-muted);
    font-weight: bold;
  }

  .color-picker-group hex-color-picker {
    width: 120px;
    height: 120px;
  }

  .color-hex-input {
    width: 5.5rem !important;
    text-align: center;
    font-size: 0.8rem !important;
  }

  .slider-pair {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .slider-group {
    flex: 1;
    min-width: 10rem;
  }
  .slider-group label {
    display: block;
    font-size: 0.85rem;
    margin-bottom: 0.25rem;
    color: var(--text-muted);
  }
  .slider-value {
    opacity: 0.6;
    font-size: 0.8rem;
  }
  .hue-range {
    -webkit-appearance: none;
    appearance: none;
    height: 6px;
    border-radius: 3px;
    background: linear-gradient(to right, #ff0000, #ffff00, #00ff00, #00ffff, #0000ff, #ff00ff, #ff0000);
    outline: none;
  }
  .hue-range::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--text);
    border: 2px solid var(--bg);
    cursor: pointer;
  }
  .hue-range::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--text);
    border: 2px solid var(--bg);
    cursor: pointer;
  }
  .slider-control {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .slider-control input[type="range"] {
    flex: 1;
    accent-color: var(--accent);
  }
  .contrast-reset {
    font-family: inherit;
    font-size: 0.8rem;
    padding: 0.2rem 0.6rem;
    background: var(--btn-secondary);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 3px;
    cursor: pointer;
  }
  .contrast-reset:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .theme-mode-switch {
    display: flex;
    gap: 0;
    border: 1px solid var(--border);
    border-radius: 3px;
    overflow: hidden;
  }

  .mode-btn {
    padding: 0.3rem 1rem;
    font-family: inherit;
    font-size: 0.8rem;
    font-weight: bold;
    border: none;
    cursor: pointer;
    background: var(--bg-input);
    color: var(--text-muted);
  }

  .mode-btn.active {
    background: var(--accent);
    color: var(--accent-text);
  }

  .mode-btn:hover:not(.active) {
    background: var(--menu-hover);
  }

  .secret-field {
    -webkit-text-security: disc;
  }
  .secret-field:focus {
    -webkit-text-security: none;
  }

  button {
    background: var(--accent);
    color: var(--accent-text);
    border: none;
    padding: 0.5rem 1.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: bold;
    border-radius: 3px;
    cursor: pointer;
  }

  button:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .hint {
    font-size: 0.7rem;
    color: var(--text-dim);
  }

  .global-hint {
    font-size: 0.65rem;
    color: var(--accent);
    opacity: 0.7;
    font-style: italic;
  }

  .toggle-row {
    flex-direction: row;
    align-items: center;
    gap: 0.75rem;
  }

  .theme-toggle {
    background: var(--btn-secondary);
    color: var(--text);
    padding: 0.3rem 1rem;
    font-size: 0.85rem;
  }

  .theme-toggle:hover {
    background: var(--btn-secondary-hover);
  }

  .qrz-status-row {
    flex-direction: row;
    align-items: center;
    gap: 0.75rem;
  }

  .qrz-ok {
    color: var(--accent);
    font-size: 0.85rem;
  }

  .qrz-error {
    color: var(--accent-error);
    font-size: 0.85rem;
  }

  .conn-status {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-left: auto;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    background: var(--text-dim);
  }
  .dot.green { background: #4caf50; }
  .dot.yellow { background: #ff9800; }
  .dot.red { background: #f44336; }
  .dot.off { background: var(--text-dim); opacity: 0.4; }

  p.hint {
    font-size: 0.7rem;
    color: var(--text-dim);
    margin: 0;
  }

  .setup-hint {
    color: var(--accent);
    font-size: 0.95rem;
    margin: 0 0 1rem;
    font-weight: 600;
  }

  .required {
    color: #ff4444;
    font-weight: bold;
  }

  :global(.input-required) {
    border-color: #ff4444 !important;
  }

  .danger-zone {
    border-color: #ff4444;
  }

  .danger-zone h3 {
    color: #ff4444;
  }

  .danger-text {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin: 0 0 0.75rem;
    line-height: 1.4;
  }

  .danger-error {
    color: #ff6666;
    font-size: 0.8rem;
    margin: 0 0 0.5rem;
  }

  .danger-separator {
    border-top: 1px solid #ff444444;
    margin: 0.75rem 0;
  }

  .danger-btn {
    background: #ff4444;
    color: #fff;
  }

  .danger-btn:hover:not(:disabled) {
    background: #cc3333;
  }

  .danger-btn:disabled {
    background: #ff4444;
    opacity: 0.4;
  }
  .warning-btn {
    background: #e67e22;
    color: #fff;
  }
  .warning-btn:hover {
    background: #cf6d17;
  }
  .update-status {
    margin-top: 0.5rem;
    font-size: 0.9rem;
    color: var(--text-muted);
  }
  .update-available {
    color: #2ecc40;
    font-weight: bold;
    text-decoration: none;
  }
  .update-available:hover {
    text-decoration: underline;
  }
  .update-actions {
    margin-top: 0.3rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .update-check-meta {
    margin-top: 0.7rem;
    font-size: 0.8rem;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .check-now-btn {
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    cursor: pointer;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-input, transparent);
    color: var(--text);
    align-self: flex-start;
  }
  .check-now-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .apply-update-btn {
    background: #2ecc40;
    color: var(--accent-text);
    font-weight: bold;
    border-color: #2ecc40;
    margin-left: 0.5rem;
  }
  .apply-update-btn:disabled {
    background: #2ecc40;
    opacity: 0.6;
  }
  .update-error {
    color: #e74c3c;
    font-size: 0.8rem;
    margin-left: 0.5rem;
  }
  .update-custom-repo-warning {
    margin-top: 0.5rem;
    padding: 0.4rem 0.6rem;
    font-size: 0.85rem;
    color: #f39c12;
    border: 1px solid #f39c12;
    border-radius: 4px;
    background: rgba(243, 156, 18, 0.1);
  }
  .update-custom-repo-warning a {
    color: #2ecc40;
  }
  .sha-link {
    font-family: monospace;
    color: var(--accent);
  }
</style>
