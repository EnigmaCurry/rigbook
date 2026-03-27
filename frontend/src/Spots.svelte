<script>
  import { onMount, onDestroy, tick, createEventDispatcher } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";
  import { QrzLookup, formatFreq, locationStr } from "./qrzLookup.js";
  import { getMapTileConfig } from "./mapTiles.js";
  import { storageGet, storageSet } from "./storage.js";
  import ParkDetail from "./ParkDetail.svelte";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";

  const dispatch = createEventDispatcher();
  export let potaEnabled = true;

  let modalParkRef = null;
  let modalParkDetail = null;
  let modalParkLoading = false;

  async function openParkModal(ref) {
    modalParkRef = ref;
    modalParkDetail = null;
    modalParkLoading = true;
    try {
      const res = await fetch(`/api/pota/park/${encodeURIComponent(ref)}`);
      if (res.ok) {
        const data = await res.json();
        if (!data.error) modalParkDetail = data;
      }
    } catch {}
    modalParkLoading = false;
  }

  function closeParkModal() {
    modalParkRef = null;
    modalParkDetail = null;
    modalParkLoading = false;
  }

  let spots = [];
  let myGrid = "";
  let showMap = storageGet("spotsMapEnabled") !== "false";
  const MIN_MAP_HEIGHT = 60;
  const MAX_MAP_FRAC = 0.7;
  let mapHeight = Math.min(parseInt(storageGet("spotsMapHeight")) || 350, Math.floor(document.documentElement.clientHeight * MAX_MAP_FRAC));
  let status = { rbn: { connected: false, enabled: false }, hamalert: { connected: false, enabled: false }, callsigns: 0, entries: 0, total_spots: 0, avg_spots_per_callsign: 0 };
  let bands = {};
  let modes = {};
  let filterSource = "";
  let filterBands = new Set();
  let filterMode = "";
  let filterCallsign = "";
  let filterSkcc = "";
  let filtersLoaded = false;
  let restarting = false;
  let workedTodayKeys = new Set();
  let potaKeys = new Set();
  let potaByKey = {};

  const BAND_RANGES = {
    "160m": [1800, 2000], "80m": [3500, 4000], "60m": [5330, 5410],
    "40m": [7000, 7300], "30m": [10100, 10150], "20m": [14000, 14350],
    "17m": [18068, 18168], "15m": [21000, 21450], "12m": [24890, 24990],
    "10m": [28000, 29700], "6m": [50000, 54000], "2m": [144000, 148000],
  };

  const MODE_NORMALIZE = {
    "USB": "SSB", "LSB": "SSB", "CW-R": "CW", "CWR": "CW", "RTTY-R": "RTTY",
  };

  function freqToBand(freqKhz) {
    const f = parseFloat(freqKhz);
    if (isNaN(f)) return "";
    for (const [band, [lo, hi]] of Object.entries(BAND_RANGES)) {
      if (f >= lo && f <= hi) return band;
    }
    return "";
  }

  function normalizeMode(m) {
    const u = (m || "").toUpperCase();
    return MODE_NORMALIZE[u] || u;
  }

  async function fetchWorkedToday() {
    try {
      const res = await fetch("/api/contacts/today");
      if (res.ok) {
        const contacts = await res.json();
        const keys = new Set();
        for (const c of contacts) {
          const band = freqToBand(parseFloat(c.freq));
          const key = `${(c.call || "").toUpperCase()}|${band}|${normalizeMode(c.mode)}`;
          keys.add(key);
        }
        workedTodayKeys = keys;
      }
    } catch {}
  }

  async function fetchPotaSpots() {
    if (!potaEnabled) { potaKeys = new Set(); potaByKey = {}; return; }
    try {
      const res = await fetch("/api/pota/spots");
      if (res.ok) {
        const pota = await res.json();
        const keys = new Set();
        const byKey = {};
        for (const s of pota) {
          const call = (s.activator || "").toUpperCase();
          const band = freqToBand(parseFloat(s.frequency));
          if (call && band) {
            const key = `${call}|${band}`;
            keys.add(key);
            byKey[key] = s;
          }
        }
        potaKeys = keys;
        potaByKey = byKey;
      }
    } catch {}
  }

  function isPotaActivator(spot) {
    if (potaKeys.size === 0) return false;
    const call = (spot.callsign || "").toUpperCase();
    const band = spot.band || freqToBand(parseFloat(spot.frequency));
    return potaKeys.has(`${call}|${band}`);
  }

  function getPotaSpot(spot) {
    const call = (spot.callsign || "").toUpperCase();
    const band = spot.band || freqToBand(parseFloat(spot.frequency));
    return potaByKey[`${call}|${band}`] || null;
  }

  function addQsoWithPota(spot) {
    const pota = getPotaSpot(spot);
    if (pota) {
      dispatch("addqso", {
        activator: String(spot.callsign || ""),
        frequency: String(spot.frequency || ""),
        mode: String(spot.mode || ""),
        reference: String(pota.reference || ""),
        grid4: String(pota.grid4 || ""),
        locationDesc: String(pota.locationDesc || ""),
        skcc: String(spot.skcc || ""),
      });
    } else {
      dispatch("addqso", spot);
    }
  }

  function spotHomeGrid(spot) {
    const pota = getPotaSpot(spot);
    if (pota) return pota.grid6 || pota.grid4 || "";
    return spot.qrz_grid || "";
  }

  function spotHomeLabel(spot) {
    const pota = getPotaSpot(spot);
    if (pota) return pota.reference || "";
    return locationStr(spot);
  }

  function isWorkedToday(spot) {
    if (workedTodayKeys.size === 0) return false;
    const band = spot.band || freqToBand(parseFloat(spot.frequency));
    const mode = normalizeMode(spot.mode);
    if (!mode || mode === "?") {
      const prefix = `${(spot.callsign || "").toUpperCase()}|${band}|`;
      for (const k of workedTodayKeys) {
        if (k.startsWith(prefix)) return true;
      }
      return false;
    }
    const key = `${(spot.callsign || "").toUpperCase()}|${band}|${mode}`;
    return workedTodayKeys.has(key);
  }
  let qrzConfigured = true;
  const qrz = new QrzLookup(() => { spots = spots; });
  let sortCol = storageGet("spotsSortCol") || "distance";
  let sortDir = storageGet("spotsSortDir") === "-1" ? -1 : 1;

  const defaultSpotColumns = ["time", "callsign", "skcc", "frequency", "band", "mode", "spotters", "snr", "wpm", "location", "source", "distance", "info"];
  const spotColumnDefs = {
    time:      { key: "time",      label: "Time" },
    callsign:  { key: "callsign",  label: "Callsign" },
    skcc:      { key: "skcc",      label: "SKCC" },
    frequency: { key: "frequency", label: "Freq (MHz)" },
    band:      { key: "band",      label: "Band" },
    mode:      { key: "mode",      label: "Mode" },
    spotters:  { key: "spotters",  label: "Spotters" },
    snr:       { key: "snr",       label: "Best SNR" },
    wpm:       { key: "wpm",       label: "WPM" },
    location:  { key: "location",   label: "Location" },
    source:    { key: "source",    label: "Source" },
    distance:  { key: "distance",  label: "Closest Spot" },
    info:      { key: "info",      label: "Info" },
  };

  function loadSpotColumnOrder() {
    try {
      const saved = JSON.parse(storageGet("spotsColumnOrder"));
      if (Array.isArray(saved) && saved.every(k => spotColumnDefs[k])) {
        const missing = defaultSpotColumns.filter(k => !saved.includes(k));
        const merged = [...saved.filter(k => spotColumnDefs[k]), ...missing];
        if (merged.length === defaultSpotColumns.length) return merged;
      }
    } catch {}
    return [...defaultSpotColumns];
  }

  let spotColumnOrder = loadSpotColumnOrder();
  $: spotColumns = spotColumnOrder.filter(k => k !== "skcc" || filterMode === "CW").map(k => spotColumnDefs[k]);

  let spotDragCol = null;
  let spotDragOverCol = null;

  function onSpotColDragStart(e, key) {
    spotDragCol = key;
    e.dataTransfer.effectAllowed = "move";
  }
  function onSpotColDragOver(e, key) {
    e.preventDefault();
    spotDragOverCol = key;
  }
  function onSpotColDrop(e, key) {
    e.preventDefault();
    if (spotDragCol && spotDragCol !== key) {
      const from = spotColumnOrder.indexOf(spotDragCol);
      const to = spotColumnOrder.indexOf(key);
      const newOrder = [...spotColumnOrder];
      newOrder.splice(from, 1);
      newOrder.splice(to, 0, spotDragCol);
      spotColumnOrder = newOrder;
      storageSet("spotsColumnOrder", JSON.stringify(spotColumnOrder));
    }
    spotDragCol = null;
    spotDragOverCol = null;
  }
  function onSpotColDragEnd() {
    spotDragCol = null;
    spotDragOverCol = null;
  }

  // Column resize
  let spotResizeCol = null;
  let spotResizeColKey = null;
  let spotResizeStartX = 0;
  let spotResizeStartW = 0;

  function loadSpotColumnWidths() {
    try {
      return JSON.parse(storageGet("spotsColumnWidths")) || {};
    } catch { return {}; }
  }

  let spotColumnWidths = loadSpotColumnWidths();

  function startSpotColResize(e, key) {
    e.preventDefault();
    e.stopPropagation();
    const th = e.target.parentElement;
    spotResizeCol = th;
    spotResizeColKey = key;
    spotResizeStartX = e.clientX;
    spotResizeStartW = th.offsetWidth;
    window.addEventListener("mousemove", onSpotColResize);
    window.addEventListener("mouseup", stopSpotColResize);
  }

  function onSpotColResize(e) {
    if (!spotResizeCol) return;
    const diff = e.clientX - spotResizeStartX;
    const newW = Math.max(30, spotResizeStartW + diff);
    spotResizeCol.style.width = newW + "px";
  }

  function stopSpotColResize() {
    if (spotResizeCol && spotResizeColKey) {
      spotColumnWidths[spotResizeColKey] = spotResizeCol.style.width;
      storageSet("spotsColumnWidths", JSON.stringify(spotColumnWidths));
    }
    spotResizeCol = null;
    spotResizeColKey = null;
    window.removeEventListener("mousemove", onSpotColResize);
    window.removeEventListener("mouseup", stopSpotColResize);
  }

  function toggleSort(col) {
    if (sortCol === col) {
      sortDir = -sortDir;
    } else {
      sortCol = col;
      sortDir = 1;
    }
    storageSet("spotsSortCol", sortCol);
    storageSet("spotsSortDir", String(sortDir));
  }

  let statusInterval;
  let spotsInterval;

  async function fetchStatus() {
    try {
      const res = await fetch("/api/spots/status");
      if (res.ok) status = await res.json();
    } catch {}
  }

  async function fetchBands() {
    try {
      const res = await fetch("/api/spots/bands");
      if (res.ok) bands = await res.json();
    } catch {}
  }

  async function fetchModes() {
    try {
      const res = await fetch("/api/spots/modes");
      if (res.ok) modes = await res.json();
    } catch {}
  }

  function toggleMap() {
    showMap = !showMap;
    storageSet("spotsMapEnabled", String(showMap));
    if (showMap && myGrid && !leafletMap) {
      tick().then(() => { initMap(); updateMap(); });
    }
    if (!showMap) { destroyMap(); }
  }

  function onDragStart(e) {
    e.preventDefault();
    const startY = e.type === "touchstart" ? e.touches[0].clientY : e.clientY;
    const startH = mapHeight;
    function onMove(ev) {
      const clientY = ev.type === "touchmove" ? ev.touches[0].clientY : ev.clientY;
      const newH = startH + (clientY - startY);
      if (newH < MIN_MAP_HEIGHT) {
        showMap = false;
        storageSet("spotsMapEnabled", "false");
        destroyMap();
        cleanup();
        return;
      }
      mapHeight = Math.min(newH, Math.floor(document.documentElement.clientHeight * MAX_MAP_FRAC));
      if (leafletMap) leafletMap.invalidateSize();
    }
    function cleanup() {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", cleanup);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", cleanup);
      storageSet("spotsMapHeight", String(mapHeight));
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", cleanup);
    window.addEventListener("touchmove", onMove);
    window.addEventListener("touchend", cleanup);
  }

  function onFilterChange() {
    fetchSpots();
  }

  async function fetchSpots() {
    try {
      const params = new URLSearchParams();
      if (filterSource) params.set("source", filterSource);
      if (filterBandsStr) params.set("band", filterBandsStr);
      if (filterMode) params.set("mode", filterMode);
      if (filterCallsign) params.set("callsign", filterCallsign);
      if (filterSkcc) params.set("skcc", filterSkcc);
      params.set("limit", "200");
      const res = await fetch(`/api/spots/?${params}`);
      if (res.ok) {
        const data = await res.json();
        spots = data.spots;
        myGrid = data.my_grid || "";
        await qrz.enqueue(spots);
      }
    } catch {}
  }

  async function restart() {
    restarting = true;
    try {
      await fetch("/api/spots/restart", { method: "POST" });
    } catch {}
    restarting = false;
    setTimeout(fetchStatus, 2000);
  }

  function formatTime(spot) {
    if (spot.time) return spot.time;
    if (spot.received_at) {
      const d = new Date(spot.received_at * 1000);
      return d.getUTCHours().toString().padStart(2, "0") +
             d.getUTCMinutes().toString().padStart(2, "0") + "Z";
    }
    return "";
  }

  async function checkQrzConfigured() {
    try {
      const res = await fetch("/api/settings/qrz_password");
      if (res.ok) {
        const data = await res.json();
        qrzConfigured = !!data.value && data.value !== "";
      } else {
        qrzConfigured = false;
      }
    } catch {
      qrzConfigured = false;
    }
  }

  $: filterBandsStr = [...filterBands].sort().join(",");

  function toggleBand(b) {
    if (filterBands.has(b)) filterBands.delete(b);
    else filterBands.add(b);
    filterBands = new Set(filterBands);
  }

  const FILTER_SETTINGS_KEY = "spot_filters";

  async function loadFilters() {
    try {
      const res = await fetch(`/api/settings/${FILTER_SETTINGS_KEY}`);
      if (res.ok) {
        const data = await res.json();
        if (data.value) {
          const saved = JSON.parse(data.value);
          filterSource = saved.source || "";
          filterBands = saved.band ? new Set(saved.band.split(",")) : new Set();
          filterMode = saved.mode || "";
          filterCallsign = saved.callsign || "";
          filterSkcc = saved.skcc || "";
        }
      }
    } catch {}
    filtersLoaded = true;
  }

  async function saveFilters() {
    if (!filtersLoaded) return;
    try {
      await fetch(`/api/settings/${FILTER_SETTINGS_KEY}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: JSON.stringify({
          source: filterSource,
          band: [...filterBands].sort().join(","),
          mode: filterMode,
          callsign: filterCallsign,
          skcc: filterSkcc,
        }) }),
      });
    } catch {}
  }

  // Auto-save filters whenever they change (after initial load)
  $: if (filtersLoaded) {
    const _filters = { s: filterSource, b: filterBandsStr, m: filterMode, c: filterCallsign, k: filterSkcc };
    saveFilters();
  }

  onMount(async () => {
    checkQrzConfigured();
    fetchStatus();
    fetchBands();
    fetchModes();
    fetchWorkedToday();
    fetchPotaSpots();
    await loadFilters();
    await fetchSpots();
    if (myGrid && showMap) { await initMap(); updateMap(); }
    statusInterval = setInterval(() => { fetchStatus(); fetchBands(); fetchModes(); fetchWorkedToday(); fetchPotaSpots(); }, 5000);
    spotsInterval = setInterval(fetchSpots, 3000);
    window.addEventListener("keydown", onFullscreenKey);
    window.addEventListener("keydown", onSpotsKeydown);
    window.addEventListener("resize", onWindowResize);
    if (window.visualViewport) window.visualViewport.addEventListener("resize", onWindowResize);
  });

  function onWindowResize() {
    const maxH = Math.floor(document.documentElement.clientHeight * MAX_MAP_FRAC);
    if (mapHeight > maxH) {
      mapHeight = maxH;
      storageSet("spotsMapHeight", String(mapHeight));
    }
    if (leafletMap) leafletMap.invalidateSize();
  }

  onDestroy(() => {
    clearInterval(statusInterval);
    clearInterval(spotsInterval);
    qrz.destroy();
    destroyMap();
    window.removeEventListener("keydown", onFullscreenKey);
    window.removeEventListener("keydown", onSpotsKeydown);
    window.removeEventListener("resize", onWindowResize);
    if (window.visualViewport) window.visualViewport.removeEventListener("resize", onWindowResize);
  });

  $: bandList = Object.keys(bands).sort((a, b) => {
    const numA = parseInt(a);
    const numB = parseInt(b);
    return numB - numA;
  });

  $: modeList = Object.keys(modes).sort((a, b) => (modes[b] || 0) - (modes[a] || 0));

  // --- Map ---
  let mapEl;
  let leafletMap = null;
  let spotterMarkers = {};   // closest_call -> marker
  let homeMarkers = {};      // callsign -> marker
  let spotterLines = {};     // closest_call -> polyline (to my QTH)
  let myMarker = null;
  let selectionLines = [];   // active triangle lines
  let hoveredSpot = null;    // spot hovered in table (temporary triangle)
  let lockedSpot = null;     // spot clicked in table (persistent triangle)
  let selectedSpotter = null; // spotter clicked on map (highlights table rows)
  let tableWrapEl;
  let mapInitialFitDone = false;
  let fullscreenMap = null;
  let fullscreenWrap = null;

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

  /** Shift lon to be within ±180 of baseLon so lines take the short path. */
  function nearLon(baseLon, lon) {
    let d = lon - baseLon;
    if (d > 180) lon -= 360;
    else if (d < -180) lon += 360;
    return lon;
  }

  /** Normalize a [lat, lon] point relative to a base longitude. */
  function nearLL(baseLon, pt) {
    return [pt[0], nearLon(baseLon, pt[1])];
  }

  const spotterIcon = L.divIcon({ className: "spot-marker", html: '<div class="spot-marker-dot spotter"></div>', iconSize: [10, 10], iconAnchor: [5, 5] });
  const spotterSecondaryIcon = L.divIcon({ className: "spot-marker", html: '<div class="spot-marker-dot spotter-secondary"></div>', iconSize: [10, 10], iconAnchor: [5, 5] });
  function homeLocIcon(spotterCount) {
    const t = Math.min(spotterCount / 10, 1);
    // Lerp from dim gold (#886600) to bright yellow (#ffee00)
    const r = Math.round(0x88 + t * (0xff - 0x88));
    const g = Math.round(0x66 + t * (0xee - 0x66));
    const b = Math.round(0x00 + t * (0x00 - 0x00));
    const bg = `rgb(${r},${g},${b})`;
    const br = Math.round(0x55 + t * (0x99 - 0x55));
    const bg2 = Math.round(0x33 + t * (0x77 - 0x33));
    const border = `rgb(${br},${bg2},0)`;
    const size = spotterCount > 10 ? 15 : Math.round(10 + (spotterCount / 10) * 5);
    const half = Math.round(size / 2);
    return L.divIcon({
      className: "spot-marker",
      html: `<div class="spot-marker-dot" style="width:${size-2}px;height:${size-2}px;background:${bg};border:2px solid ${border};border-radius:50%"></div>`,
      iconSize: [size, size],
      iconAnchor: [half, half],
    });
  }
  const myIcon = L.divIcon({ className: "spot-marker", html: '<div class="spot-marker-dot my-pos"></div>', iconSize: [14, 14], iconAnchor: [7, 7] });

  function addExpandControl(map, wrapEl) {
    const ExpandControl = L.Control.extend({
      options: { position: "topright" },
      onAdd() {
        const btn = L.DomUtil.create("div", "leaflet-bar leaflet-control map-expand-btn");
        btn.innerHTML = "⛶";
        btn.title = "Toggle fullscreen";
        btn.onclick = (e) => { e.stopPropagation(); toggleFullscreen(map, wrapEl); };
        return btn;
      }
    });
    map.addControl(new ExpandControl());
  }

  function toggleFullscreen(map, wrapEl) {
    if (fullscreenMap) {
      exitFullscreen();
    } else {
      fullscreenMap = map;
      fullscreenWrap = wrapEl;
      wrapEl.classList.add("map-fullscreen");
      document.body.style.overflow = "hidden";
      setTimeout(() => map.invalidateSize(), 100);
    }
  }

  function exitFullscreen() {
    if (!fullscreenMap) return;
    const map = fullscreenMap;
    fullscreenWrap.classList.remove("map-fullscreen");
    document.body.style.overflow = "";
    fullscreenMap = null;
    fullscreenWrap = null;
    setTimeout(() => map.invalidateSize(), 100);
  }

  function onFullscreenKey(e) {
    if (e.key === "Escape" && fullscreenMap) exitFullscreen();
  }

  function lockedIndex() {
    if (!lockedSpot) return -1;
    const k = spotKey(lockedSpot);
    return sortedSpots.findIndex(s => spotKey(s) === k);
  }

  function onSpotsKeydown(e) {
    const tag = e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const cur = lockedIndex();
      const next = cur < sortedSpots.length - 1 ? cur + 1 : cur;
      selectSpotByIndex(next);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const cur = lockedIndex();
      const next = cur > 0 ? cur - 1 : 0;
      selectSpotByIndex(next);
    } else if (e.key === "Escape" && lockedSpot) {
      clearAll();
    } else if (e.key === "Enter" && lockedSpot) {
      if (!isWorkedToday(lockedSpot)) addQsoWithPota(lockedSpot);
    }
  }

  function selectSpotByIndex(idx) {
    const spot = sortedSpots[idx];
    if (!spot) return;
    // Use onSpotClick but prevent it from toggling off if same spot
    if (lockedSpot && spotKey(lockedSpot) === spotKey(spot)) return;
    onSpotClick(spot);
    tick().then(() => {
      if (!tableWrapEl) return;
      const row = tableWrapEl.querySelector(`tbody tr:nth-child(${idx + 1})`);
      if (row) row.scrollIntoView({ block: "center" });
    });
  }

  function clearLines() {
    for (const line of selectionLines) leafletMap.removeLayer(line);
    selectionLines = [];
  }

  function clearAll() {
    if (leafletMap) leafletMap.closePopup();
    clearLines();
    hoveredSpot = null;
    lockedSpot = null;
    selectedSpotter = null;
    showAllMarkers();
  }

  function setMarkerVisible(marker, visible) {
    const el = marker.getElement?.();
    if (el) el.style.display = visible ? "" : "none";
  }

  function filterMarkersForSpot(spot) {
    if (!leafletMap) return;
    const coWitnesses = new Set(Object.keys(spot.spotter_grids || {}));
    for (const [call, marker] of Object.entries(spotterMarkers)) {
      const visible = coWitnesses.has(call);
      setMarkerVisible(marker, visible);
      if (visible) {
        marker.setIcon(call === spot.closest_call ? spotterIcon : spotterSecondaryIcon);
      }
    }
    for (const [call, marker] of Object.entries(homeMarkers)) {
      setMarkerVisible(marker, call === spot.callsign);
    }
  }

  function globalClosestCalls() {
    const closest = new Set();
    for (const s of spots) {
      if (s.closest_call) closest.add(s.closest_call);
    }
    return closest;
  }

  function showAllMarkers() {
    const closest = globalClosestCalls();
    for (const [call, m] of Object.entries(spotterMarkers)) {
      setMarkerVisible(m, true);
      m.setIcon(closest.has(call) ? spotterIcon : spotterSecondaryIcon);
    }
    for (const m of Object.values(homeMarkers)) setMarkerVisible(m, true);
  }

  function spotKey(s) {
    return `${s.callsign}|${s.frequency}|${s.mode}`;
  }

  function drawTriangleForSpot(spot) {
    if (!leafletMap || !spot) return;
    clearLines();
    const myPos = gridToLatLon(myGrid);
    if (!myPos) return;
    const myLL = [myPos.lat, myPos.lon];
    const baseLon = myLL[1];

    const spotterGrid = spot.closest_grid;
    const homeGrid = spotHomeGrid(spot);
    const spotterPos = spotterGrid ? gridToLatLon(spotterGrid) : null;
    const homePos = homeGrid ? gridToLatLon(homeGrid) : null;

    // Normalize all points relative to my QTH longitude
    const homeLL = homePos ? nearLL(baseLon, [homePos.lat, homePos.lon]) : null;
    const spotterLL = spotterPos ? nearLL(baseLon, [spotterPos.lat, spotterPos.lon]) : null;

    // Draw dashed cyan lines from secondary spotters first (lower z-order)
    if (homeLL && spot.spotter_grids) {
      for (const [call, grid] of Object.entries(spot.spotter_grids)) {
        if (call === spot.closest_call) continue;
        const pos = gridToLatLon(grid);
        if (!pos) continue;
        selectionLines.push(
          L.polyline([nearLL(baseLon, [pos.lat, pos.lon]), homeLL], { color: "#00ccff", weight: 2, opacity: 0.6, dashArray: "6 4" }).addTo(leafletMap),
        );
      }
    }

    // Primary triangle lines drawn last (higher z-order)
    if (spotterLL && homeLL) {
      selectionLines.push(
        L.polyline([spotterLL, homeLL], { color: "#00ccff", weight: 2, opacity: 0.6 }).addTo(leafletMap),
        L.polyline([homeLL, myLL], { color: "#ffaa00", weight: 2, opacity: 0.6 }).addTo(leafletMap),
        L.polyline([myLL, spotterLL], { color: "#ff4444", weight: 2, opacity: 0.6 }).addTo(leafletMap),
      );
    } else if (spotterLL) {
      selectionLines.push(
        L.polyline([myLL, spotterLL], { color: "#ff4444", weight: 2, opacity: 0.6 }).addTo(leafletMap),
      );
    } else if (homeLL) {
      selectionLines.push(
        L.polyline([myLL, homeLL], { color: "#ffaa00", weight: 2, opacity: 0.6 }).addTo(leafletMap),
      );
    }
  }

  function drawTrianglesForSpotter(call) {
    if (!leafletMap || !call) return;
    clearLines();
    const myPos = gridToLatLon(myGrid);
    if (!myPos) return;
    const myLL = [myPos.lat, myPos.lon];
    const baseLon = myLL[1];
    const spotterMarker = spotterMarkers[call];
    if (!spotterMarker) return;
    const rawLL = spotterMarker.getLatLng();
    const sLL = nearLL(baseLon, [rawLL.lat, rawLL.lng]);

    for (const s of spots) {
      const hg = spotHomeGrid(s);
      if (s.closest_call !== call || !hg) continue;
      const homePos = gridToLatLon(hg);
      if (!homePos) continue;
      const homeLL = nearLL(baseLon, [homePos.lat, homePos.lon]);
      selectionLines.push(
        L.polyline([sLL, homeLL], { color: "#00ccff", weight: 2, opacity: 0.6 }).addTo(leafletMap),
        L.polyline([homeLL, myLL], { color: "#ffaa00", weight: 2, opacity: 0.6 }).addTo(leafletMap),
        L.polyline([myLL, sLL], { color: "#ff4444", weight: 2, opacity: 0.6 }).addTo(leafletMap),
      );
    }
  }

  function onSpotHover(spot) {
    if (lockedSpot || selectedSpotter) return;
    hoveredSpot = spot;
    drawTriangleForSpot(spot);
  }

  function onSpotLeave() {
    if (lockedSpot || selectedSpotter) return;
    hoveredSpot = null;
    clearLines();
  }

  function onSpotClick(spot) {
    if (leafletMap) leafletMap.closePopup();
    if (lockedSpot && spotKey(lockedSpot) === spotKey(spot)) {
      lockedSpot = null;
      selectedSpotter = null;
      clearLines();
      showAllMarkers();
      return;
    }
    lockedSpot = spot;
    selectedSpotter = null;
    drawTriangleForSpot(spot);
    filterMarkersForSpot(spot);
    fitMapToSpot(spot);
    const hm = homeMarkers[spot.call];
    if (hm) hm.openPopup();
  }

  function fitMapToSpot(spot) {
    if (!leafletMap || !myGrid) return;
    const myPos = gridToLatLon(myGrid);
    if (!myPos) return;

    const points = [[myPos.lat, myPos.lon]];

    const spotterGrid = spot.closest_grid;
    const homeGrid = spotHomeGrid(spot);
    const spotterPos = spotterGrid ? gridToLatLon(spotterGrid) : null;
    const homePos = homeGrid ? gridToLatLon(homeGrid) : null;

    const baseLon = myPos.lon;
    if (spotterPos) points.push(nearLL(baseLon, [spotterPos.lat, spotterPos.lon]));
    if (homePos) points.push(nearLL(baseLon, [homePos.lat, homePos.lon]));

    if (points.length > 1) {
      leafletMap.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 12 });
    } else {
      leafletMap.setView(points[0], 8);
    }
  }

  function scrollToSpot(spot) {
    if (!tableWrapEl) return;
    const idx = sortedSpots.findIndex(s => spotKey(s) === spotKey(spot));
    if (idx < 0) return;
    tick().then(() => {
      const row = tableWrapEl.querySelector(`tbody tr:nth-child(${idx + 1})`);
      if (row) row.scrollIntoView({ block: "center" });
    });
  }

  function onMapHomeClick(call) {
    const spot = spots.find(s => s.callsign === call);
    if (!spot) return;
    if (lockedSpot && spotKey(lockedSpot) === spotKey(spot)) {
      clearAll();
      return;
    }
    lockedSpot = spot;
    selectedSpotter = null;
    drawTriangleForSpot(spot);
    filterMarkersForSpot(spot);
    scrollToSpot(spot);
  }

  function onMapSpotterClick(call) {
    if (selectedSpotter === call) {
      clearAll();
      return;
    }
    lockedSpot = null;
    hoveredSpot = null;
    selectedSpotter = call;
    drawTrianglesForSpotter(call);
    // Scroll to first spot for this spotter
    const spot = sortedSpots.find(s => s.closest_call === call);
    if (spot) scrollToSpot(spot);
  }

  async function initMap() {
    await tick();
    if (leafletMap || !mapEl) return;
    leafletMap = L.map(mapEl, { scrollWheelZoom: true, worldCopyJump: true });
    const tiles = await getMapTileConfig();
    L.tileLayer(tiles.url, {
      attribution: tiles.attribution,
      maxZoom: tiles.maxZoom,
    }).addTo(leafletMap);
    leafletMap.on("click", clearAll);
    addExpandControl(leafletMap, mapEl.parentElement);
    mapResizeObserver = new ResizeObserver(() => { leafletMap?.invalidateSize(); });
    mapResizeObserver.observe(mapEl);
  }

  function updateMap() {
    if (!leafletMap || !myGrid) return;
    const myPos = gridToLatLon(myGrid);
    if (!myPos) return;
    const baseLon = myPos.lon;

    // User's home marker
    if (!myMarker) {
      myMarker = L.marker([myPos.lat, myPos.lon], { icon: myIcon })
        .bindPopup(`My QTH: ${myGrid}`)
        .addTo(leafletMap);
    }

    // Collect current spotters and home locations
    const currentSpotters = new Map();
    const closestCalls = new Set();
    const currentHomes = new Map();
    const homeSpotterCounts = new Map();
    for (const s of spots) {
      if (s.closest_call && s.closest_grid) {
        currentSpotters.set(s.closest_call, s.closest_grid);
        closestCalls.add(s.closest_call);
      }
      // Add all spotters with known grids
      if (s.spotter_grids) {
        for (const [call, grid] of Object.entries(s.spotter_grids)) {
          currentSpotters.set(call, grid);
        }
      }
      const hg = spotHomeGrid(s);
      if (s.callsign && hg) {
        currentHomes.set(s.callsign, hg);
        homeSpotterCounts.set(s.callsign, s.spotter_count || 1);
      }
    }

    // Remove stale spotter markers
    for (const call of Object.keys(spotterMarkers)) {
      if (!currentSpotters.has(call)) {
        leafletMap.removeLayer(spotterMarkers[call]);
        delete spotterMarkers[call];
      }
    }
    // Remove stale home markers
    for (const call of Object.keys(homeMarkers)) {
      if (!currentHomes.has(call)) {
        leafletMap.removeLayer(homeMarkers[call]);
        delete homeMarkers[call];
      }
    }

    // Add/update spotter markers (normalized to QTH longitude)
    for (const [call, grid] of currentSpotters) {
      const icon = closestCalls.has(call) ? spotterIcon : spotterSecondaryIcon;
      const pos = gridToLatLon(grid);
      if (!pos) continue;
      const ll = nearLL(baseLon, [pos.lat, pos.lon]);
      if (spotterMarkers[call]) {
        spotterMarkers[call].setIcon(icon);
        spotterMarkers[call].setLatLng(ll);
        spotterMarkers[call].setPopupContent(`Spotter: ${call}<br>Grid: ${grid}`);
        continue;
      }
      const m = L.marker(ll, { icon })
        .bindPopup(`Spotter: ${call}<br>Grid: ${grid}`)
        .addTo(leafletMap);
      m.on("click", () => onMapSpotterClick(call));
      spotterMarkers[call] = m;
    }

    // Add/update home location markers (normalized to QTH longitude)
    for (const [call, grid] of currentHomes) {
      const count = homeSpotterCounts.get(call) || 1;
      const icon = homeLocIcon(count);
      const pos = gridToLatLon(grid);
      if (!pos) continue;
      const ll = nearLL(baseLon, [pos.lat, pos.lon]);
      if (homeMarkers[call]) {
        homeMarkers[call].setIcon(icon);
        homeMarkers[call].setLatLng(ll);
        homeMarkers[call].setPopupContent(`Station: ${call}<br>Grid: ${grid}`);
        continue;
      }
      const hm = L.marker(ll, { icon })
        .bindPopup(`Station: ${call}<br>Grid: ${grid}`)
        .addTo(leafletMap);
      hm.on("click", () => onMapHomeClick(call));
      homeMarkers[call] = hm;
    }

    // Fit bounds on first load only
    if (!mapInitialFitDone) {
      const allLatLngs = [[myPos.lat, myPos.lon]];
      for (const m of Object.values(spotterMarkers)) { const ll = m.getLatLng(); allLatLngs.push([ll.lat, ll.lng]); }
      for (const m of Object.values(homeMarkers)) { const ll = m.getLatLng(); allLatLngs.push([ll.lat, ll.lng]); }
      if (allLatLngs.length > 1) {
        leafletMap.fitBounds(allLatLngs, { padding: [30, 30], maxZoom: 8 });
        mapInitialFitDone = true;
      }
    }

    // Re-apply marker filtering if a spot is locked
    if (lockedSpot) filterMarkersForSpot(lockedSpot);
  }

  function destroyMap() {
    if (mapResizeObserver) { mapResizeObserver.disconnect(); mapResizeObserver = null; }
    if (leafletMap) { leafletMap.remove(); leafletMap = null; }
    spotterMarkers = {};
    homeMarkers = {};
    selectionLines = [];
    myMarker = null;
    selectedSpotter = null;
    mapInitialFitDone = false;
  }

  $: if (leafletMap && myGrid) {
    spots;  // track spots reassignment
    updateMap();
  }

  $: sortedSpots = [...spots].sort((a, b) => {
    let va, vb;
    switch (sortCol) {
      case "time":        va = a.received_at || 0; vb = b.received_at || 0; break;
      case "callsign":    va = a.callsign || ""; vb = b.callsign || ""; break;
      case "skcc":        va = a.skcc || ""; vb = b.skcc || ""; break;
      case "frequency":   va = a.frequency || 0; vb = b.frequency || 0; break;
      case "band":        va = parseInt(a.band) || 0; vb = parseInt(b.band) || 0; break;
      case "mode":        va = a.mode || ""; vb = b.mode || ""; break;
      case "spotters":    va = a.spotter_count || 0; vb = b.spotter_count || 0; break;
      case "snr":         va = a.best_snr ?? -999; vb = b.best_snr ?? -999; break;
      case "wpm":         va = a.wpm ?? 0; vb = b.wpm ?? 0; break;
      case "location":     va = (a.country || "") + (a.qrz_state || ""); vb = (b.country || "") + (b.qrz_state || ""); break;
      case "source":      va = a.source || ""; vb = b.source || ""; break;
      case "distance":    va = a.distance_mi ?? 99999; vb = b.distance_mi ?? 99999; break;
      default:            va = a.callsign || ""; vb = b.callsign || "";
    }
    if (typeof va === "string") return sortDir * va.localeCompare(vb);
    return sortDir * (va - vb);
  });

  // Keep locked/selected spot in view as data refreshes
  $: if (sortedSpots && lockedSpot) {
    scrollToSpot(lockedSpot);
  }
</script>

<div class="spots-page">
  <h2>Spots</h2>

  <div class="status-bar">
    <div class="status-item">
      <span class="dot" class:green={status.rbn.connected} class:red={status.rbn.enabled && !status.rbn.connected} class:off={!status.rbn.enabled}></span>
      RBN {#if !status.rbn.enabled}(disabled){:else if status.rbn.connected}(connected){:else}(connecting...){/if}
    </div>
    <div class="status-item">
      <span class="dot" class:green={status.hamalert.connected} class:red={status.hamalert.enabled && !status.hamalert.connected} class:off={!status.hamalert.enabled}></span>
      HamAlert {#if !status.hamalert.enabled}(disabled){:else if status.hamalert.connected}(connected){:else}(connecting...){/if}
    </div>
    <div class="status-item cache-stats">
      {status.callsigns} callsign{status.callsigns !== 1 ? "s" : ""} &middot;
      {status.total_spots} spot{status.total_spots !== 1 ? "s" : ""} &middot;
      {status.avg_spots_per_callsign} avg/call
    </div>
  </div>

  <div class="filters">
    {#if bandList.length > 0}
      {#each bandList as b}
        <span
          class="band-badge"
          class:active={filterBands.has(b)}
          style="background: {bandColor(b)}; color: {bandTextColor(b)}; opacity: {filterBands.size > 0 && !filterBands.has(b) ? 0.3 : 1}"
          on:click={() => { toggleBand(b); onFilterChange(); }}
          on:keydown={(e) => { if (e.key === 'Enter') { toggleBand(b); onFilterChange(); } }}
          role="button"
          tabindex="0"
        >
          {b}
        </span>
      {/each}
    {/if}
    {#if filterBands.size > 0}
      <button class="default-btn clear-bands" on:click={() => { filterBands = new Set(); onFilterChange(); }}>Clear bands</button>
    {/if}
    <select bind:value={filterSource} on:change={onFilterChange}>
      <option value="">All Sources</option>
      <option value="rbn">RBN</option>
      <option value="hamalert">HamAlert</option>
    </select>
    <select bind:value={filterMode} on:change={() => { if (filterMode !== "CW") filterSkcc = ""; onFilterChange(); }}>
      <option value="">All Modes</option>
      {#each modeList as m}
        <option value={m}>{m} ({modes[m]})</option>
      {/each}
    </select>
    <input type="text" placeholder="Callsign" bind:value={filterCallsign} on:input={onFilterChange} style="text-transform: uppercase; width: 10ch" />
    {#if filterMode === "CW"}
      <select bind:value={filterSkcc} on:change={onFilterChange}>
        <option value="">SKCC: Any</option>
        <option value="required">SKCC: Required</option>
      </select>
    {/if}
    {#if myGrid}
      <button class="default-btn map-toggle" class:active={showMap} on:click={toggleMap} title="{showMap ? 'Hide' : 'Show'} map">Map</button>
    {/if}
  </div>

  {#if myGrid && showMap}
    <div class="spots-map-wrap">
      <div class="spots-map" bind:this={mapEl} style="height: {mapHeight}px"></div>
    </div>
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="map-drag-handle" on:mousedown={onDragStart} on:touchstart={onDragStart}>
      <div class="drag-grip"></div>
    </div>
  {/if}

  <div class="spots-table-wrap" bind:this={tableWrapEl}>
    <table class="spots-table">
      <thead>
        <tr>
          {#each spotColumns as col (col.key)}
            <th class="sortable" class:drag-over={spotDragOverCol === col.key && spotDragCol !== col.key} class:sorting={sortCol === col.key} on:dragover={e => onSpotColDragOver(e, col.key)} on:drop={e => onSpotColDrop(e, col.key)} style={spotColumnWidths[col.key] ? `width: ${spotColumnWidths[col.key]}` : ""}>
              <span class="col-label" draggable="true" on:dragstart={e => onSpotColDragStart(e, col.key)} on:dragend={onSpotColDragEnd} on:click={() => { if (col.key !== "info") toggleSort(col.key); }}>{col.label}{#if sortCol === col.key}{sortDir === 1 ? " ▲" : " ▼"}{/if}</span><span class="resize-handle" on:mousedown={e => startSpotColResize(e, col.key)}></span>
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each sortedSpots as spot, i (spot.callsign + spot.frequency + spot.mode)}
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <tr class:worked={isWorkedToday(spot)}
              class:spot-highlighted={selectedSpotter && spot.closest_call === selectedSpotter}
              class:spot-locked={lockedSpot && spotKey(lockedSpot) === spotKey(spot)}
              on:mouseenter={() => onSpotHover(spot)}
              on:mouseleave={onSpotLeave}
              on:click|stopPropagation={() => onSpotClick(spot)}>
            {#each spotColumns as col (col.key)}
              {#if col.key === "time"}<td class="mono">{formatTime(spot)}</td>
              {:else if col.key === "callsign"}
                {#if isWorkedToday(spot)}
                  <td class="mono call worked-call" title="Already worked today">{spot.callsign}{#if isPotaActivator(spot)} 🌲{/if}</td>
                {:else}
                  <td class="mono call"><!-- svelte-ignore a11y-click-events-have-key-events --><!-- svelte-ignore a11y-no-static-element-interactions --><span class="clickable" on:click|stopPropagation={() => addQsoWithPota(spot)} title="Log QSO with {spot.callsign}">{spot.callsign}{#if isPotaActivator(spot)} 🌲{/if}</span></td>
                {/if}
              {:else if col.key === "skcc"}<td class="mono skcc">{spot.skcc ?? ""}</td>
              {:else if col.key === "frequency"}<td class="mono freq"><!-- svelte-ignore a11y-click-events-have-key-events --><!-- svelte-ignore a11y-no-static-element-interactions --><span class="clickable" on:click|stopPropagation={() => dispatch("tune", spot)} title="Tune radio">{formatFreq(spot.frequency)}</span></td>
              {:else if col.key === "band"}<td><span class="band-tag" style="background: {bandColor(spot.band)}; color: {bandTextColor(spot.band)}">{spot.band}</span></td>
              {:else if col.key === "mode"}<td>{spot.mode}</td>
              {:else if col.key === "spotters"}<td class="mono" title={spot.spotters ? spot.spotters.join(", ") : ""}>{spot.spotter_count}</td>
              {:else if col.key === "snr"}<td class="mono">{spot.best_snr ?? ""}</td>
              {:else if col.key === "wpm"}<td class="mono">{spot.wpm ?? ""}</td>
              {:else if col.key === "location"}<td class="location">{#if isPotaActivator(spot)}{@const pota = getPotaSpot(spot)}<!-- svelte-ignore a11y-click-events-have-key-events --><!-- svelte-ignore a11y-no-static-element-interactions --><span class="pota-loc clickable" on:click|stopPropagation={() => openParkModal(spotHomeLabel(spot))}>{spotHomeLabel(spot)}</span>{#if pota?.name}<span class="pota-name">{pota.name}</span>{/if}{:else if spot.country || spot.qrz_state}{locationStr(spot)}{:else if !qrzConfigured}<span class="fetch-hint">(Configure QRZ account)</span>{:else if qrz.skipped}<span class="fetch-hint">(filter more to fetch)</span>{:else if qrz.pending > 0}<span class="fetch-hint">(fetching... {qrz.pending} left)</span>{/if}</td>
              {:else if col.key === "source"}<td class="source-tag {spot.source}">{spot.source}</td>
              {:else if col.key === "distance"}<td class="mono">{spot.closest_call || ""}{spot.distance_mi != null ? ` ${spot.distance_mi}mi` : ""}{spot.closest_snr != null ? ` ${spot.closest_snr}dB` : ""}</td>
              {:else if col.key === "info"}<td class="info">{spot.state}{spot.wwff_ref ? ` ${spot.wwff_ref}` : ""}{spot.comment ? ` ${spot.comment}` : ""}</td>
              {/if}
            {/each}
          </tr>
        {/each}
        {#if spots.length === 0}
          <tr><td colspan={spotColumns.length} class="empty">No spots{filterSource || filterBands.size > 0 || filterMode || filterCallsign ? " matching filters" : ""}. {status.rbn.enabled || status.hamalert.enabled ? "Waiting for data..." : "Enable RBN or HamAlert in Settings."}</td></tr>
        {/if}
      </tbody>
    </table>
  </div>
</div>

{#if modalParkRef}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="modal-backdrop" on:click={closeParkModal}>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="modal-content" on:click|stopPropagation on:keydown={e => { if (e.key === "Escape") closeParkModal(); }}>
      <button class="modal-close" on:click={closeParkModal}>X</button>
      {#if modalParkLoading}
        <p class="status">Loading park details...</p>
      {:else if modalParkDetail}
        <ParkDetail park={modalParkDetail} on:close={closeParkModal} />
      {:else}
        {@const prefix = modalParkRef.match(/^([A-Z]{1,2})-/)?.[1] || ""}
        <p class="status">Park {modalParkRef} not found in cache.</p>
        <p class="cache-link">Go to <a href="#/parks/download">Cache</a> to download park data{prefix ? ` for country code ${prefix}` : ""}.</p>
      {/if}
    </div>
  </div>
{/if}

<svelte:window on:keydown={e => { if (modalParkRef && e.key === "Escape") closeParkModal(); }} />

<style>
  .spots-page {
    max-width: none;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  h2 {
    color: var(--accent);
    font-size: 1.2rem;
    margin: 0 0 1rem 0;
  }

  .status-bar {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    padding: 0.5rem 0.75rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    margin-bottom: 0.75rem;
    font-size: 0.85rem;
    flex-wrap: wrap;
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    background: var(--text-dim);
  }
  .dot.green { background: #4caf50; }
  .dot.red { background: #f44336; }
  .dot.off { background: var(--text-dim); opacity: 0.4; }

  .restart-btn {
    margin-left: auto;
    background: var(--btn-secondary);
    color: var(--text);
    border: none;
    padding: 0.25rem 0.75rem;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 3px;
    cursor: pointer;
  }
  .restart-btn:hover:not(:disabled) { background: var(--btn-secondary-hover); }
  .restart-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  .filters {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
  }

  .filters select,
  .filters input {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 0.3rem 0.5rem;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
  }
  .filters select:focus,
  .filters input:focus {
    outline: none;
    border-color: var(--accent);
  }

  .default-btn {
    background: var(--btn-secondary);
    color: var(--text);
    border: none;
    padding: 0.3rem 0.6rem;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 3px;
    cursor: pointer;
    white-space: nowrap;
  }
  .default-btn:hover { background: var(--btn-secondary-hover); }
  .default-btn.map-toggle.active { background: var(--accent); color: var(--bg); }

  .band-badge {
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    font-size: 0.75rem;
    cursor: pointer;
    user-select: none;
    transition: opacity 0.15s;
  }
  .band-badge.active {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }

  .spots-table-wrap {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  .spots-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.8rem;
  }

  .spots-table th {
    text-align: left;
    padding: 0.3rem 0.5rem;
    border-bottom: 2px solid var(--border);
    color: var(--text-muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    white-space: nowrap;
    position: sticky;
    top: 0;
    background: var(--bg);
    z-index: 1;
  }

  .spots-table th.sortable {
    cursor: pointer;
    user-select: none;
  }
  .spots-table th.sortable:hover {
    color: var(--accent);
  }
  .spots-table th.sorting {
    color: var(--accent);
  }
  .spots-table th.drag-over {
    border-left: 2px solid var(--accent);
  }

  .spots-table .col-label {
    cursor: pointer;
  }

  .spots-table .resize-handle {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 5px;
    cursor: col-resize;
    background: transparent;
  }

  .spots-table .resize-handle:hover,
  .spots-table .resize-handle:active {
    background: var(--accent);
    opacity: 0.4;
  }

  .spots-table td {
    padding: 0.25rem 0.5rem;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }

  .mono {
    font-variant-numeric: tabular-nums;
  }

  .call {
    font-weight: bold;
    color: var(--accent-callsign, #ffcc00);
  }
  .worked-call {
    color: var(--fg, #ccc);
    font-weight: normal;
  }
  tr.worked {
    opacity: 0.5;
  }
  tr.spot-highlighted {
    background: rgba(0, 204, 255, 0.15);
  }
  tr.spot-locked {
    background: rgba(0, 204, 255, 0.25);
    outline: 1px solid rgba(0, 204, 255, 0.4);
  }

  .freq {
    color: var(--accent);
  }

  .clickable {
    cursor: pointer;
  }

  .clickable:hover {
    text-decoration: underline;
  }

  .band-tag {
    padding: 0.1rem 0.4rem;
    border-radius: 2px;
    font-size: 0.75rem;
  }

  .source-tag {
    font-size: 0.7rem;
    text-transform: uppercase;
    padding: 0.1rem 0.3rem;
    border-radius: 2px;
  }
  .source-tag.rbn {
    background: #2196f3;
    color: #fff;
  }
  .source-tag.hamalert {
    background: #ff9800;
    color: #fff;
  }

  .location {
    color: var(--text-muted);
    font-size: 0.75rem;
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .pota-loc {
    color: var(--accent, #00ff88);
    font-weight: bold;
    font-size: 0.8rem;
  }

  .pota-name {
    color: var(--text-dim);
    font-size: 0.7rem;
    margin-left: 0.3rem;
  }

  .fetch-hint {
    color: var(--text-dim);
    font-size: 0.65rem;
    font-style: italic;
  }

  .info {
    color: var(--text-muted);
    font-size: 0.75rem;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .empty {
    text-align: center;
    color: var(--text-dim);
    padding: 2rem 0.5rem !important;
  }

  .spots-map-wrap {
    margin-bottom: 0;
  }

  .spots-map {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 3px;
  }

  .map-drag-handle {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 10px;
    cursor: row-resize;
    user-select: none;
    touch-action: none;
    margin-bottom: 0.5rem;
  }

  .drag-grip {
    width: 40px;
    height: 4px;
    border-radius: 2px;
    background: var(--border);
  }

  .map-drag-handle:hover .drag-grip {
    background: var(--accent);
  }

  :global(.spot-marker-dot) {
    border-radius: 50%;
    transition: all 0.15s;
  }

  :global(.spot-marker-dot.spotter) {
    width: 8px;
    height: 8px;
    background: #00ccff;
    border: 2px solid #006688;
  }

  :global(.spot-marker-dot.spotter-secondary) {
    width: 8px;
    height: 8px;
    background: #005577;
    border: 2px solid #003344;
  }


  :global(.spot-marker-dot.my-pos) {
    width: 12px;
    height: 12px;
    background: #ff4444;
    border: 2px solid #880000;
    box-shadow: 0 0 8px rgba(255, 68, 68, 0.6);
  }

  :global(.map-fullscreen) {
    position: fixed !important;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
    margin: 0 !important;
    border-radius: 0 !important;
    border: none !important;
    padding: 0 !important;
  }

  :global(.map-fullscreen .spots-map) {
    height: 100% !important;
  }

  :global(.spots-map .leaflet-popup-content-wrapper),
  :global(.spots-map .leaflet-popup-tip) {
    opacity: 0.7;
  }

  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .modal-content {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    max-width: 900px;
    width: 95%;
    max-height: 80vh;
    overflow-y: auto;
    position: relative;
  }

  .modal-close {
    position: absolute;
    top: 0.5rem;
    right: 0.75rem;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 1rem;
    font-family: inherit;
    font-weight: bold;
    cursor: pointer;
  }

  .modal-close:hover {
    color: var(--text);
  }

  .cache-link {
    font-size: 0.9rem;
  }

  .cache-link a {
    color: var(--accent);
    text-decoration: none;
  }

  .cache-link a:hover {
    text-decoration: underline;
  }
</style>
