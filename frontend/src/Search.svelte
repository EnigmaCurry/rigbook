<script>
  import { onMount, createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  let inputEl;
  let query = "";
  let open = false;

  export function focus() {
    inputEl?.focus();
  }
  let logbookResults = [];
  let potaResults = [];
  let parkResults = [];
  let skccResults = [];
  let qrzResult = null;
  let qrzLoading = false;
  let qrzEnabled = false;
  let potaSpots = [];
  let debounceTimer;
  let qrzDebounceTimer;
  let highlightIndex = -1;

  function looksLikeCallsign(q) {
    if (!q || q.length < 3) return false;
    return /^[A-Za-z0-9]{1,3}[0-9][A-Za-z0-9]{0,4}(\/[A-Za-z0-9]+)?$/.test(q.trim());
  }

  $: allResults = [
    ...logbookResults.map(r => ({ type: "logbook", data: r })),
    ...potaResults.map(r => ({ type: "pota", data: r })),
    ...parkResults.map(r => ({ type: "park", data: r })),
    ...skccResults.map(r => ({ type: "skcc", data: r })),
    ...(qrzResult ? [{ type: "qrz", data: qrzResult }] : []),
  ];

  async function fetchPotaSpots() {
    try {
      const res = await fetch("/api/pota/spots");
      if (res.ok) potaSpots = await res.json();
    } catch {}
  }

  function filterPota(q) {
    if (!q || q.length < 2) return [];
    const ql = q.toLowerCase();
    return potaSpots
      .filter(s =>
        (s.activator || "").toLowerCase().includes(ql) ||
        (s.reference || "").toLowerCase().includes(ql) ||
        (s.name || "").toLowerCase().includes(ql) ||
        (s.locationDesc || "").toLowerCase().includes(ql)
      )
      .slice(0, 5);
  }

  async function searchLogbook(q) {
    if (!q || q.length < 2) { logbookResults = []; return; }
    try {
      const res = await fetch(`/api/search/?q=${encodeURIComponent(q)}`);
      if (res.ok) logbookResults = (await res.json()).slice(0, 5);
      else logbookResults = [];
    } catch { logbookResults = []; }
    maybeSearchQrz(q);
  }

  function maybeSearchQrz(q) {
    clearTimeout(qrzDebounceTimer);
    qrzResult = null;
    if (!qrzEnabled || !looksLikeCallsign(q) || logbookResults.length > 0) return;
    qrzDebounceTimer = setTimeout(() => searchQrz(q), 500);
  }

  async function searchQrz(q) {
    if (!q || q.length < 3) return;
    qrzLoading = true;
    try {
      const res = await fetch(`/api/qrz/lookup/${q.toUpperCase().trim()}`);
      if (res.ok) {
        const data = await res.json();
        qrzResult = data.error ? null : data;
      }
    } catch {}
    qrzLoading = false;
  }

  async function checkQrzEnabled() {
    try {
      const res = await fetch("/api/settings/qrz_password");
      if (res.ok) {
        const data = await res.json();
        qrzEnabled = !!data.value && data.value !== "";
      }
    } catch {}
  }

  async function searchParks(q) {
    if (!q || q.length < 2) { parkResults = []; return; }
    try {
      const res = await fetch(`/api/pota/parks/search?q=${encodeURIComponent(q)}`);
      if (res.ok) parkResults = (await res.json()).slice(0, 5);
      else parkResults = [];
    } catch { parkResults = []; }
  }

  async function searchSkcc(q) {
    if (!q || q.length < 2) { skccResults = []; return; }
    try {
      const res = await fetch(`/api/skcc/search?q=${encodeURIComponent(q)}`);
      if (res.ok) skccResults = await res.json();
      else skccResults = [];
    } catch { skccResults = []; }
  }

  function onInput() {
    open = true;
    highlightIndex = -1;
    qrzResult = null;
    clearTimeout(debounceTimer);
    clearTimeout(qrzDebounceTimer);
    potaResults = filterPota(query);
    debounceTimer = setTimeout(() => { searchLogbook(query); searchParks(query); searchSkcc(query); }, 300);
  }

  function onKeydown(e) {
    if (e.key === "Escape") {
      if (open) {
        open = false;
      } else {
        inputEl?.blur();
      }
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (highlightIndex >= 0 && highlightIndex < allResults.length) {
        pick(allResults[highlightIndex]);
      } else if (query.trim()) {
        open = false;
        dispatch("action", { type: "search", data: { query: query.trim() } });
        query = "";
        logbookResults = [];
        potaResults = [];
        parkResults = [];
        skccResults = [];
      }
      return;
    }
    if (!open || allResults.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      highlightIndex = (highlightIndex + 1) % allResults.length;
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      highlightIndex = highlightIndex <= 0 ? allResults.length - 1 : highlightIndex - 1;
    }
  }

  function pick(item) {
    open = false;
    query = "";
    logbookResults = [];
    potaResults = [];
    parkResults = [];
    skccResults = [];
    qrzResult = null;
    dispatch("action", item);
  }

  function onBlur() {
    setTimeout(() => { open = false; }, 200);
  }

  function onFocus() {
    if (query.length >= 2) open = true;
  }

  function formatFreq(f) {
    if (!f) return "";
    const n = parseFloat(f);
    if (isNaN(n)) return f;
    return parseFloat(n.toFixed(1)).toString();
  }

  function formatTs(ts) {
    if (!ts) return "";
    try {
      return new Date(ts).toISOString().replace("T", " ").substring(0, 16);
    } catch { return ts; }
  }

  onMount(() => {
    fetchPotaSpots();
    checkQrzEnabled();
    const interval = setInterval(fetchPotaSpots, 60000);
    return () => clearInterval(interval);
  });
</script>

<div class="search-wrap">
  <input
    bind:this={inputEl}
    type="search"
    bind:value={query}
    on:input={onInput}
    on:keydown={onKeydown}
    on:blur={onBlur}
    on:focus={onFocus}
    placeholder="Search..."
    autocomplete="off"
  />
  {#if open && (allResults.length > 0 || qrzLoading || query.length >= 2)}
    <div class="results">
      {#if logbookResults.length > 0}
        <div class="group-header">Logbook</div>
        {#each logbookResults as r, i}
          {@const idx = i}
          <div
            class="result-item"
            class:highlighted={highlightIndex === idx}
            on:mousedown|preventDefault={() => pick({ type: "logbook", data: r })}
          >
            <span class="result-call">{r.call}</span>
            <span class="result-detail">{r.name || ""} {r.mode || ""} {formatTs(r.timestamp)}</span>
          </div>
        {/each}
      {/if}

      {#if potaResults.length > 0}
        <div class="group-header">POTA Spots</div>
        {#each potaResults as s, i}
          {@const idx = logbookResults.length + i}
          <div
            class="result-item"
            class:highlighted={highlightIndex === idx}
            on:mousedown|preventDefault={() => pick({ type: "pota", data: s })}
          >
            <span class="result-call">{s.activator}</span>
            <span class="result-detail">{s.reference} {s.name || ""} {formatFreq(s.frequency)} KHz {s.mode || ""}</span>
          </div>
        {/each}
      {/if}

      {#if parkResults.length > 0}
        <div class="group-header">POTA Parks</div>
        {#each parkResults as p, i}
          {@const idx = logbookResults.length + potaResults.length + i}
          <div
            class="result-item"
            class:highlighted={highlightIndex === idx}
            on:mousedown|preventDefault={() => pick({ type: "park", data: p })}
          >
            <span class="result-call">{p.reference}</span>
            <span class="result-detail">{p.name}{p.location_name ? " — " + p.location_name : ""}{p.grid ? " " + p.grid : ""}</span>
          </div>
        {/each}
      {/if}

      {#if skccResults.length > 0}
        <div class="group-header">SKCC</div>
        {#each skccResults as s, i}
          {@const idx = logbookResults.length + potaResults.length + parkResults.length + i}
          <div
            class="result-item"
            class:highlighted={highlightIndex === idx}
            on:mousedown|preventDefault={() => pick({ type: "skcc", data: s })}
          >
            <span class="result-call">{s.call}</span>
            <span class="result-detail">SKCC #{s.skcc}</span>
          </div>
        {/each}
      {/if}

      {#if qrzResult}
        <div class="group-header">QRZ</div>
        {@const idx = logbookResults.length + potaResults.length + parkResults.length + skccResults.length}
        <a
          class="result-item qrz-link"
          class:highlighted={highlightIndex === idx}
          href="https://www.qrz.com/db/{qrzResult.call}"
          target="_blank"
          rel="noopener noreferrer"
          on:mousedown|preventDefault={() => { window.open(`https://www.qrz.com/db/${qrzResult.call}`, '_blank'); open = false; }}
        >
          <span class="result-call">{qrzResult.call}</span>
          <span class="result-detail">{qrzResult.name || ""} {qrzResult.qth || ""} {qrzResult.state || ""} ↗</span>
        </a>
      {:else if qrzLoading}
        <div class="qrz-hint">Looking up on QRZ...</div>
      {/if}

      {#if query.length >= 2 && allResults.length > 0}
        <div class="qrz-hint">Press Enter to search all fields</div>
      {/if}

      {#if allResults.length === 0 && !qrzLoading && query.length >= 2}
        <div class="qrz-hint">No results</div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .search-wrap {
    position: relative;
    flex: 0 1 250px;
  }

  input {
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 0.3rem 0.5rem;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
    -webkit-appearance: none;
    appearance: none;
  }

  input::-webkit-search-cancel-button,
  input::-webkit-search-decoration {
    display: none;
  }

  input:focus {
    outline: none;
    border-color: var(--accent);
  }

  .results {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    min-width: 350px;
    max-height: 400px;
    overflow-y: auto;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-top: none;
    border-radius: 0 0 6px 6px;
    z-index: 10000;
  }

  .group-header {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-dim);
    padding: 0.4rem 0.6rem 0.2rem;
    font-weight: bold;
  }

  .result-item {
    padding: 0.35rem 0.6rem;
    cursor: pointer;
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
    font-size: 0.8rem;
  }

  .result-item:hover,
  .result-item.highlighted {
    background: var(--accent);
    color: var(--bg);
  }

  .result-call {
    color: var(--accent-callsign);
    font-weight: bold;
    white-space: nowrap;
  }

  .result-item:hover .result-call,
  .result-item.highlighted .result-call {
    color: var(--bg);
  }

  .result-detail {
    color: var(--text-muted);
    font-size: 0.75rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .result-item:hover .result-detail,
  .result-item.highlighted .result-detail {
    color: var(--bg);
  }

  a.qrz-link {
    text-decoration: none;
    color: inherit;
  }

  .qrz-hint {
    padding: 0.4rem 0.6rem;
    color: var(--text-dim);
    font-size: 0.75rem;
    font-style: italic;
  }
</style>
