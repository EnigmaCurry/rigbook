<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";
  import { QrzLookup, formatFreq, locationStr } from "./qrzLookup.js";

  const dispatch = createEventDispatcher();

  let spots = [];
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
        spots = await res.json();
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
    await loadDefaultFilters();
    fetchSpots();
    statusInterval = setInterval(() => { fetchStatus(); fetchBands(); fetchModes(); }, 5000);
    spotsInterval = setInterval(fetchSpots, 3000);
  });

  onDestroy(() => {
    clearInterval(statusInterval);
    clearInterval(spotsInterval);
    qrz.destroy();
  });

  $: bandList = Object.keys(bands).sort((a, b) => {
    const numA = parseInt(a);
    const numB = parseInt(b);
    return numB - numA;
  });

  $: modeList = Object.keys(modes).sort((a, b) => (modes[b] || 0) - (modes[a] || 0));

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
    <button class="restart-btn" on:click={restart} disabled={restarting}>
      {restarting ? "Restarting..." : "Restart Feeds"}
    </button>
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
          <tr>
            <td class="mono">{formatTime(spot)}</td>
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <td class="mono call clickable" on:click={() => dispatch("addqso", spot)} title="Log QSO with {spot.callsign}">{spot.callsign}</td>
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
</style>
