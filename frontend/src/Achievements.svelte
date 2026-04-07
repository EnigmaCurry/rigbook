<script>
  import { onMount } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";

  const FILTER_KEY = "achievements_filters";

  let activeTab = "states";
  let filterMode = "";
  let filterBand = "";
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

  $: stateCount = workedStates.length;
  $: totalStates = usStates.length;
  $: statePct = totalStates > 0 ? Math.round(stateCount / totalStates * 100) : 0;
  $: missingStates = usStates.filter(s => !workedStates.includes(s.name));

  $: totalDxcc = Object.keys(dxccEntities).length;
  $: dxccPct = totalDxcc > 0 ? Math.round(workedDxcc.length / totalDxcc * 100) : 0;
  $: workedDxccSet = new Set(workedDxcc.map(String));
  $: missingDxcc = Object.entries(dxccEntities).filter(([k]) => !workedDxccSet.has(k)).map(([k, v]) => ({ code: k, name: v }));

  async function loadFilters() {
    try {
      const res = await fetch(`/api/settings/${FILTER_KEY}`);
      if (res.ok) {
        const data = await res.json();
        if (data.value) {
          const saved = JSON.parse(data.value);
          filterMode = saved.mode || "";
          filterBand = saved.band || "";
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
        body: JSON.stringify({ value: JSON.stringify({ mode: filterMode, band: filterBand, tab: activeTab }) }),
      });
    } catch {}
  }

  async function fetchAchievements() {
    const params = new URLSearchParams();
    if (filterMode) params.set("mode", filterMode);
    if (filterBand) params.set("band", filterBand);
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
    const _f = { m: filterMode, b: filterBand, t: activeTab };
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
  $: matrixModes = availableModes;
</script>

<div class="achievements">
  <h2>Achievements</h2>

  <div class="controls">
    <div class="tabs">
      <button class="tab" class:active={activeTab === "states"} on:click={() => activeTab = "states"}>States</button>
      <button class="tab" class:active={activeTab === "countries"} on:click={() => activeTab = "countries"}>Countries</button>
      <button class="tab" class:active={activeTab === "grids"} on:click={() => activeTab = "grids"}>Grids</button>
    </div>
    <div class="filters">
      <select bind:value={filterBand}>
        <option value="">All Bands</option>
        {#each availableBands as b}
          <option value={b}>{b}</option>
        {/each}
      </select>
      <select bind:value={filterMode}>
        <option value="">All Modes</option>
        {#each availableModes as m}
          <option value={m}>{m}</option>
        {/each}
      </select>
    </div>
  </div>

  {#if loading}
    <p class="status">Loading...</p>
  {:else if activeTab === "states"}
    <div class="section">
      <div class="progress-row">
        <span class="progress-label">{stateCount} / {totalStates} states ({statePct}%)</span>
        <div class="progress-bar"><div class="progress-fill" style="width: {statePct}%"></div></div>
      </div>

      {#if matrixBands.length > 0 && !filterBand}
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
          <ul>{#each missingStates as st}<li class="missing">{st.name}</li>{/each}</ul>
        </div>
      </div>
    </div>

  {:else if activeTab === "countries"}
    <div class="section">
      <div class="progress-row">
        <span class="progress-label">{workedDxcc.length} / {totalDxcc} DXCC entities ({dxccPct}%)</span>
        <div class="progress-bar"><div class="progress-fill" style="width: {dxccPct}%"></div></div>
      </div>

      {#if matrixBands.length > 0 && !filterBand}
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
    margin-bottom: 0.8rem;
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
    gap: 0.5rem;
    margin-left: auto;
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
    .controls { flex-direction: column; align-items: stretch; }
    .filters { margin-left: 0; }
    .lists { grid-template-columns: 1fr; }
  }
</style>
