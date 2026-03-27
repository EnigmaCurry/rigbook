<script>
  import { onMount, onDestroy, tick, createEventDispatcher } from "svelte";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";
  import { getMapTileConfig } from "./mapTiles.js";
  import { storageGet, storageSet } from "./storage.js";
  import { parkAward, parkAwardTitle } from "./parkAward.js";
  import { countryFlag, prefixFromRef } from "./countryFlag.js";
  import ParkDetail from "./ParkDetail.svelte";

  const dispatch = createEventDispatcher();
  export let activePark = "";

  // --- Tab routing ---
  const TABS = ["my-qsos", "by-country", "download"];
  let tab = parseTab();
  let parkRef = parseParkRef();
  let parkDetail = null;
  let parkLoading = false;

  // --- My QSOs state ---
  let myParks = [];
  let myParksLoading = false;
  let mySort = "date"; // "date", "name", "qsos"
  let mySortAsc = false;

  $: myParksSorted = [...myParks].sort((a, b) => {
    let cmp = 0;
    if (mySort === "date") {
      cmp = (a.last_contact || "").localeCompare(b.last_contact || "");
    } else if (mySort === "name") {
      cmp = (a.name || a.reference).localeCompare(b.name || b.reference);
    } else if (mySort === "code") {
      cmp = (a.reference || "").localeCompare(b.reference || "");
    } else if (mySort === "qsos") {
      cmp = (a.qso_count || 0) - (b.qso_count || 0);
    }
    return mySortAsc ? cmp : -cmp;
  });

  function toggleMySort(col) {
    if (mySort === col) mySortAsc = !mySortAsc;
    else { mySort = col; mySortAsc = col === "name" || col === "code"; }
  }
  let showMap = storageGet("parksMapEnabled") !== "false";
  const MIN_MAP_HEIGHT = 60;
  const MAX_MAP_FRAC = 0.7;
  let mapHeight = Math.min(parseInt(storageGet("parksMapHeight")) || 350, Math.floor(window.innerHeight * MAX_MAP_FRAC));
  let mapEl;
  let leafletMap = null;
  let markersByRef = {};
  let selectedPark = null;
  let activeMarker = null; // temporary marker for activePark from QSO form
  let lastActivePark = activePark;
  let fullscreenMap = null; // reference to the map currently fullscreen
  let fullscreenWrap = null; // reference to the wrap element
  let myParksListEl;

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

  function selectedParkIndex() {
    if (!selectedPark) return -1;
    return myParksSorted.findIndex(p => p.reference === selectedPark);
  }

  function onParksKeydown(e) {
    if (tab !== "my-qsos" || myParksSorted.length === 0) return;
    const tag = e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const cur = selectedParkIndex();
      const next = cur < myParksSorted.length - 1 ? cur + 1 : cur;
      navigateToParkIndex(next);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const cur = selectedParkIndex();
      const next = cur > 0 ? cur - 1 : 0;
      navigateToParkIndex(next);
    } else if (e.key === "Escape" && selectedPark) {
      deselectPark();
    } else if (e.key === "Enter" && selectedPark) {
      viewPark(selectedPark);
    }
  }

  function navigateToParkIndex(idx) {
    const park = myParksSorted[idx];
    if (!park) return;
    if (selectedPark === park.reference) return;
    selectPark(park.reference);
    tick().then(() => {
      if (!myParksListEl) return;
      const row = myParksListEl.querySelector(`.park-row:nth-child(${idx + 1})`);
      if (row) row.scrollIntoView({ block: "center" });
    });
  }

  function parseTab() {
    const hash = window.location.hash.slice(1) || "";
    const parts = hash.split("/").filter(Boolean);
    if (parts.length >= 3 && parts[1] === "park") return "park";
    if (parts.length >= 2 && TABS.includes(parts[1])) return parts[1];
    return "my-qsos";
  }

  function parseParkRef() {
    const hash = window.location.hash.slice(1) || "";
    const parts = hash.split("/").filter(Boolean);
    if (parts.length >= 3 && parts[1] === "park") return decodeURIComponent(parts[2]);
    return "";
  }

  function switchTab(t) {
    tab = t;
    parkDetail = null;
    exitFullscreen();
    destroyMap();
    if (t === "my-qsos") loadMyParks();
    window.location.hash = `/parks/${t}`;
  }

  function viewPark(ref) {
    parkRef = ref;
    tab = "park";
    window.location.hash = `/parks/park/${encodeURIComponent(ref)}`;
    loadParkDetail(ref);
  }

  async function loadParkDetail(ref) {
    parkLoading = true;
    parkDetail = null;
    try {
      const res = await fetch(`/api/pota/park/${encodeURIComponent(ref)}`);
      if (res.ok) {
        const data = await res.json();
        if (!data.error) parkDetail = data;
      }
    } catch {}
    parkLoading = false;
  }

  function onHashChange() {
    const prevTab = tab;
    tab = parseTab();
    const newRef = parseParkRef();
    if (tab === "park" && newRef && newRef !== parkRef) {
      parkRef = newRef;
      loadParkDetail(newRef);
    }
    if (tab === "my-qsos" && prevTab !== "my-qsos") {
      renderMap();
    }
  }

  // --- Programs / Cache state ---
  let programs = [];
  let loading = false;
  let saving = false;
  let fetching = false;
  let fetchProgress = null;
  let fetchResult = null;
  let cacheFilter = "";
  let dirty = false;

  $: cachedPrograms = programs.filter(p => p.park_count > 0);
  $: cacheFiltered = cacheFilter
    ? programs.filter(p =>
        p.prefix.toLowerCase().includes(cacheFilter.toLowerCase()) ||
        p.name.toLowerCase().includes(cacheFilter.toLowerCase())
      )
    : programs;

  $: selectedCount = programs.filter(p => p.selected).length;
  $: cachedCountries = cachedPrograms.length;
  $: totalLocations = programs.reduce((s, p) => s + (p.location_count || 0), 0);
  $: totalParks = programs.reduce((s, p) => s + (p.park_count || 0), 0);
  $: myTotalQsos = myParks.reduce((s, p) => s + (p.qso_count || 0), 0);
  $: myAvgQsos = myParks.length ? (myTotalQsos / myParks.length).toFixed(1) : "0";

  async function loadPrograms() {
    loading = true;
    try {
      const res = await fetch("/api/pota/programs");
      if (res.ok) programs = await res.json();
    } catch {}
    loading = false;
  }

  function toggle(prefix) {
    programs = programs.map(p =>
      p.prefix === prefix ? { ...p, selected: !p.selected } : p
    );
    dirty = true;
  }

  async function saveSelections() {
    saving = true;
    const prefixes = programs.filter(p => p.selected).map(p => p.prefix);
    try {
      await fetch("/api/pota/selected-programs", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prefixes }),
      });
      dirty = false;
    } catch {}
    saving = false;
  }

  async function fetchParks() {
    if (dirty) await saveSelections();
    fetching = true;
    fetchProgress = null;
    fetchResult = null;
    let fetchedParks = 0;
    let fetchedLocations = 0;
    let errors = 0;
    try {
      const res = await fetch("/api/pota/fetch-parks", { method: "POST" });
      const contentType = res.headers.get("content-type") || "";

      if (contentType.includes("text/event-stream")) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split("\n\n");
          buf = lines.pop();
          for (const line of lines) {
            const m = line.match(/^data: (.+)$/);
            if (!m) continue;
            const msg = JSON.parse(m[1]);
            if (msg.type === "progress") {
              fetchProgress = msg;
              fetchedParks += msg.parks || 0;
              fetchedLocations++;
            } else if (msg.type === "error") {
              fetchProgress = msg;
              errors++;
            } else if (msg.type === "start") {
              fetchProgress = { done: 0, total: msg.total, location: "" };
            }
          }
        }
        fetchResult = { locations: fetchedLocations, parks: fetchedParks, errors };
      } else {
        const data = await res.json();
        if (data.status === "up_to_date") {
          fetchResult = { upToDate: true, locations: data.locations };
        }
      }
    } catch {}
    fetching = false;
    fetchProgress = null;
    await loadPrograms();
  }

  // --- List tab state ---
  let expandedCountries = {};
  let expandedLocations = {};
  let locationsByPrefix = {};
  let parksByDescriptor = {};
  let loadingLocations = {};
  let loadingParks = {};
  let listFilter = "";

  $: listFiltered = listFilter
    ? cachedPrograms.filter(p =>
        p.prefix.toLowerCase().includes(listFilter.toLowerCase()) ||
        p.name.toLowerCase().includes(listFilter.toLowerCase())
      )
    : cachedPrograms;

  async function toggleCountry(prefix) {
    if (expandedCountries[prefix]) {
      expandedCountries[prefix] = false;
      expandedCountries = expandedCountries;
      return;
    }
    expandedCountries[prefix] = true;
    expandedCountries = expandedCountries;

    if (!locationsByPrefix[prefix]) {
      loadingLocations[prefix] = true;
      loadingLocations = loadingLocations;
      try {
        const res = await fetch(`/api/pota/programs/${prefix}/locations`);
        if (res.ok) locationsByPrefix[prefix] = await res.json();
      } catch {}
      loadingLocations[prefix] = false;
      loadingLocations = loadingLocations;
    }
  }

  async function toggleLocation(descriptor) {
    if (expandedLocations[descriptor]) {
      expandedLocations[descriptor] = false;
      expandedLocations = expandedLocations;
      return;
    }
    expandedLocations[descriptor] = true;
    expandedLocations = expandedLocations;

    if (!parksByDescriptor[descriptor]) {
      loadingParks[descriptor] = true;
      loadingParks = loadingParks;
      try {
        const res = await fetch(`/api/pota/locations/${descriptor}/parks`);
        if (res.ok) parksByDescriptor[descriptor] = await res.json();
      } catch {}
      loadingParks[descriptor] = false;
      loadingParks = loadingParks;
    }
  }

  function destroyMap() {
    if (mapResizeObserver) { mapResizeObserver.disconnect(); mapResizeObserver = null; }
    if (leafletMap) { leafletMap.remove(); leafletMap = null; }
    markersByRef = {};
    selectedPark = null;
    activeMarker = null;
  }

  function toggleMap() {
    showMap = !showMap;
    storageSet("parksMapEnabled", String(showMap));
    if (showMap && myParks.length > 0 && !leafletMap) {
      tick().then(() => renderMap());
    }
    if (!showMap) destroyMap();
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
        storageSet("parksMapEnabled", "false");
        destroyMap();
        cleanup();
        return;
      }
      mapHeight = Math.min(newH, Math.floor(window.innerHeight * MAX_MAP_FRAC));
      if (leafletMap) leafletMap.invalidateSize();
    }
    function cleanup() {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", cleanup);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", cleanup);
      storageSet("parksMapHeight", String(mapHeight));
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", cleanup);
    window.addEventListener("touchmove", onMove);
    window.addEventListener("touchend", cleanup);
  }

  const highlightIcon = L.divIcon({
    className: "park-marker",
    html: '<div class="park-marker-dot highlight"></div>',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });

  const normalIcon = L.divIcon({
    className: "park-marker",
    html: '<div class="park-marker-dot"></div>',
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

  const activeIcon = L.divIcon({
    className: "park-marker",
    html: '<div class="park-marker-dot active"></div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });

  async function showActivePark(ref) {
    if (!ref || !leafletMap) {
      if (activeMarker) { leafletMap?.removeLayer(activeMarker); activeMarker = null; }
      return;
    }
    // If it's already a known park marker, just highlight it
    if (markersByRef[ref]) {
      if (activeMarker) { leafletMap.removeLayer(activeMarker); activeMarker = null; }
      selectPark(ref);
      return;
    }
    // Fetch park data and add temporary marker
    try {
      const res = await fetch(`/api/pota/park/${encodeURIComponent(ref)}`);
      if (!res.ok) return;
      const park = await res.json();
      if (park.latitude == null || park.longitude == null) return;
      if (activeMarker) leafletMap.removeLayer(activeMarker);
      const ll = [park.latitude, park.longitude];
      activeMarker = L.marker(ll, { icon: activeIcon })
        .bindPopup(`<b>${park.reference}</b><br>${park.name || ""}<br><i>Not yet logged</i>`)
        .addTo(leafletMap);
      activeMarker.openPopup();
      leafletMap.panTo(ll);
    } catch {}
  }

  $: if (activePark !== lastActivePark) {
    lastActivePark = activePark;
    if (tab === "my-qsos" && !renderingMap) showActivePark(activePark);
  }

  function highlightPark(ref) {
    if (selectedPark) return;
    const m = markersByRef[ref];
    if (m) { m.setIcon(highlightIcon); m.openPopup(); }
  }

  function unhighlightPark(ref) {
    if (selectedPark) return;
    const m = markersByRef[ref];
    if (m) { m.setIcon(normalIcon); m.closePopup(); }
  }

  function deselectPark() {
    if (selectedPark) {
      const m = markersByRef[selectedPark];
      if (m) { m.setIcon(normalIcon); m.closePopup(); }
      selectedPark = null;
    }
  }

  function selectPark(ref) {
    // Deselect if clicking the same park
    if (selectedPark === ref) {
      deselectPark();
      return;
    }
    // Unhighlight previous selection
    if (selectedPark) {
      const prev = markersByRef[selectedPark];
      if (prev) { prev.setIcon(normalIcon); prev.closePopup(); }
    }
    selectedPark = ref;
    const m = markersByRef[ref];
    if (m) {
      m.setIcon(highlightIcon);
      m.openPopup();
      leafletMap?.panTo(m.getLatLng());
    }
    scrollToParkRef(ref);
  }

  function scrollToParkRef(ref) {
    if (!myParksListEl) return;
    const idx = myParksSorted.findIndex(p => p.reference === ref);
    if (idx < 0) return;
    tick().then(() => {
      const row = myParksListEl.querySelector(`.park-row:nth-child(${idx + 1})`);
      if (row) row.scrollIntoView({ block: "center" });
    });
  }

  let renderingMap = false;
  async function renderMap() {
    if (renderingMap) return;
    renderingMap = true;
    await tick();
    destroyMap();
    if (!mapEl) { renderingMap = false; return; }
    const pts = myParks.filter(p => p.latitude != null && p.longitude != null);
    if (!pts.length) return;

    const tiles = await getMapTileConfig();
    // Re-check mapEl after async gap — DOM may have changed
    if (!mapEl) { renderingMap = false; return; }
    leafletMap = L.map(mapEl, { scrollWheelZoom: true });
    L.tileLayer(tiles.url, {
      attribution: tiles.attribution,
      maxZoom: tiles.maxZoom,
    }).addTo(leafletMap);

    markersByRef = {};
    const bounds = [];
    for (const p of pts) {
      const ll = [p.latitude, p.longitude];
      bounds.push(ll);
      const m = L.marker(ll, { icon: normalIcon })
        .bindPopup(`<b>${p.reference}</b><br>${p.name || ""}<br>${p.qso_count} QSO${p.qso_count !== 1 ? "s" : ""} <span title="${parkAwardTitle(p.qso_count)}">${parkAward(p.qso_count)}</span><br><a href="#/parks/park/${encodeURIComponent(p.reference)}">View details</a>`)
        .addTo(leafletMap);
      m.on("click", () => selectPark(p.reference));
      markersByRef[p.reference] = m;
    }
    leafletMap.on("click", deselectPark);
    leafletMap.invalidateSize();
    // Pick the initial park to focus on
    const initRef = activePark || (myParksSorted.length > 0 ? myParksSorted[0].reference : null);
    const initMarker = initRef ? markersByRef[initRef] : null;
    if (initMarker) {
      leafletMap.setView(initMarker.getLatLng(), 7);
    } else {
      leafletMap.fitBounds(bounds, { padding: [30, 30], maxZoom: 8 });
      if (leafletMap.getZoom() < 5) leafletMap.setZoom(5);
    }
    addExpandControl(leafletMap, mapEl.parentElement);
    mapResizeObserver = new ResizeObserver(() => { leafletMap?.invalidateSize(); });
    mapResizeObserver.observe(mapEl);
    if (activePark) showActivePark(activePark);
    else if (initRef) selectPark(initRef);
    renderingMap = false;
  }

  export async function refreshParks() {
    await loadMyParks();
  }

  async function loadMyParks() {
    myParksLoading = true;
    try {
      const res = await fetch("/api/pota/my-parks");
      if (res.ok) myParks = await res.json();
    } catch {}
    myParksLoading = false;
    if (tab === "my-qsos" && !loading && showMap) renderMap();
  }

  // Render map once both loads complete and we're on the my-qsos tab
  $: if (tab === "my-qsos" && showMap && !myParksLoading && !loading && myParks.length > 0 && !leafletMap) {
    renderMap();
  }

  onMount(() => {
    loadPrograms();
    loadMyParks();
    if (tab === "park" && parkRef) loadParkDetail(parkRef);
    window.addEventListener("hashchange", onHashChange);
    window.addEventListener("keydown", onFullscreenKey);
    window.addEventListener("keydown", onParksKeydown);
    window.addEventListener("resize", onWindowResize);
  });

  let mapResizeObserver;
  function onWindowResize() {
    const maxH = Math.floor(window.innerHeight * MAX_MAP_FRAC);
    if (mapHeight > maxH) {
      mapHeight = maxH;
      storageSet("parksMapHeight", String(mapHeight));
    }
    if (leafletMap) leafletMap.invalidateSize();
  }

  onDestroy(() => {
    exitFullscreen();
    destroyMap();
    window.removeEventListener("hashchange", onHashChange);
    window.removeEventListener("keydown", onFullscreenKey);
    window.removeEventListener("keydown", onParksKeydown);
    window.removeEventListener("resize", onWindowResize);
  });
</script>

<section class="parks">
  <div class="parks-header">
    <h2>POTA Parks</h2>
  </div>

  {#if tab === "park"}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <span class="back-link" on:click={() => history.back()}>&larr; Back</span>
  {:else}
    <div class="tabs">
      <button class="tab" class:active={tab === "my-qsos"} on:click={() => switchTab("my-qsos")}>My Parks</button>
      <button class="tab" class:active={tab === "by-country"} on:click={() => switchTab("by-country")}>By Country</button>
      <button class="tab" class:active={tab === "download"} on:click={() => switchTab("download")}>Cache</button>
    </div>
  {/if}

  {#if tab === "my-qsos"}
    <div class="tab-content">
      {#if myParksLoading || loading}
        <p class="loading">Loading...</p>
      {:else if totalParks === 0}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <p class="empty">No POTA park data cached. Go to the <span class="link" on:click={() => switchTab("download")}>Cache</span> tab to download parks for your countries.</p>
      {:else if myParks.length === 0}
        <p class="empty">No POTA parks contacted yet.</p>
      {:else}
        {#if showMap}
          <div class="my-map-wrap">
            <div class="my-map" bind:this={mapEl} style="height: {mapHeight}px"></div>
          </div>
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <div class="map-drag-handle" on:mousedown={onDragStart} on:touchstart={onDragStart}>
            <div class="drag-grip"></div>
          </div>
        {/if}
        <div class="stats">
          <span class="stat-highlight">{myParks.length} parks contacted</span>
          <span>{myAvgQsos} avg QSOs/park</span>
          <button class="map-toggle-btn" class:active={showMap} on:click={toggleMap}>Map</button>
        </div>
        <div class="my-sort-bar">
          <span class="my-sort-label">Sort:</span>
          <button class="my-sort-btn" class:active={mySort === "date"} on:click={() => toggleMySort("date")}>Date {mySort === "date" ? (mySortAsc ? "▲" : "▼") : ""}</button>
          <button class="my-sort-btn" class:active={mySort === "code"} on:click={() => toggleMySort("code")}>Code {mySort === "code" ? (mySortAsc ? "▲" : "▼") : ""}</button>
          <button class="my-sort-btn" class:active={mySort === "name"} on:click={() => toggleMySort("name")}>Name {mySort === "name" ? (mySortAsc ? "▲" : "▼") : ""}</button>
          <button class="my-sort-btn" class:active={mySort === "qsos"} on:click={() => toggleMySort("qsos")}>QSOs {mySort === "qsos" ? (mySortAsc ? "▲" : "▼") : ""}</button>
        </div>
        <div class="my-parks-list" bind:this={myParksListEl}>
          {#each myParksSorted as park}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
            <div class="tree-row park-row clickable" class:selected-park={selectedPark === park.reference} on:click={() => selectPark(park.reference)} on:mouseenter={() => highlightPark(park.reference)} on:mouseleave={() => unhighlightPark(park.reference)}>
              <span class="park-award" title="{parkAwardTitle(park.qso_count)}">{parkAward(park.qso_count)}</span>
              <span class="park-flag">{countryFlag(prefixFromRef(park.reference))}</span>
              <span class="park-ref">{park.reference}</span>
              <span class="park-name">{park.name || park.reference}</span>
              {#if park.grid}
                <span class="park-grid">{park.grid}</span>
              {/if}
              <span class="park-date">{park.last_contact ? park.last_contact.slice(0, 10) : ""}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>

  {:else if tab === "by-country"}
    <div class="tab-content">
      {#if cachedPrograms.length === 0}
        <p class="empty">No parks cached yet. Go to the Cache tab to select countries and fetch parks.</p>
      {:else}
        <input type="text" class="filter-input" placeholder="Filter countries..." bind:value={listFilter} />
        <div class="tree">
          {#each listFiltered as prog}
            <div class="tree-node">
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <div class="tree-row country-row" on:click={() => toggleCountry(prog.prefix)}>
                <span class="chevron" class:expanded={expandedCountries[prog.prefix]}>▶</span>
                <span class="prefix">{prog.prefix}</span>
                <span class="name">{prog.name}</span>
                <span class="badge">{prog.park_count} parks</span>
              </div>

              {#if expandedCountries[prog.prefix]}
                <div class="children">
                  {#if loadingLocations[prog.prefix]}
                    <p class="loading indent">Loading locations...</p>
                  {:else if locationsByPrefix[prog.prefix]}
                    {#each locationsByPrefix[prog.prefix] as loc}
                      {#if loc.park_count > 0}
                        <div class="tree-node">
                          <!-- svelte-ignore a11y-click-events-have-key-events -->
                          <!-- svelte-ignore a11y-no-static-element-interactions -->
                          <div class="tree-row location-row" on:click={() => toggleLocation(loc.descriptor)}>
                            <span class="chevron" class:expanded={expandedLocations[loc.descriptor]}>▶</span>
                            <span class="descriptor">{loc.descriptor}</span>
                            <span class="name">{loc.name}</span>
                            <span class="badge">{loc.park_count} parks</span>
                          </div>

                          {#if expandedLocations[loc.descriptor]}
                            <div class="children">
                              {#if loadingParks[loc.descriptor]}
                                <p class="loading indent">Loading parks...</p>
                              {:else if parksByDescriptor[loc.descriptor]}
                                {#each parksByDescriptor[loc.descriptor] as park}
                                  <!-- svelte-ignore a11y-click-events-have-key-events -->
                                  <!-- svelte-ignore a11y-no-static-element-interactions -->
                                  <div class="tree-row park-row clickable" on:click={() => viewPark(park.reference)}>
                                    <span class="park-ref">{park.reference}</span>
                                    <span class="park-name">{park.name}</span>
                                    {#if park.grid}
                                      <span class="park-grid">{park.grid}</span>
                                    {/if}
                                    {#if park.activations}
                                      <span class="park-stat">{park.activations} act</span>
                                    {/if}
                                  </div>
                                {/each}
                              {/if}
                            </div>
                          {/if}
                        </div>
                      {/if}
                    {/each}
                  {/if}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>

  {:else if tab === "download"}
    <div class="tab-content">
      <div class="stats">
        <span>{programs.length} countries</span>
        <span>{totalLocations} locations</span>
        <span class="stat-highlight">{totalParks} parks cached across {cachedCountries} {cachedCountries === 1 ? "country" : "countries"}</span>
      </div>
      <p class="description">Select countries to cache park data for. Then click Update to fetch all parks for selected countries.</p>

      <div class="controls">
        <input type="text" class="filter-input" placeholder="Filter countries..." bind:value={cacheFilter} />
        <span class="count">{selectedCount} selected</span>
        {#if dirty}
          <button class="btn save-btn" on:click={saveSelections} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </button>
        {/if}
        <button class="btn update-btn" on:click={fetchParks} disabled={fetching || selectedCount === 0}>
          {#if fetching}
            Fetching...
          {:else}
            Update Parks
          {/if}
        </button>
      </div>

      {#if fetchResult}
        <div class="fetch-result">
          {#if fetchResult.upToDate}
            All {fetchResult.locations} locations already up to date.
          {:else}
            Fetched {fetchResult.parks} parks across {fetchResult.locations} locations.{#if fetchResult.errors} ({fetchResult.errors} errors){/if}
          {/if}
        </div>
      {/if}

      {#if fetching && fetchProgress}
        <div class="progress">
          <div class="progress-bar">
            <div class="progress-fill" style="width: {(fetchProgress.done / fetchProgress.total * 100).toFixed(1)}%"></div>
          </div>
          <span class="progress-text">{fetchProgress.done} / {fetchProgress.total} locations — {fetchProgress.location || "..."}</span>
        </div>
      {/if}

      {#if loading}
        <p class="loading">Loading programs...</p>
      {:else}
        <div class="program-list">
          {#each cacheFiltered as prog}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div class="program-row" class:selected={prog.selected} on:click={() => toggle(prog.prefix)}>
              <input type="checkbox" checked={prog.selected} on:click|stopPropagation={() => toggle(prog.prefix)} />
              <span class="prefix">{prog.prefix}</span>
              <span class="name">{prog.name}</span>
              {#if prog.park_count > 0}
                <span class="badge">{prog.park_count} parks</span>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  {#if tab === "park"}
    <div class="tab-content">
      {#if parkLoading}
        <p class="loading">Loading park...</p>
      {:else if parkDetail}
        <ParkDetail park={parkDetail} showAddQso={true} on:addqso />
      {:else}
        <p class="empty">Park {parkRef} not found in cache.</p>
      {/if}
    </div>
  {/if}
</section>

<style>
  .parks {
    padding: 0;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .parks-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  h2 {
    margin: 0;
    color: var(--accent);
    font-size: 1.2rem;
  }

  .stats {
    display: flex;
    gap: 1rem;
    font-size: 0.85rem;
    color: var(--text-dim);
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
  }

  .back-link {
    color: var(--accent);
    cursor: pointer;
    font-size: 0.85rem;
    display: inline-block;
    margin-bottom: 0.75rem;
  }

  .back-link:hover {
    text-decoration: underline;
  }

  .stat-highlight {
    color: var(--accent);
  }

  /* Tabs */
  .tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0.75rem;
  }

  .tab {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-muted);
    padding: 0.4rem 1rem;
    font-family: inherit;
    font-size: 0.9rem;
    cursor: pointer;
  }

  .tab:hover {
    color: var(--text);
  }

  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
    font-weight: bold;
  }

  .tab-content {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  /* Shared */
  .description {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin: 0 0 0.75rem 0;
  }

  .empty {
    color: var(--text-dim);
    font-style: italic;
  }

  .empty .link {
    color: var(--accent);
    cursor: pointer;
    font-style: normal;
  }

  .empty .link:hover {
    text-decoration: underline;
  }

  .loading {
    color: var(--text-muted);
    font-style: italic;
  }

  .indent {
    margin-left: 2rem;
  }

  .filter-input {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 0.3rem 0.5rem;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
    outline: none;
    width: 200px;
    margin-bottom: 0.5rem;
  }

  .filter-input:focus {
    border-color: var(--accent);
  }

  .prefix, .descriptor {
    color: var(--accent-callsign);
    font-weight: bold;
    flex-shrink: 0;
    min-width: 4ch;
  }

  .name {
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .badge {
    font-size: 0.75rem;
    color: var(--text-dim);
    background: var(--bg-deep);
    padding: 0.05rem 0.4rem;
    border-radius: 8px;
    flex-shrink: 0;
    margin-left: auto;
  }

  /* My QSOs tab */
  .my-map-wrap {
    margin-bottom: 0;
  }

  .my-map {
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

  .map-toggle-btn {
    background: var(--btn-secondary);
    color: var(--text);
    border: none;
    padding: 0.2rem 0.5rem;
    font-family: inherit;
    font-size: 0.75rem;
    border-radius: 3px;
    cursor: pointer;
    margin-left: auto;
  }

  .map-toggle-btn:hover { background: var(--btn-secondary-hover); }
  .map-toggle-btn.active { background: var(--accent); color: var(--bg); }

  :global(.park-marker-dot) {
    width: 10px;
    height: 10px;
    background: #00ff88;
    border: 2px solid #005533;
    border-radius: 50%;
    transition: all 0.15s;
  }

  :global(.park-marker-dot.highlight) {
    width: 16px;
    height: 16px;
    background: #ffcc00;
    border-color: #996600;
    box-shadow: 0 0 8px rgba(255, 204, 0, 0.6);
  }
  :global(.park-marker-dot.active) {
    width: 18px;
    height: 18px;
    background: var(--accent, #00ff88);
    border-color: #006633;
    box-shadow: 0 0 10px rgba(0, 255, 136, 0.6);
  }

  .my-parks-list {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow-y: scroll;
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: 0.25rem;
  }

  .my-sort-bar {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 0.4rem;
  }

  .my-sort-label {
    color: var(--text-dim);
    font-size: 0.8rem;
  }

  .my-sort-btn {
    background: none;
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-family: inherit;
    font-size: 0.8rem;
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    cursor: pointer;
  }

  .my-sort-btn:hover {
    background: var(--row-hover);
  }

  .my-sort-btn.active {
    color: var(--accent);
    border-color: var(--accent);
  }

  .my-parks-list .tree-row {
    padding: 0.4rem 0.4rem;
    line-height: 1.6;
  }

  .my-parks-list .selected-park {
    background: var(--bg-deep);
    border-left: 3px solid var(--accent);
  }


  .park-date {
    color: var(--text-dim);
    font-size: 0.8rem;
    flex-shrink: 0;
    margin-left: auto;
  }

  /* List tab - tree */
  .tree {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .tree-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.4rem;
    cursor: pointer;
    border-radius: 3px;
    white-space: nowrap;
    overflow: hidden;
    line-height: 1.4;
  }

  .tree-row:hover {
    background: var(--row-hover);
  }

  .park-row {
    padding-left: 1rem;
    min-height: 1.2em;
  }

  .park-row.clickable {
    cursor: pointer;
  }

  .children {
    margin-left: 1.2rem;
  }

  .chevron {
    display: inline-block;
    font-size: 0.7rem;
    transition: transform 0.15s;
    color: var(--text-dim);
    width: 0.8rem;
    flex-shrink: 0;
  }

  .chevron.expanded {
    transform: rotate(90deg);
  }

  .park-flag {
    flex-shrink: 0;
    font-size: 0.9rem;
    display: inline-block;
    width: 1.2em;
    text-align: center;
  }

  .park-ref {
    color: var(--accent-vfo);
    font-weight: bold;
    flex-shrink: 0;
    min-width: 7ch;
  }

  .park-name {
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
    min-width: 0;
  }

  .park-grid {
    color: var(--text-muted);
    font-size: 0.85rem;
    flex-shrink: 0;
    width: 7ch;
    text-align: right;
  }

  .park-stat {
    color: var(--text-dim);
    font-size: 0.8rem;
    flex-shrink: 0;
  }

  /* Cache tab */
  .controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
  }

  .controls .filter-input {
    margin-bottom: 0;
  }

  .count {
    color: var(--text-dim);
    font-size: 0.85rem;
  }

  .btn {
    padding: 0.3rem 0.8rem;
    font-size: 0.85rem;
    border-radius: 3px;
    border: none;
    cursor: pointer;
    font-family: inherit;
    font-weight: bold;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .save-btn {
    background: var(--btn-secondary);
    color: var(--text);
  }

  .update-btn {
    background: var(--accent);
    color: var(--bg);
  }

  .update-btn:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .progress {
    margin-bottom: 0.75rem;
  }

  .progress-bar {
    height: 6px;
    background: var(--bg-deep);
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 0.25rem;
  }

  .progress-fill {
    height: 100%;
    background: var(--accent);
    transition: width 0.2s;
  }

  .progress-text {
    font-size: 0.75rem;
    color: var(--text-dim);
  }

  .fetch-result {
    font-size: 0.85rem;
    color: var(--accent);
    margin-bottom: 0.75rem;
  }

  .program-list {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .program-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.4rem;
    cursor: pointer;
    border-radius: 3px;
    white-space: nowrap;
    line-height: 1.4;
  }

  .program-row:hover {
    background: var(--row-hover);
  }

  .program-row.selected {
    background: var(--bg-deep);
  }

  .program-row input[type="checkbox"] {
    cursor: pointer;
    flex-shrink: 0;
  }

  :global(.map-fullscreen .my-map) {
    height: 100% !important;
  }
</style>
