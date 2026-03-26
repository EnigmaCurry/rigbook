<script>
  import { onMount, onDestroy, tick, createEventDispatcher } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";
  import { QrzLookup, formatFreq, locationStr } from "./qrzLookup.js";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";

  const dispatch = createEventDispatcher();
  export let potaEnabled = true;

  let spots = [];
  let myGrid = "";
  let status = { rbn: { connected: false, enabled: false }, hamalert: { connected: false, enabled: false }, callsigns: 0, entries: 0, total_spots: 0, avg_spots_per_callsign: 0 };
  let bands = {};
  let modes = {};
  // Parse initial filter state from URL hash query params
  function parseFiltersFromHash() {
    const hash = window.location.hash.slice(1) || "";
    const qIdx = hash.indexOf("?");
    if (qIdx < 0) return {};
    const params = new URLSearchParams(hash.slice(qIdx + 1));
    return Object.fromEntries(params.entries());
  }

  function updateHash() {
    const params = new URLSearchParams();
    if (filterSource) params.set("source", filterSource);
    if (filterBand) params.set("band", filterBand);
    if (filterMode) params.set("mode", filterMode);
    if (filterCallsign) params.set("callsign", filterCallsign);
    if (filterSkcc) params.set("skcc", filterSkcc);
    const qs = params.toString();
    window.location.hash = qs ? `/spots?${qs}` : "/spots";
  }

  const initFilters = parseFiltersFromHash();
  const hasHashFilters = Object.keys(initFilters).length > 0;
  let filterSource = initFilters.source || "";
  let filterBand = initFilters.band || "";
  let filterMode = initFilters.mode || "";
  let filterCallsign = initFilters.callsign || "";
  let filterSkcc = initFilters.skcc || "";
  let savedFilters = null; // what's stored as the default
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
  let sortCol = "distance";
  let sortDir = 1; // 1 = ascending, -1 = descending

  function toggleSort(col) {
    if (sortCol === col) {
      sortDir = -sortDir;
    } else {
      sortCol = col;
      sortDir = 1;
    }
  }

  function sortIndicator(col) {
    if (sortCol !== col) return "";
    return sortDir === 1 ? " \u25B2" : " \u25BC";
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

  function onFilterChange() {
    updateHash();
    fetchSpots();
  }

  async function fetchSpots() {
    try {
      const params = new URLSearchParams();
      if (filterSource) params.set("source", filterSource);
      if (filterBand) params.set("band", filterBand);
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

  function currentFilters() {
    return {
      source: filterSource,
      band: filterBand,
      mode: filterMode,
      callsign: filterCallsign,
      skcc: filterSkcc,
    };
  }

  function filtersMatch(a, b) {
    if (!a || !b) return false;
    return a.source === b.source && a.band === b.band && a.mode === b.mode
      && a.callsign === b.callsign && a.skcc === b.skcc;
  }

  const factoryFilters = { source: "", band: "", mode: "", callsign: "", skcc: "" };
  $: isDefault = filtersLoaded && filtersMatch(
    { source: filterSource, band: filterBand, mode: filterMode, callsign: filterCallsign, skcc: filterSkcc },
    savedFilters || factoryFilters
  );

  async function loadDefaultFilters() {
    try {
      const res = await fetch("/api/settings/spot_filters");
      if (res.ok) {
        const data = await res.json();
        if (data.value) {
          savedFilters = JSON.parse(data.value);
          if (!hasHashFilters && savedFilters) {
            filterSource = savedFilters.source || "";
            filterBand = savedFilters.band || "";
            filterMode = savedFilters.mode || "";
            filterCallsign = savedFilters.callsign || "";
            filterSkcc = savedFilters.skcc || "";
            updateHash();
          }
        }
      }
    } catch {}
    filtersLoaded = true;
  }

  async function saveDefaultFilters() {
    savedFilters = currentFilters();
    try {
      await fetch("/api/settings/spot_filters", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: JSON.stringify(savedFilters) }),
      });
    } catch {}
  }

  async function clearDefaultFilters() {
    savedFilters = null;
    try {
      await fetch("/api/settings/spot_filters", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: "" }),
      });
    } catch {}
  }

  onMount(async () => {
    checkQrzConfigured();
    fetchStatus();
    fetchBands();
    fetchModes();
    fetchWorkedToday();
    fetchPotaSpots();
    await loadDefaultFilters();
    await fetchSpots();
    if (myGrid) { await initMap(); updateMap(); }
    statusInterval = setInterval(() => { fetchStatus(); fetchBands(); fetchModes(); fetchWorkedToday(); fetchPotaSpots(); }, 5000);
    spotsInterval = setInterval(fetchSpots, 3000);
    window.addEventListener("keydown", onFullscreenKey);
  });

  onDestroy(() => {
    clearInterval(statusInterval);
    clearInterval(spotsInterval);
    qrz.destroy();
    destroyMap();
    window.removeEventListener("keydown", onFullscreenKey);
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
  let selectedSpotter = null;
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

  const spotterIcon = L.divIcon({ className: "spot-marker", html: '<div class="spot-marker-dot spotter"></div>', iconSize: [10, 10], iconAnchor: [5, 5] });
  const homeLocIcon = L.divIcon({ className: "spot-marker", html: '<div class="spot-marker-dot home-loc"></div>', iconSize: [10, 10], iconAnchor: [5, 5] });
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

  function clearSelection() {
    for (const line of selectionLines) leafletMap.removeLayer(line);
    selectionLines = [];
    selectedSpotter = null;
  }

  function selectSpotter(call) {
    if (!leafletMap) return;
    clearSelection();
    if (!call) return;
    selectedSpotter = call;

    const myPos = gridToLatLon(myGrid);
    const spotterMarker = spotterMarkers[call];
    if (!myPos || !spotterMarker) return;
    const spotterLL = spotterMarker.getLatLng();
    const myLL = [myPos.lat, myPos.lon];

    // Find all spots using this spotter and draw triangles to their home locations
    for (const s of spots) {
      if (s.closest_call !== call || !s.qrz_grid) continue;
      const homePos = gridToLatLon(s.qrz_grid);
      if (!homePos) continue;
      const homeLL = [homePos.lat, homePos.lon];

      selectionLines.push(
        L.polyline([spotterLL, homeLL], { color: "#00ccff", weight: 2, opacity: 0.6 }).addTo(leafletMap),
        L.polyline([homeLL, myLL], { color: "#ffaa00", weight: 2, opacity: 0.6 }).addTo(leafletMap),
        L.polyline([myLL, spotterLL], { color: "#ff4444", weight: 2, opacity: 0.6 }).addTo(leafletMap),
      );
    }
  }

  async function initMap() {
    await tick();
    if (leafletMap || !mapEl) return;
    leafletMap = L.map(mapEl, { scrollWheelZoom: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
      maxZoom: 18,
    }).addTo(leafletMap);
    leafletMap.on("click", clearSelection);
    addExpandControl(leafletMap, mapEl.parentElement);
  }

  function updateMap() {
    if (!leafletMap || !myGrid) return;
    const myPos = gridToLatLon(myGrid);
    if (!myPos) return;

    // User's home marker
    if (!myMarker) {
      myMarker = L.marker([myPos.lat, myPos.lon], { icon: myIcon })
        .bindPopup(`My QTH: ${myGrid}`)
        .addTo(leafletMap);
    }

    // Collect current spotters and home locations
    const currentSpotters = new Map();
    const currentHomes = new Map();
    for (const s of spots) {
      if (s.closest_call && s.closest_grid) currentSpotters.set(s.closest_call, s.closest_grid);
      if (s.callsign && s.qrz_grid) currentHomes.set(s.callsign, s.qrz_grid);
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

    // Add new spotter markers
    for (const [call, grid] of currentSpotters) {
      if (spotterMarkers[call]) continue;
      const pos = gridToLatLon(grid);
      if (!pos) continue;
      const m = L.marker([pos.lat, pos.lon], { icon: spotterIcon })
        .bindPopup(`Spotter: ${call}<br>Grid: ${grid}`)
        .addTo(leafletMap);
      m.on("click", () => selectSpotter(call));
      spotterMarkers[call] = m;
    }

    // Add new home location markers
    for (const [call, grid] of currentHomes) {
      if (homeMarkers[call]) continue;
      const pos = gridToLatLon(grid);
      if (!pos) continue;
      homeMarkers[call] = L.marker([pos.lat, pos.lon], { icon: homeLocIcon })
        .bindPopup(`Station: ${call}<br>Grid: ${grid}`)
        .addTo(leafletMap);
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
  }

  function destroyMap() {
    if (leafletMap) { leafletMap.remove(); leafletMap = null; }
    spotterMarkers = {};
    homeMarkers = {};
    selectionLines = [];
    myMarker = null;
    selectedSpotter = null;
    mapInitialFitDone = false;
  }

  $: if (leafletMap && spots.length > 0 && myGrid) {
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
      case "country":     va = (a.country || "") + (a.qrz_state || ""); vb = (b.country || "") + (b.qrz_state || ""); break;
      case "source":      va = a.source || ""; vb = b.source || ""; break;
      case "distance":    va = a.distance_mi ?? 99999; vb = b.distance_mi ?? 99999; break;
      default:            va = a.callsign || ""; vb = b.callsign || "";
    }
    if (typeof va === "string") return sortDir * va.localeCompare(vb);
    return sortDir * (va - vb);
  });
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
    <select bind:value={filterSource} on:change={onFilterChange}>
      <option value="">All Sources</option>
      <option value="rbn">RBN</option>
      <option value="hamalert">HamAlert</option>
    </select>
    <select bind:value={filterBand} on:change={onFilterChange} style={filterBand ? `background: ${bandColor(filterBand)}; color: ${bandTextColor(filterBand)}` : ""}>
      <option value="">All Bands</option>
      {#each bandList as b}
        <option value={b} style="background: {bandColor(b)}; color: {bandTextColor(b)}">{b} ({bands[b]})</option>
      {/each}
    </select>
    <select bind:value={filterMode} on:change={() => { if (filterMode !== "CW") filterSkcc = ""; onFilterChange(); }}>
      <option value="">All Modes</option>
      {#each modeList as m}
        <option value={m}>{m} ({modes[m]})</option>
      {/each}
    </select>
    <input type="text" placeholder="Callsign" bind:value={filterCallsign} on:input={onFilterChange} style="text-transform: uppercase" />
    {#if filterMode === "CW"}
      <select bind:value={filterSkcc} on:change={onFilterChange}>
        <option value="">SKCC: Any</option>
        <option value="required">SKCC: Required</option>
      </select>
    {/if}
    {#if filtersLoaded}
      {#if !isDefault}
        <button class="default-btn save" on:click={saveDefaultFilters} title="Save current filters as default">Save as default</button>
      {:else if savedFilters}
        <button class="default-btn clear" on:click={clearDefaultFilters} title="Clear saved default filters">Clear default</button>
      {/if}
    {/if}
  </div>

  {#if bandList.length > 0}
    <div class="band-badges">
      {#each bandList as b}
        <span
          class="band-badge"
          class:active={filterBand === b}
          style="background: {bandColor(b)}; color: {bandTextColor(b)}; opacity: {filterBand && filterBand !== b ? 0.3 : 1}"
          on:click={() => { filterBand = filterBand === b ? "" : b; onFilterChange(); }}
          on:keydown={(e) => { if (e.key === 'Enter') { filterBand = filterBand === b ? "" : b; onFilterChange(); } }}
          role="button"
          tabindex="0"
        >
          {b}: {bands[b]}
        </span>
      {/each}
    </div>
  {/if}

  {#if myGrid}
    <div class="spots-map-wrap">
      <div class="spots-map" bind:this={mapEl}></div>
    </div>
  {/if}

  <div class="spots-table-wrap">
    <table class="spots-table">
      <thead>
        <tr>
          <th class="sortable" on:click={() => toggleSort("time")}>Time{sortIndicator("time")}</th>
          <th class="sortable" on:click={() => toggleSort("callsign")}>Callsign{sortIndicator("callsign")}</th>
          {#if filterMode === "CW"}<th class="sortable" on:click={() => toggleSort("skcc")}>SKCC{sortIndicator("skcc")}</th>{/if}
          <th class="sortable" on:click={() => toggleSort("frequency")}>Freq (MHz){sortIndicator("frequency")}</th>
          <th class="sortable" on:click={() => toggleSort("band")}>Band{sortIndicator("band")}</th>
          <th class="sortable" on:click={() => toggleSort("mode")}>Mode{sortIndicator("mode")}</th>
          <th class="sortable" on:click={() => toggleSort("spotters")}>Spotters{sortIndicator("spotters")}</th>
          <th class="sortable" on:click={() => toggleSort("snr")}>Best SNR{sortIndicator("snr")}</th>
          <th class="sortable" on:click={() => toggleSort("wpm")}>WPM{sortIndicator("wpm")}</th>
          <th class="sortable" on:click={() => toggleSort("country")}>Home Location{sortIndicator("country")}</th>
          <th class="sortable" on:click={() => toggleSort("source")}>Source{sortIndicator("source")}</th>
          <th class="sortable" on:click={() => toggleSort("distance")}>Closest Spot{sortIndicator("distance")}</th>
          <th>Info</th>
        </tr>
      </thead>
      <tbody>
        {#each sortedSpots as spot (spot.callsign + spot.frequency + spot.mode)}
          <tr class:worked={isWorkedToday(spot)}>
            <td class="mono">{formatTime(spot)}</td>
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            {#if isWorkedToday(spot)}
              <td class="mono call worked-call" title="Already worked today">{spot.callsign}{#if isPotaActivator(spot)} 🌲{/if}</td>
            {:else}
              <td class="mono call clickable" on:click={() => addQsoWithPota(spot)} title="Log QSO with {spot.callsign}">{spot.callsign}{#if isPotaActivator(spot)} 🌲{/if}</td>
            {/if}
            {#if filterMode === "CW"}<td class="mono skcc">{spot.skcc ?? ""}</td>{/if}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <td class="mono freq clickable" on:click={() => dispatch("tune", spot)} title="Tune radio">{formatFreq(spot.frequency)}</td>
            <td><span class="band-tag" style="background: {bandColor(spot.band)}; color: {bandTextColor(spot.band)}">{spot.band}</span></td>
            <td>{spot.mode}</td>
            <td class="mono" title={spot.spotters ? spot.spotters.join(", ") : ""}>{spot.spotter_count}</td>
            <td class="mono">{spot.best_snr ?? ""}</td>
            <td class="mono">{spot.wpm ?? ""}</td>
            <td class="location">{#if spot.country || spot.qrz_state}{locationStr(spot)}{:else if !qrzConfigured}<span class="fetch-hint">(Configure QRZ account)</span>{:else if qrz.skipped}<span class="fetch-hint">(filter more to fetch)</span>{:else if qrz.pending > 0}<span class="fetch-hint">(fetching... {qrz.pending} left)</span>{/if}</td>
            <td class="source-tag {spot.source}">{spot.source}</td>
            <td class="mono">{spot.closest_call || ""}{spot.distance_mi != null ? ` ${spot.distance_mi}mi` : ""}{spot.closest_snr != null ? ` ${spot.closest_snr}dB` : ""}</td>
            <td class="info">{spot.state}{spot.wwff_ref ? ` ${spot.wwff_ref}` : ""}{spot.comment ? ` ${spot.comment}` : ""}</td>
          </tr>
        {/each}
        {#if spots.length === 0}
          <tr><td colspan={filterMode === "CW" ? 13 : 12} class="empty">No spots{filterSource || filterBand || filterMode || filterCallsign ? " matching filters" : ""}. {status.rbn.enabled || status.hamalert.enabled ? "Waiting for data..." : "Enable RBN or HamAlert in Settings."}</td></tr>
        {/if}
      </tbody>
    </table>
  </div>
</div>

<style>
  .spots-page {
    max-width: 1200px;
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
  .default-btn.save { background: var(--accent); color: var(--bg); }
  .default-btn.save:hover { opacity: 0.85; }
  .default-btn.clear { opacity: 0.7; font-size: 0.75rem; }

  .band-badges {
    display: flex;
    gap: 0.4rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
  }

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
    overflow-x: auto;
  }

  .spots-table {
    width: 100%;
    border-collapse: collapse;
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
  }

  .spots-table th.sortable {
    cursor: pointer;
    user-select: none;
  }
  .spots-table th.sortable:hover {
    color: var(--accent);
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
    margin-bottom: 0.75rem;
  }

  .spots-map {
    width: 100%;
    height: 350px;
    border: 1px solid var(--border);
    border-radius: 3px;
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

  :global(.spot-marker-dot.home-loc) {
    width: 8px;
    height: 8px;
    background: #ffaa00;
    border: 2px solid #885500;
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
</style>
