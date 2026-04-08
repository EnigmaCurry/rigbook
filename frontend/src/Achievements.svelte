<script>
  import { onMount, createEventDispatcher } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";

  const dispatch = createEventDispatcher();

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

  // QSO detail modal
  let modalQsos = [];
  let modalTitle = "";
  let modalOpen = false;
  let modalLoading = false;

  async function openCellModal(label, params) {
    modalTitle = label;
    modalOpen = true;
    modalLoading = true;
    modalQsos = [];
    const sp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== null && v !== undefined && v !== "") sp.set(k, v);
    }
    if (filterMode) sp.set("mode", filterMode);
    if (filterPota) sp.set("pota", "true");
    if (filterSkcc) sp.set("skcc", "true");
    try {
      const res = await fetch(`/api/achievements/qsos?${sp}`);
      if (res.ok) modalQsos = await res.json();
    } catch {}
    modalLoading = false;
  }

  function closeModal() {
    modalOpen = false;
    modalQsos = [];
  }

  function goToQso(id) {
    closeModal();
    dispatch("editcontact", id);
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
    if (filterBands.size > 0) {
      params.set("band", [...filterBands].join(","));
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
            {#each usStates as st}
              {@const stKey = matrix.state_band[st.short] ? st.short : st.name}
              {@const row = matrix.state_band[stKey] || {}}
              {@const hasAny = Object.keys(row).length > 0}
              <tr class:unworked={!hasAny}>
                <td>{st.name} ({st.short})</td>
                {#each matrixBands as b}
                  {@const count = row[b] || 0}
                  <!-- svelte-ignore a11y-click-events-have-key-events -->
                  <!-- svelte-ignore a11y-no-static-element-interactions -->
                  <td class="matrix-cell" class:worked={count > 0} class:clickable={count > 0} on:click={() => { if (count > 0) openCellModal(`${st.name} - ${b}`, { state: stKey, band: b }); }}>{count || ""}</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

  {:else if activeTab === "countries"}
    <div class="section">
      <div class="progress-row">
        <span class="progress-label">{workedDxcc.length} / {totalDxcc} DXCC entities ({dxccPct}%)</span>
        <div class="progress-bar"><div class="progress-fill" style="width: {dxccPct}%"></div></div>
      </div>

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
              {@const row = matrix.dxcc_band[String(code)] || {}}
              <tr>
                <td>{dxccEntities[String(code)] || code}</td>
                {#each matrixBands as b}
                  {@const count = row[b] || 0}
                  <!-- svelte-ignore a11y-click-events-have-key-events -->
                  <!-- svelte-ignore a11y-no-static-element-interactions -->
                  <td class="matrix-cell" class:worked={count > 0} class:clickable={count > 0} on:click={() => { if (count > 0) openCellModal(`${dxccEntities[String(code)] || code} - ${b}`, { dxcc: code, band: b }); }}>{count || ""}</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
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

{#if modalOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="modal-backdrop" on:click={closeModal}>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="modal-content" on:click|stopPropagation>
      <button class="modal-close" on:click={closeModal}>X</button>
      <h3>{modalTitle}</h3>
      {#if modalLoading}
        <p class="status">Loading...</p>
      {:else if modalQsos.length === 0}
        <p class="status">No QSOs found.</p>
      {:else}
        <div class="modal-table-wrap">
          <table class="qso-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Call</th>
                <th>Freq</th>
                <th>Mode</th>
                <th>RST S</th>
                <th>RST R</th>
                <th>Name</th>
                <th>State</th>
                <th>Country</th>
                <th>Grid</th>
                <th>POTA</th>
              </tr>
            </thead>
            <tbody>
              {#each modalQsos as q}
                <tr>
                  <td class="nowrap">{q.timestamp}</td>
                  <!-- svelte-ignore a11y-click-events-have-key-events -->
                  <!-- svelte-ignore a11y-no-static-element-interactions -->
                  <td class="call clickable" on:click={() => goToQso(q.id)}>{q.call}</td>
                  <td>{q.freq || ""}</td>
                  <td>{q.mode || ""}</td>
                  <td>{q.rst_sent || ""}</td>
                  <td>{q.rst_recv || ""}</td>
                  <td>{q.name || ""}</td>
                  <td>{q.state || ""}</td>
                  <td>{q.country || ""}</td>
                  <td>{q.grid || ""}</td>
                  <td>{q.pota_park || ""}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .achievements {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0.5rem 1rem 0;
    overflow: hidden;
    width: 100%;
    box-sizing: border-box;
  }
  h2 { margin: 0 0 0.5rem; flex-shrink: 0; }
  h3 { margin: 0.8rem 0 0.4rem; font-size: 0.95rem; flex-shrink: 0; }

  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.5rem;
    flex-shrink: 0;
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
    margin-bottom: 0.5rem;
    flex-shrink: 0;
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

  .section {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .progress-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
    flex-shrink: 0;
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

  .matrix-wrap {
    overflow: auto;
    flex: 1;
    min-height: 0;
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
    z-index: 2;
  }
  .matrix th:first-child {
    position: sticky;
    left: 0;
    z-index: 3;
    background: var(--bg-card);
  }
  .matrix td:first-child {
    text-align: left;
    font-weight: 500;
    position: sticky;
    left: 0;
    z-index: 1;
    background: var(--bg-card);
  }
  tr.unworked {
    opacity: 0.4;
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

  .clickable {
    cursor: pointer;
  }
  .matrix-cell.clickable:hover {
    filter: brightness(1.3);
  }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .modal-content {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    width: 90vw;
    height: 80vh;
    display: flex;
    flex-direction: column;
    position: relative;
  }
  .modal-content h3 {
    margin: 0 0 0.5rem;
    flex-shrink: 0;
  }
  .modal-close {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    background: none;
    border: none;
    color: var(--text);
    font-size: 1rem;
    cursor: pointer;
  }
  .modal-table-wrap {
    overflow: auto;
    flex: 1;
    min-height: 0;
  }
  .qso-table {
    border-collapse: collapse;
    font-size: 0.8rem;
    width: 100%;
  }
  .qso-table th, .qso-table td {
    border: 1px solid var(--border-input);
    padding: 0.2rem 0.4rem;
    white-space: nowrap;
  }
  .qso-table th {
    background: var(--bg-input);
    font-weight: bold;
    position: sticky;
    top: 0;
  }
  .qso-table .call {
    font-weight: bold;
    color: var(--accent);
  }
  .qso-table .call:hover {
    text-decoration: underline;
  }
  .nowrap { white-space: nowrap; }
</style>
