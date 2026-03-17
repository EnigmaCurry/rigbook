<script>
  import { onMount, onDestroy, tick } from "svelte";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";

  // --- Tab routing ---
  const TABS = ["my-qsos", "by-country", "download"];
  let tab = parseTab();
  let parkRef = parseParkRef();
  let parkDetail = null;
  let parkLoading = false;

  // --- My QSOs state ---
  let myParks = [];
  let myParksLoading = false;
  let mapEl;
  let leafletMap = null;
  let markersByRef = {};

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

  function parkAward(count) {
    if (count >= 20) return "🏆";
    if (count >= 15) return "💎";
    if (count >= 10) return "🌟";
    if (count >= 5) return "⭐";
    if (count >= 2) return "🥈";
    if (count >= 1) return "🥇";
    return "";
  }

  function destroyMap() {
    if (leafletMap) { leafletMap.remove(); leafletMap = null; }
    markersByRef = {};
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

  function highlightPark(ref) {
    const m = markersByRef[ref];
    if (m) { m.setIcon(highlightIcon); m.openPopup(); }
  }

  function unhighlightPark(ref) {
    const m = markersByRef[ref];
    if (m) { m.setIcon(normalIcon); m.closePopup(); }
  }

  async function renderMap() {
    await tick();
    destroyMap();
    if (!mapEl) return;
    const pts = myParks.filter(p => p.latitude != null && p.longitude != null);
    if (!pts.length) return;

    leafletMap = L.map(mapEl, { scrollWheelZoom: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
      maxZoom: 18,
    }).addTo(leafletMap);

    markersByRef = {};
    const bounds = [];
    for (const p of pts) {
      const ll = [p.latitude, p.longitude];
      bounds.push(ll);
      const m = L.marker(ll, { icon: normalIcon })
        .bindPopup(`<b>${p.reference}</b><br>${p.name || ""}<br>${p.qso_count} QSO${p.qso_count !== 1 ? "s" : ""} ${parkAward(p.qso_count)}`)
        .addTo(leafletMap);
      markersByRef[p.reference] = m;
    }
    leafletMap.fitBounds(bounds, { padding: [30, 30], maxZoom: 8 });
  }

  async function loadMyParks() {
    myParksLoading = true;
    try {
      const res = await fetch("/api/pota/my-parks");
      if (res.ok) myParks = await res.json();
    } catch {}
    myParksLoading = false;
    if (tab === "my-qsos") renderMap();
  }

  onMount(() => {
    loadPrograms();
    loadMyParks();
    if (tab === "park" && parkRef) loadParkDetail(parkRef);
    window.addEventListener("hashchange", onHashChange);
  });

  onDestroy(() => {
    destroyMap();
    window.removeEventListener("hashchange", onHashChange);
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
    <div class="stats">
      <span>{programs.length} countries</span>
      <span>{totalLocations} locations</span>
      <span class="stat-highlight">{totalParks} parks cached across {cachedCountries} {cachedCountries === 1 ? "country" : "countries"}</span>
    </div>

    <div class="tabs">
      <button class="tab" class:active={tab === "my-qsos"} on:click={() => switchTab("my-qsos")}>My QSOs</button>
      <button class="tab" class:active={tab === "by-country"} on:click={() => switchTab("by-country")}>By Country</button>
      <button class="tab" class:active={tab === "download"} on:click={() => switchTab("download")}>Download</button>
    </div>
  {/if}

  {#if tab === "my-qsos"}
    <div class="tab-content">
      {#if myParksLoading}
        <p class="loading">Loading...</p>
      {:else if myParks.length === 0}
        <p class="empty">No POTA QSOs logged yet.</p>
      {:else}
        <div class="my-map-wrap">
          <div class="my-map" bind:this={mapEl}></div>
        </div>
        <div class="my-parks-list">
          {#each myParks as park}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
            <div class="tree-row park-row clickable" on:click={() => viewPark(park.reference)} on:mouseenter={() => highlightPark(park.reference)} on:mouseleave={() => unhighlightPark(park.reference)}>
              <span class="park-ref">{park.reference}</span>
              <span class="park-name">{park.name || park.reference}</span>
              {#if park.grid}
                <span class="park-grid">{park.grid}</span>
              {/if}
              <span class="park-stat">{park.qso_count} QSO{park.qso_count !== 1 ? "s" : ""} {parkAward(park.qso_count)}</span>
              <span class="park-date">{park.last_contact ? park.last_contact.slice(0, 10) : ""}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>

  {:else if tab === "by-country"}
    <div class="tab-content">
      {#if cachedPrograms.length === 0}
        <p class="empty">No parks cached yet. Go to the Download tab to select countries and fetch parks.</p>
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
        <div class="park-detail">
          <h3>{parkDetail.reference}</h3>
          <p class="park-detail-name">{parkDetail.name}</p>
          <div class="park-detail-grid">
            <div class="detail-row"><span class="detail-label">Location</span> <span>{parkDetail.location_name || ""} ({parkDetail.location_desc})</span></div>
            <div class="detail-row"><span class="detail-label">Country</span> <span>{parkDetail.program_name || ""}</span></div>
            {#if parkDetail.grid}
              <div class="detail-row"><span class="detail-label">Grid</span> <span>{parkDetail.grid}</span></div>
            {/if}
            {#if parkDetail.latitude != null && parkDetail.longitude != null}
              <div class="detail-row"><span class="detail-label">Coordinates</span> <span>{parkDetail.latitude}, {parkDetail.longitude}</span></div>
            {/if}
            {#if parkDetail.activations != null}
              <div class="detail-row"><span class="detail-label">Activations</span> <span>{parkDetail.activations}</span></div>
            {/if}
            {#if parkDetail.attempts != null}
              <div class="detail-row"><span class="detail-label">Attempts</span> <span>{parkDetail.attempts}</span></div>
            {/if}
            {#if parkDetail.qsos != null}
              <div class="detail-row"><span class="detail-label">QSOs</span> <span>{parkDetail.qsos}</span></div>
            {/if}
            <div class="detail-row">
              <span class="detail-label">My QSOs</span>
              <span>{parkDetail.my_qsos || 0} {parkAward(parkDetail.my_qsos || 0)}</span>
            </div>
          </div>
          {#if parkDetail.latitude != null && parkDetail.longitude != null}
            <iframe
              class="park-map"
              title="Park location"
              src="https://www.openstreetmap.org/export/embed.html?bbox={parkDetail.longitude - 0.05},{parkDetail.latitude - 0.03},{parkDetail.longitude + 0.05},{parkDetail.latitude + 0.03}&layer=mapnik&marker={parkDetail.latitude},{parkDetail.longitude}"
              frameborder="0"
            ></iframe>
          {/if}
          <div class="park-detail-links">
            <a href="https://pota.app/#/park/{parkDetail.reference}" target="_blank" rel="noopener">View on POTA</a>
          </div>
        </div>
      {:else}
        <p class="empty">Park {parkRef} not found in cache.</p>
      {/if}
    </div>
  {/if}
</section>

<style>
  .parks {
    padding: 0;
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
    min-height: 200px;
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
    margin-bottom: 0.75rem;
  }

  .my-map {
    width: 100%;
    height: 350px;
    border: 1px solid var(--border);
    border-radius: 3px;
  }

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

  .my-parks-list {
    display: flex;
    flex-direction: column;
    height: 40vh;
    overflow-y: scroll;
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: 0.25rem;
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
    max-height: 65vh;
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
  }

  .park-grid {
    color: var(--text-muted);
    font-size: 0.85rem;
    flex-shrink: 0;
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
    max-height: 60vh;
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

  /* Park detail */
  .park-detail h3 {
    color: var(--accent-vfo);
    font-size: 1.3rem;
    margin: 0 0 0.25rem 0;
  }

  .park-detail-name {
    font-size: 1.1rem;
    color: var(--text);
    margin: 0 0 1rem 0;
  }

  .park-detail-grid {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin-bottom: 1rem;
  }

  .detail-row {
    display: flex;
    gap: 0.75rem;
    font-size: 0.9rem;
  }

  .detail-label {
    color: var(--text-dim);
    min-width: 10ch;
    flex-shrink: 0;
  }

  .park-map {
    width: 100%;
    max-width: 500px;
    height: 250px;
    border: 1px solid var(--border);
    border-radius: 3px;
    margin-bottom: 0.75rem;
  }

  .park-detail-links {
    margin-top: 0.75rem;
  }

  .park-detail-links a {
    color: var(--accent);
    text-decoration: none;
    font-size: 0.85rem;
  }

  .park-detail-links a:hover {
    text-decoration: underline;
  }
</style>
