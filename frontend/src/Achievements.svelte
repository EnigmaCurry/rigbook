<script>
  import { onMount } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";

  const FILTER_KEY = "achievements_filters";

  let activeTab = "states";
  let filterMode = "";
  let filterBands = new Set();
  let filterPota = false;
  let filterSkcc = false;
  let filtersLoaded = false;
  let loading = true;

  // Reference data (fetched once)
  let usStates = [];
  let dxccEntities = {};

  // Achievement data (re-fetched on filter change)
  let workedStates = [];
  let workedDxcc = [];
  let workedGrids = [];
  let availableModes = [];
  let availableBands = [];
  let matrix = { state_band: {}, state_mode: {}, dxcc_band: {}, dxcc_mode: {} };

  $: workedStatesSet = new Set(workedStates.map(s => s.toUpperCase()));
  $: matchedStates = usStates.filter(s => workedStatesSet.has(s.short) || workedStatesSet.has(s.name.toUpperCase()));
  $: stateCount = matchedStates.length;
  $: totalStates = usStates.length;
  $: statePct = totalStates > 0 ? Math.round(stateCount / totalStates * 100) : 0;
  $: missingStates = usStates.filter(s => !workedStatesSet.has(s.short) && !workedStatesSet.has(s.name.toUpperCase()));

  $: totalDxcc = Object.keys(dxccEntities).length;
  $: dxccPct = totalDxcc > 0 ? Math.round(workedDxcc.length / totalDxcc * 100) : 0;
  $: workedDxccSet = new Set(workedDxcc.map(String));
  $: missingDxcc = Object.entries(dxccEntities).filter(([k]) => !workedDxccSet.has(k)).map(([k, v]) => ({ code: k, name: v }));

  function toggleBand(b) {
    if (filterBands.has(b)) {
      filterBands.delete(b);
    } else {
      filterBands.add(b);
    }
    filterBands = filterBands; // trigger reactivity
  }

  async function loadFilters() {
    try {
      const res = await fetch(`/api/settings/${FILTER_KEY}`);
      if (res.ok) {
        const data = await res.json();
        if (data.value) {
          const saved = JSON.parse(data.value);
          filterMode = saved.mode || "";
          filterBands = saved.bands ? new Set(saved.bands.split(",").filter(Boolean)) : new Set();
          filterPota = saved.pota || false;
          filterSkcc = saved.skcc || false;
          activeTab = saved.tab || "states";
        }
      }
    } catch {}
    filtersLoaded = true;
  }

  async function saveFilters() {
    if (!filtersLoaded) return;
    try {
      await fetch(`/api/settings/${FILTER_KEY}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: JSON.stringify({
          mode: filterMode,
          bands: [...filterBands].join(","),
          pota: filterPota,
          skcc: filterSkcc,
          tab: activeTab,
        }) }),
      });
    } catch {}
  }

  async function fetchAchievements() {
    const params = new URLSearchParams();
    if (filterMode) params.set("mode", filterMode);
    // For band filter, use first selected band (API supports single band)
    // If multiple bands selected, we'll need to make multiple requests or filter client-side
    if (filterBands.size === 1) {
      params.set("band", [...filterBands][0]);
    }
    if (filterPota) params.set("pota", "true");
    if (filterSkcc) params.set("skcc", "true");
    const qs = params.toString();
    try {
      const res = await fetch(`/api/achievements${qs ? "?" + qs : ""}`);
      if (res.ok) {
        const data = await res.json();
        workedStates = data.states;
        workedDxcc = data.dxcc;
        workedGrids = data.grids;
        availableModes = data.modes;
        availableBands = data.bands_used;
        matrix = data.matrix;
      }
    } catch {}
    loading = false;
  }

  async function fetchReference() {
    try {
      const res = await fetch("/api/achievements/reference");
      if (res.ok) {
        const data = await res.json();
        usStates = data.us_states;
        dxccEntities = data.dxcc_entities;
      }
    } catch {}
  }

  $: if (filtersLoaded) {
    const _f = { m: filterMode, b: [...filterBands].join(","), p: filterPota, s: filterSkcc, t: activeTab };
    saveFilters();
    fetchAchievements();
  }

  onMount(async () => {
    await fetchReference();
    await loadFilters();
  });

  // Band order for matrix columns
  const BAND_ORDER = ["160m","80m","60m","40m","30m","20m","17m","15m","12m","10m","6m","2m"];
  $: matrixBands = BAND_ORDER.filter(b => availableBands.includes(b));
</script>

<div class="achievements">
  <h2>Achievements</h2>

  <div class="controls">
    <div class="tabs">
      <button class="tab" class:active={activeTab === "states"} on:click={() => activeTab = "states"}>States</button>
      <button class="tab" class:active={activeTab === "countries"} on:click={() => activeTab = "countries"}>Countries</button>
      <button class="tab" class:active={activeTab === "grids"} on:click={() => activeTab = "grids"}>Grids</button>
    </div>
  </div>

  <div class="filters">
    {#each availableBands as b}
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <span
        class="band-badge"
        class:active={filterBands.has(b)}
        style="background: {bandColor(b)}; color: {bandTextColor(b)}; opacity: {filterBands.size > 0 && !filterBands.has(b) ? 0.3 : 1}"
        on:click={() => toggleBand(b)}
      >
        {b}
      </span>
    {/each}
    {#if filterBands.size > 0}
      <button class="btn-clear" on:click={() => { filterBands = new Set(); }}>Clear bands</button>
    {/if}
    <select bind:value={filterMode}>
      <option value="">All Modes</option>
      {#each availableModes as m}
        <option value={m}>{m}</option>
      {/each}
    </select>
    <label class="filter-check"><input type="checkbox" bind:checked={filterPota} /> POTA</label>
    <label class="filter-check"><input type="checkbox" bind:checked={filterSkcc} /> SKCC</label>
  </div>

  {#if loading}
    <p class="status">Loading...</p>
  {:else if activeTab === "states"}
    <div class="section">
      <div class="progress-row">
        <span class="progress-label">{stateCount} / {totalStates} states ({statePct}%)</span>
        <div class="progress-bar"><div class="progress-fill" style="width: {statePct}%"></div></div>
      </div>

      {#if matrixBands.length > 0 && filterBands.size === 0}
        <h3>Band Matrix</h3>
        <div class="matrix-wrap">
          <table class="matrix">
            <thead>
              <tr>
                <th>State</th>
                {#each matrixBands as b}
                  <th style="background: {bandColor(b)}; color: {bandTextColor(b)}">{b}</th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each workedStates as st}
                <tr>
                  <td>{st}</td>
                  {#each matrixBands as b}
                    <td class="matrix-cell" class:worked={matrix.state_band[st]?.includes(b)}>{matrix.state_band[st]?.includes(b) ? "+" : ""}</td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

      <div class="lists">
        <div class="list-col">
          <h3>Worked ({workedStates.length})</h3>
          <ul>{#each workedStates as st}<li>{st}</li>{/each}</ul>
        </div>
        <div class="list-col">
          <h3>Missing ({missingStates.length})</h3>
          <ul>{#each missingStates as st}<li class="missing">{st.name} ({st.short})</li>{/each}</ul>
        </div>
      </div>
    </div>

  {:else if activeTab === "countries"}
    <div class="section">
      <div class="progress-row">
        <span class="progress-label">{workedDxcc.length} / {totalDxcc} DXCC entities ({dxccPct}%)</span>
        <div class="progress-bar"><div class="progress-fill" style="width: {dxccPct}%"></div></div>
      </div>

      {#if matrixBands.length > 0 && filterBands.size === 0}
        <h3>Band Matrix</h3>
        <div class="matrix-wrap">
          <table class="matrix">
            <thead>
              <tr>
                <th>Entity</th>
                {#each matrixBands as b}
                  <th style="background: {bandColor(b)}; color: {bandTextColor(b)}">{b}</th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each workedDxcc as code}
                <tr>
                  <td>{dxccEntities[String(code)] || code}</td>
                  {#each matrixBands as b}
                    <td class="matrix-cell" class:worked={matrix.dxcc_band[String(code)]?.includes(b)}>{matrix.dxcc_band[String(code)]?.includes(b) ? "+" : ""}</td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

      <div class="lists">
        <div class="list-col">
          <h3>Worked ({workedDxcc.length})</h3>
          <ul>{#each workedDxcc as code}<li>{dxccEntities[String(code)] || code}</li>{/each}</ul>
        </div>
        <div class="list-col">
          <h3>Missing ({missingDxcc.length})</h3>
          <ul>{#each missingDxcc.slice(0, 100) as ent}<li class="missing">{ent.name}</li>{/each}
            {#if missingDxcc.length > 100}<li class="missing">...and {missingDxcc.length - 100} more</li>{/if}
          </ul>
        </div>
      </div>
    </div>

  {:else if activeTab === "grids"}
    <div class="section">
      <div class="progress-row">
        <span class="progress-label">{workedGrids.length} unique grid squares worked</span>
      </div>

      <div class="grid-list">
        {#each workedGrids as g}
          <span class="grid-tag">{g}</span>
        {/each}
        {#if workedGrids.length === 0}
          <p class="status">No grids logged yet.</p>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .achievements {
    padding: 0.5rem 1rem 2rem;
    max-width: 1200px;
    margin: 0 auto;
  }
  h2 { margin: 0 0 0.5rem; }
  h3 { margin: 0.8rem 0 0.4rem; font-size: 0.95rem; }

  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.5rem;
  }
  .tabs {
    display: flex;
    gap: 0.25rem;
  }
  .tab {
    background: var(--bg-input);
    color: var(--text);
    border: 1px solid var(--border-input);
    border-radius: 3px;
    padding: 0.3rem 0.7rem;
    font-family: inherit;
    font-size: 0.85rem;
    cursor: pointer;
  }
  .tab.active {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }

  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.8rem;
  }
  .band-badge {
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    cursor: pointer;
    user-select: none;
    transition: opacity 0.15s;
    border: 2px solid transparent;
  }
  .band-badge.active {
    border-color: var(--accent, #fff);
  }
  .btn-clear {
    background: var(--bg-input);
    color: var(--text);
    border: 1px solid var(--border-input);
    border-radius: 3px;
    padding: 0.3rem 0.5rem;
    font-family: inherit;
    font-size: 0.8rem;
    cursor: pointer;
  }
  select {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 0.3rem 0.5rem;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 3px;
  }
  .filter-check {
    font-size: 0.8rem;
    cursor: pointer;
    user-select: none;
    display: flex;
    align-items: center;
    gap: 0.2rem;
  }

  .status { color: var(--text-muted); }

  .progress-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
  }
  .progress-label {
    font-size: 0.9rem;
    white-space: nowrap;
  }
  .progress-bar {
    flex: 1;
    height: 12px;
    background: var(--bg-input);
    border-radius: 6px;
    overflow: hidden;
  }
  .progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 6px;
    transition: width 0.3s;
  }

  .lists {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-top: 0.5rem;
  }
  .list-col ul {
    list-style: none;
    padding: 0;
    margin: 0;
    font-size: 0.85rem;
  }
  .list-col li {
    padding: 0.15rem 0;
  }
  .list-col li.missing {
    color: var(--text-muted);
  }

  .matrix-wrap {
    overflow-x: auto;
    margin-bottom: 0.5rem;
  }
  .matrix {
    border-collapse: collapse;
    font-size: 0.75rem;
    width: 100%;
  }
  .matrix th, .matrix td {
    border: 1px solid var(--border-input);
    padding: 0.15rem 0.3rem;
    text-align: center;
    white-space: nowrap;
  }
  .matrix th {
    font-weight: bold;
    position: sticky;
    top: 0;
  }
  .matrix td:first-child {
    text-align: left;
    font-weight: 500;
    position: sticky;
    left: 0;
    background: var(--bg-card);
  }
  .matrix-cell {
    background: var(--bg-deep, var(--bg-card));
  }
  .matrix-cell.worked {
    background: var(--accent);
    color: #fff;
    font-weight: bold;
  }

  .grid-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.5rem;
  }
  .grid-tag {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    border-radius: 3px;
    padding: 0.15rem 0.4rem;
    font-size: 0.8rem;
    font-family: monospace;
  }

  @media (max-width: 600px) {
    .lists { grid-template-columns: 1fr; }
  }
</style>
