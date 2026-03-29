<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";

  const dispatch = createEventDispatcher();

  export let initialQuery = "";

  let query = initialQuery;
  let contacts = [];
  let loading = false;
  let filtersOpen = false;
  let debounceTimer;

  // Advanced filters
  let filterCall = "";
  let filterMode = "";
  let filterBand = "";
  let filterDateFrom = "";
  let filterDateTo = "";
  let filterCountry = "";
  let filterState = "";
  let filterGrid = "";
  let filterPotaPark = "";
  let filterComments = "";
  let filterSkcc = "";
  let filtersLoaded = false;

  const BANDS = [
    { name: "160m", lo: 1800, hi: 2000 },
    { name: "80m", lo: 3500, hi: 4000 },
    { name: "60m", lo: 5330, hi: 5410 },
    { name: "40m", lo: 7000, hi: 7300 },
    { name: "30m", lo: 10100, hi: 10150 },
    { name: "20m", lo: 14000, hi: 14350 },
    { name: "17m", lo: 18068, hi: 18168 },
    { name: "15m", lo: 21000, hi: 21450 },
    { name: "12m", lo: 24890, hi: 24990 },
    { name: "10m", lo: 28000, hi: 29700 },
    { name: "6m", lo: 50000, hi: 54000 },
    { name: "2m", lo: 144000, hi: 148000 },
  ];

  function freqToBand(f) {
    const n = parseFloat(f);
    if (isNaN(n)) return "";
    const b = BANDS.find(b => n >= b.lo && n <= b.hi);
    return b ? b.name : "";
  }

  function formatFreq(f) {
    if (!f) return "--";
    const n = parseFloat(f);
    if (isNaN(n)) return f;
    return n.toFixed(1).padStart(9, "\u2007") + " KHz";
  }

  function formatTimestamp(ts) {
    if (!ts) return "";
    try {
      const d = new Date(ts);
      return d.toISOString().replace("T", " ").substring(0, 19) + "z";
    } catch {
      return ts;
    }
  }

  $: hasAdvancedFilters = filterCall || filterMode || filterBand || filterDateFrom || filterDateTo || filterCountry || filterState || filterGrid || filterPotaPark || filterComments || filterSkcc;
  $: hasAnyFilter = query.trim() || hasAdvancedFilters;

  function scheduleFetch() {
    if (!filtersLoaded) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(doSearch, 300);
    saveFilters();
  }

  $: if (filtersLoaded) {
    // Trigger on any filter change
    query, filterCall, filterMode, filterBand, filterDateFrom, filterDateTo,
    filterCountry, filterState, filterGrid, filterPotaPark, filterComments, filterSkcc;
    scheduleFetch();
  }

  async function doSearch() {
    if (!query.trim() && !hasAdvancedFilters) {
      contacts = [];
      return;
    }
    loading = true;
    try {
      const params = new URLSearchParams();
      if (query.trim()) params.set("q", query.trim());
      if (filterCall) params.set("call", filterCall);
      if (filterMode) params.set("mode", filterMode);
      if (filterBand) params.set("band", filterBand);
      if (filterDateFrom) params.set("date_from", filterDateFrom);
      if (filterDateTo) params.set("date_to", filterDateTo);
      if (filterCountry) params.set("country", filterCountry);
      if (filterState) params.set("state", filterState);
      if (filterGrid) params.set("grid", filterGrid);
      if (filterPotaPark) params.set("pota_park", filterPotaPark);
      if (filterComments) params.set("comments", filterComments);
      if (filterSkcc) params.set("skcc", filterSkcc);
      const qs = params.toString();
      const res = await fetch(`/api/search/advanced${qs ? "?" + qs : ""}`);
      if (res.ok) contacts = await res.json();
    } catch {}
    loading = false;
  }

  function clearAll() {
    query = "";
    filterCall = "";
    filterMode = "";
    filterBand = "";
    filterDateFrom = "";
    filterDateTo = "";
    filterCountry = "";
    filterState = "";
    filterGrid = "";
    filterPotaPark = "";
    filterComments = "";
    filterSkcc = "";
  }

  function editContact(c) {
    dispatch("editcontact", c.id);
  }

  function onSearchKeydown(e) {
    if (e.key === "Escape") {
      e.target.blur();
    }
  }

  async function saveFilters() {
    try {
      const data = {
        query, filterCall, filterMode, filterBand, filterDateFrom, filterDateTo,
        filterCountry, filterState, filterGrid, filterPotaPark, filterComments, filterSkcc,
      };
      await fetch("/api/settings/search_filters", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: JSON.stringify(data) }),
      });
    } catch {}
  }

  async function loadFilters() {
    try {
      const res = await fetch("/api/settings/search_filters");
      if (res.ok) {
        const setting = await res.json();
        if (setting.value) {
          const data = JSON.parse(setting.value);
          if (!initialQuery && data.query) query = data.query;
          filterCall = data.filterCall || "";
          filterMode = data.filterMode || "";
          filterBand = data.filterBand || "";
          filterDateFrom = data.filterDateFrom || "";
          filterDateTo = data.filterDateTo || "";
          filterCountry = data.filterCountry || "";
          filterState = data.filterState || "";
          filterGrid = data.filterGrid || "";
          filterPotaPark = data.filterPotaPark || "";
          filterComments = data.filterComments || "";
          filterSkcc = data.filterSkcc || "";
          if (data.filterCall || data.filterMode || data.filterBand || data.filterDateFrom ||
              data.filterDateTo || data.filterCountry || data.filterState || data.filterGrid ||
              data.filterPotaPark || data.filterComments || data.filterSkcc) {
            filtersOpen = true;
          }
        }
      }
    } catch {}
  }

  onMount(async () => {
    await loadFilters();
    if (initialQuery) query = initialQuery;
    filtersLoaded = true;
    doSearch();
  });
</script>

<div class="search-page">
  <div class="search-header">
    <h2>Search</h2>
    <div class="search-bar">
      <input
        type="search"
        bind:value={query}
        on:keydown={onSearchKeydown}
        placeholder="Search all fields..."
        class="search-input"
        autofocus
      />
      {#if hasAnyFilter}
        <button class="clear-btn" on:click={clearAll} title="Clear all filters">Clear</button>
      {/if}
    </div>
    <button class="toggle-filters" class:active={filtersOpen} on:click={() => filtersOpen = !filtersOpen}>
      Filters {#if hasAdvancedFilters}●{/if}
    </button>
  </div>

  {#if filtersOpen}
    <div class="filters">
      <div class="filter-row">
        <label>
          Date from
          <input type="date" bind:value={filterDateFrom} />
        </label>
        <label>
          Date to
          <input type="date" bind:value={filterDateTo} />
        </label>
      </div>
      <div class="filter-row">
        <label>
          Call
          <input type="text" bind:value={filterCall} placeholder="callsign" />
        </label>
        <label>
          Mode
          <input type="text" bind:value={filterMode} placeholder="e.g. CW, SSB" />
        </label>
        <label>
          Band
          <select bind:value={filterBand}>
            <option value="">All</option>
            {#each BANDS as b}
              <option value={b.name}>{b.name}</option>
            {/each}
          </select>
        </label>
      </div>
      <div class="filter-row">
        <label>
          Country
          <input type="text" bind:value={filterCountry} placeholder="country" />
        </label>
        <label>
          State
          <input type="text" bind:value={filterState} placeholder="state" />
        </label>
        <label>
          Grid
          <input type="text" bind:value={filterGrid} placeholder="grid prefix" />
        </label>
      </div>
      <div class="filter-row">
        <label>
          POTA Park
          <input type="text" bind:value={filterPotaPark} placeholder="park ref" />
        </label>
        <label>
          Comments / Notes
          <input type="text" bind:value={filterComments} placeholder="substring" />
        </label>
        <label>
          SKCC
          <input type="text" bind:value={filterSkcc} placeholder="SKCC #" />
        </label>
      </div>
    </div>
  {/if}

  <div class="results-info">
    {#if loading}
      Searching...
    {:else if hasAnyFilter}
      {contacts.length} result{contacts.length !== 1 ? "s" : ""}
    {:else}
      Enter a search term or set filters
    {/if}
  </div>

  {#if contacts.length > 0}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Date/Time</th>
            <th>Call</th>
            <th>Name</th>
            <th>Freq</th>
            <th>Mode</th>
            <th>POTA</th>
            <th>QTH</th>
            <th>State</th>
            <th>Country</th>
            <th>RST S</th>
            <th>RST R</th>
            <th>Comments</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {#each contacts as c (c.id)}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <tr class="clickable" on:click={() => editContact(c)}>
              <td class="nowrap">{formatTimestamp(c.timestamp)}</td>
              <td class="call">{c.call}{#if c.pota_park} 🌲{/if}</td>
              <td class="truncate">{c.name || ""}</td>
              <td class="nowrap">{formatFreq(c.freq)} {#if freqToBand(c.freq)}<span class="band-tag" style="background: {bandColor(freqToBand(c.freq))}; color: {bandTextColor(freqToBand(c.freq))}">{freqToBand(c.freq)}</span>{/if}</td>
              <td>{c.mode || ""}</td>
              <td class="truncate">{c.pota_park || ""}</td>
              <td class="truncate">{c.qth || ""}</td>
              <td>{c.state || ""}</td>
              <td class="truncate">{c.country || ""}</td>
              <td>{c.rst_sent || ""}</td>
              <td>{c.rst_recv || ""}</td>
              <td class="truncate">{c.comments || ""}</td>
              <td class="truncate">{c.notes || ""}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .search-page {
    padding: 0.5rem;
    max-width: 100%;
  }

  .search-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
  }

  .search-header h2 {
    margin: 0;
    font-size: 1.1rem;
    white-space: nowrap;
  }

  .search-bar {
    display: flex;
    gap: 0.4rem;
    flex: 1;
    min-width: 200px;
  }

  .search-input {
    flex: 1;
    background: var(--bg-input, var(--bg));
    border: 1px solid var(--border-input, var(--border, #555));
    color: var(--text);
    padding: 0.35rem 0.5rem;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
    -webkit-appearance: none;
    appearance: none;
  }

  .search-input:focus {
    outline: none;
    border-color: var(--accent);
  }

  .search-input::-webkit-search-cancel-button,
  .search-input::-webkit-search-decoration {
    display: none;
  }

  .clear-btn {
    background: none;
    border: 1px solid var(--border, #555);
    color: var(--text-muted);
    padding: 0.3rem 0.6rem;
    font-size: 0.8rem;
    border-radius: 3px;
    cursor: pointer;
    white-space: nowrap;
  }

  .clear-btn:hover {
    color: var(--text);
    border-color: var(--text-muted);
  }

  .toggle-filters {
    background: none;
    border: 1px solid var(--border, #555);
    color: var(--text-muted);
    padding: 0.3rem 0.6rem;
    font-size: 0.8rem;
    border-radius: 3px;
    cursor: pointer;
    white-space: nowrap;
  }

  .toggle-filters:hover,
  .toggle-filters.active {
    color: var(--text);
    border-color: var(--accent);
  }

  .filters {
    margin-bottom: 0.75rem;
    padding: 0.5rem;
    border: 1px solid var(--border, #555);
    border-radius: 4px;
    background: var(--bg-card, var(--bg));
  }

  .filter-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
    align-items: end;
  }

  .filter-row:last-child {
    margin-bottom: 0;
  }

  .filter-row label {
    display: flex;
    flex-direction: column;
    font-size: 0.8rem;
    color: var(--text-muted);
    gap: 0.2rem;
  }

  .filter-row input[type="date"],
  .filter-row input[type="text"],
  .filter-row select {
    background: var(--bg-input, var(--bg));
    color: var(--text);
    border: 1px solid var(--border, #555);
    padding: 0.35rem 0.5rem;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
  }

  .results-info {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
  }

  .table-wrap {
    overflow-x: auto;
    max-width: 100%;
  }

  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 0.8rem;
  }

  th {
    text-align: left;
    padding: 0.3rem 0.5rem;
    border-bottom: 2px solid var(--border, #555);
    white-space: nowrap;
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  td {
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid var(--border, #333);
    vertical-align: top;
  }

  tr.clickable {
    cursor: pointer;
  }

  tr.clickable:hover {
    background: var(--bg-hover, rgba(255, 255, 255, 0.05));
  }

  .call {
    font-weight: bold;
    color: var(--accent-callsign, var(--accent));
    white-space: nowrap;
  }

  .nowrap {
    white-space: nowrap;
  }

  .truncate {
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .band-tag {
    display: inline-block;
    padding: 0 0.3rem;
    border-radius: 3px;
    font-size: 0.7rem;
    font-weight: bold;
    margin-left: 0.3rem;
    vertical-align: middle;
  }
</style>
