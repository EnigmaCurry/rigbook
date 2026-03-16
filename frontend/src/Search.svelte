<script>
  import { onMount, createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  let query = "";
  let open = false;
  let logbookResults = [];
  let potaResults = [];
  let qrzResult = null;
  let qrzLoading = false;
  let potaSpots = [];
  let debounceTimer;
  let highlightIndex = -1;

  $: allResults = [
    ...logbookResults.map(r => ({ type: "logbook", data: r })),
    ...potaResults.map(r => ({ type: "pota", data: r })),
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
  }

  async function searchQrz() {
    if (!query || query.length < 3) return;
    qrzLoading = true;
    try {
      const res = await fetch(`/api/qrz/lookup/${query.toUpperCase()}`);
      if (res.ok) {
        const data = await res.json();
        qrzResult = data.error ? null : data;
      }
    } catch {}
    qrzLoading = false;
  }

  function onInput() {
    open = true;
    highlightIndex = -1;
    qrzResult = null;
    clearTimeout(debounceTimer);
    potaResults = filterPota(query);
    debounceTimer = setTimeout(() => searchLogbook(query), 300);
  }

  function onKeydown(e) {
    if (e.key === "Escape") {
      open = false;
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (highlightIndex >= 0 && highlightIndex < allResults.length) {
        pick(allResults[highlightIndex]);
      } else {
        searchQrz();
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
    const interval = setInterval(fetchPotaSpots, 60000);
    return () => clearInterval(interval);
  });
</script>

<div class="search-wrap">
  <input
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

      {#if qrzResult}
        <div class="group-header">QRZ</div>
        {@const idx = logbookResults.length + potaResults.length}
        <div
          class="result-item"
          class:highlighted={highlightIndex === idx}
          on:mousedown|preventDefault={() => pick({ type: "qrz", data: qrzResult })}
        >
          <span class="result-call">{qrzResult.call}</span>
          <span class="result-detail">{qrzResult.name || ""} {qrzResult.qth || ""} {qrzResult.state || ""}</span>
        </div>
      {:else if query.length >= 3 && !qrzLoading}
        <div class="qrz-hint">Press Enter to look up on QRZ</div>
      {/if}

      {#if qrzLoading}
        <div class="qrz-hint">Looking up on QRZ...</div>
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
    z-index: 200;
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

  .qrz-hint {
    padding: 0.4rem 0.6rem;
    color: var(--text-dim);
    font-size: 0.75rem;
    font-style: italic;
  }
</style>
