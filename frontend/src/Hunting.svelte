<script>
  import { onMount, onDestroy } from "svelte";
  import { createEventDispatcher } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";
  import { parkAward, parkAwardTitle } from "./parkAward.js";
  import ParkDetail from "./ParkDetail.svelte";
  import SkccSkimmer from "./SkccSkimmer.svelte";
  import { timeAgo } from "./qrzLookup.js";

  const dispatch = createEventDispatcher();
  export let potaEnabled = true;
  export let spotsEnabled = false;

  let spots = [];
  let loading = true;
  let error = "";
  let pollInterval;
  let filterMode = "";
  let filterBands = new Set();
  let filterProgram = "";
  let skccSkimmerEnabled = false;
  let filtersLoaded = false;
  let seenSpotKeys = new Set();
  let newSpotKeys = new Set();
  let myParkQsos = {};
  let myCallCounts = {};
  let workedTodayKeys = new Set();
  let workedTodayCwKeys = new Set();

  // Park modal state
  let modalParkRef = null;
  let modalParkDetail = null;
  let modalParkLoading = false;

  const DIGIT_EMOJIS = ["", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"];

  function callCountEmoji(info) {
    const count = info?.count || 0;
    if (count <= 0) return "";
    if (count <= 9) return DIGIT_EMOJIS[count];
    return "💯";
  }

  function timeAgoStr(isoStr) {
    if (!isoStr) return "";
    const lastStr = isoStr.endsWith("Z") ? isoStr : isoStr + "Z";
    const ago = Date.now() - new Date(lastStr).getTime();
    if (ago < 0) return "";
    const mins = Math.floor(ago / 60000);
    const hrs = Math.floor(mins / 60);
    const days = Math.floor(hrs / 24);
    if (days > 0) return `${days} day${days !== 1 ? "s" : ""} ago`;
    if (hrs > 0) return `${hrs} hour${hrs !== 1 ? "s" : ""} ago`;
    if (mins <= 0) return "just now";
    return `${mins} minute${mins !== 1 ? "s" : ""} ago`;
  }

  function callCountTitle(info, call) {
    if (!info) return "";
    const count = info.count;
    let s = `${count} QSO${count !== 1 ? "s" : ""} with ${call}`;
    const ago = timeAgoStr(info.last);
    if (ago) s += `, ${ago}`;
    return s;
  }

  function parkQsoTitle(info, ref) {
    if (!info) return "";
    const count = info.count;
    let s = `${count} QSO${count !== 1 ? "s" : ""} @ ${ref}`;
    const ago = timeAgoStr(info.last);
    if (ago) s += `, ${ago}`;
    return s;
  }

  async function fetchCallCounts() {
    try {
      const res = await fetch("/api/contacts/callsign-counts");
      if (res.ok) myCallCounts = await res.json();
    } catch {}
  }

  async function fetchMyParks() {
    try {
      const res = await fetch("/api/pota/my-parks");
      if (res.ok) {
        const parks = await res.json();
        const map = {};
        for (const p of parks) map[p.reference] = { count: p.qso_count, last: p.last_contact };
        myParkQsos = map;
      }
    } catch {}
  }

  function spotKey(s) {
    return `${s.activator}|${s.reference}`;
  }

  const BANDS = {
    "160m": [1800, 2000],
    "80m": [3500, 4000],
    "60m": [5330, 5410],
    "40m": [7000, 7300],
    "30m": [10100, 10150],
    "20m": [14000, 14350],
    "17m": [18068, 18168],
    "15m": [21000, 21450],
    "12m": [24890, 24990],
    "10m": [28000, 29700],
    "6m": [50000, 54000],
    "2m": [144000, 148000],
  };

  function freqToBand(freqKhz) {
    const f = parseFloat(freqKhz);
    if (isNaN(f)) return "";
    for (const [band, [lo, hi]] of Object.entries(BANDS)) {
      if (f >= lo && f <= hi) return band;
    }
    return "";
  }

  function toggleBand(b) {
    if (filterBands.has(b)) filterBands.delete(b);
    else filterBands.add(b);
    filterBands = new Set(filterBands);
  }

  function formatFreq(f) {
    if (!f) return "";
    const n = parseFloat(f);
    if (isNaN(n)) return f;
    return parseFloat(n.toFixed(1)).toString();
  }


  function spotProgram(spot) {
    const ref = spot.reference || "";
    const i = ref.indexOf("-");
    return i > 0 ? ref.slice(0, i) : ref;
  }

  $: modes = [...new Set([...spots.map(s => s.mode), filterMode].filter(Boolean))].sort();
  $: bands = [...new Set([...spots.map(s => freqToBand(s.frequency)), ...filterBands].filter(Boolean))].sort((a, b) => {
    const order = Object.keys(BANDS);
    return order.indexOf(a) - order.indexOf(b);
  });
  $: programs = [...new Set([...spots.map(s => spotProgram(s)), filterProgram].filter(Boolean))].sort();

  $: filteredSpots = spots.filter(s => {
    if (filterMode && s.mode !== filterMode) return false;
    if (filterBands.size > 0 && !filterBands.has(freqToBand(s.frequency))) return false;
    if (filterProgram && spotProgram(s) !== filterProgram) return false;
    return true;
  });


  const FILTER_SETTINGS_KEY = "pota_spot_filters";

  async function loadFilters() {
    try {
      const res = await fetch(`/api/settings/${FILTER_SETTINGS_KEY}`);
      if (res.ok) {
        const data = await res.json();
        if (data.value) {
          const saved = JSON.parse(data.value);
          filterMode = saved.mode || "";
          filterBands = saved.band ? new Set(saved.band.split(",")) : new Set();
          filterProgram = saved.program || "";
        }
      }
    } catch {}
    try {
      const res = await fetch("/api/settings/skcc_skimmer_enabled");
      if (res.ok) {
        const data = await res.json();
        skccSkimmerEnabled = data.value === "true";
      }
    } catch {}
    filtersLoaded = true;
  }

  async function saveFilters() {
    if (!filtersLoaded) return;
    try {
      await fetch(`/api/settings/${FILTER_SETTINGS_KEY}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: JSON.stringify({ mode: filterMode, band: [...filterBands].join(","), program: filterProgram }) }),
      });
    } catch {}
  }

  // Save filters and refresh spots whenever they change (after initial load)
  $: if (filtersLoaded) {
    const _filters = { m: filterMode, b: [...filterBands].join(","), p: filterProgram };
    saveFilters();
    fetchSpots();
  }

  async function fetchSpots() {
    try {
      const res = await fetch("/api/pota/spots");
      if (res.ok) {
        const fresh = await res.json();
        // Track new spots (skip first load)
        if (seenSpotKeys.size > 0) {
          const justNew = new Set();
          for (const s of fresh) {
            if (!seenSpotKeys.has(spotKey(s))) justNew.add(spotKey(s));
          }
          newSpotKeys = justNew;
          if (justNew.size > 0) {
            setTimeout(() => { newSpotKeys = new Set(); }, 15000);
          }
        }
        for (const s of fresh) seenSpotKeys.add(spotKey(s));
        spots = fresh;
        error = "";
      } else {
        error = `Failed to fetch spots: ${res.status}`;
      }
    } catch (e) {
      error = `Network error: ${e.message}`;
    }
    loading = false;
  }

  function tuneToSpot(spot) {
    dispatch("tune", spot);
  }

  function addQsoFromSpot(spot) {
    dispatch("addqso", spot);
  }

  const MODE_NORMALIZE = {
    "USB": "SSB", "LSB": "SSB",
    "CW-R": "CW", "CWR": "CW",
    "FT8": "FT8", "FT4": "FT4",
    "RTTY": "RTTY", "RTTY-R": "RTTY",
  };

  function normalizeMode(m) {
    const u = (m || "").toUpperCase();
    return MODE_NORMALIZE[u] || u;
  }

  function isWorkedToday(spot) {
    const band = freqToBand(parseFloat(spot.frequency));
    const mode = normalizeMode(spot.mode);
    if (!mode || mode === "?") {
      const prefix = `${(spot.activator || "").toUpperCase()}|${band}|`;
      const suffix = `|${(spot.reference || "").toUpperCase()}`;
      for (const k of workedTodayKeys) {
        if (k.startsWith(prefix) && k.endsWith(suffix)) return true;
      }
      return false;
    }
    const key = `${(spot.activator || "").toUpperCase()}|${band}|${mode}|${(spot.reference || "").toUpperCase()}`;
    return workedTodayKeys.has(key);
  }

  async function fetchTodayPota() {
    try {
      const res = await fetch("/api/contacts/today-pota");
      if (res.ok) {
        const contacts = await res.json();
        const keys = new Set();
        for (const c of contacts) {
          const band = freqToBand(parseFloat(c.freq));
          const key = `${(c.call || "").toUpperCase()}|${band}|${normalizeMode(c.mode)}|${(c.pota_park || "").toUpperCase()}`;
          keys.add(key);
        }
        workedTodayKeys = keys;
      }
    } catch {}
  }

  async function fetchTodayCw() {
    try {
      const res = await fetch("/api/contacts/today-cw");
      if (res.ok) {
        const contacts = await res.json();
        const keys = new Set();
        for (const c of contacts) {
          const band = freqToBand(parseFloat(c.freq));
          const key = `${(c.call || "").toUpperCase()}|${band}|CW`;
          keys.add(key);
        }
        workedTodayCwKeys = keys;
      }
    } catch {}
  }

  async function openParkModal(ref) {
    modalParkRef = ref;
    modalParkDetail = null;
    modalParkLoading = true;
    try {
      const res = await fetch(`/api/pota/park/${encodeURIComponent(ref)}`);
      if (res.ok) {
        const data = await res.json();
        if (!data.error) modalParkDetail = data;
      }
    } catch {}
    modalParkLoading = false;
  }

  function closeParkModal() {
    modalParkRef = null;
    modalParkDetail = null;
    modalParkLoading = false;
  }

  function onModalKeydown(e) {
    if (e.key === "Escape") closeParkModal();
  }

  export function refreshAwards() {
    fetchMyParks();
    fetchCallCounts();
    fetchTodayPota();
    fetchTodayCw();
  }

  onMount(async () => {
    await loadFilters();
    if (potaEnabled) {
      fetchSpots();
      fetchMyParks();
      fetchTodayPota();
    }
    fetchCallCounts();
    fetchTodayCw();
    pollInterval = setInterval(() => { if (potaEnabled) fetchSpots(); }, 30000);
  });

  onDestroy(() => {
    if (pollInterval) clearInterval(pollInterval);
  });
</script>

<div class="hunting">
  {#if filtersLoaded && !potaEnabled && !(skccSkimmerEnabled && spotsEnabled)}
    <h2>Hunting</h2>
    <p class="status">No hunting activities enabled. Enable POTA or SKCC Skimmer in <a href="#/settings">Settings</a>.</p>
  {:else}
  <div class="controls">
    <h2>Hunting</h2>
    <div class="filters">
      {#if bands.length > 0}
        {#each bands as b}
          <!-- svelte-ignore a11y-click-events-have-key-events -->
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <span
            class="band-badge"
            class:active={filterBands.has(b)}
            style="background: {bandColor(b)}; color: {bandTextColor(b)}; opacity: {filterBands.size > 0 && !filterBands.has(b) ? 0.3 : 1}"
            on:click={() => { toggleBand(b); }}
          >
            {b}
          </span>
        {/each}
      {/if}
      {#if filterBands.size > 0}
        <button class="btn-clear-bands" on:click={() => { filterBands = new Set(); }}>Clear bands</button>
      {/if}
      <select bind:value={filterMode}>
        <option value="">All Modes</option>
        {#each modes as m}
          <option value={m}>{m}</option>
        {/each}
      </select>
      <select bind:value={filterProgram}>
        <option value="">All Programs</option>
        {#each programs as p}
          <option value={p}>{p}</option>
        {/each}
      </select>
    </div>
  </div>

  {#if skccSkimmerEnabled && spotsEnabled}
    <SkccSkimmer filterMode={filterMode} filterBands={filterBands} workedTodayKeys={workedTodayCwKeys} {potaEnabled} on:tune on:addqso />
  {/if}

  {#if potaEnabled}
  <h2>POTA Spots ({filteredSpots.length})</h2>

  {#if loading}
    <p class="status">Loading spots...</p>
  {:else if error}
    <p class="status error">{error}</p>
  {:else if filteredSpots.length === 0}
    <p class="status">No spots found.</p>
  {:else}
    <div class="grid">
      {#each filteredSpots as spot}
        <div class="card" class:new-spot={newSpotKeys.has(spotKey(spot))} class:worked={workedTodayKeys && isWorkedToday(spot)}>
          <div class="card-header">
            {#if workedTodayKeys && isWorkedToday(spot)}
              <span class="activator worked-call" title="Already worked today">{spot.activator}</span>
            {:else}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <span class="activator clickable" on:click={() => addQsoFromSpot(spot)} title="Add QSO">{spot.activator}</span>
            {/if}
            <span class="badge mode">{spot.mode || "?"}</span>
            <span class="badge band" style="background: {bandColor(freqToBand(spot.frequency))}; color: {bandTextColor(freqToBand(spot.frequency))}">{freqToBand(spot.frequency) || "?"}</span>
            {#if myCallCounts[spot.activator]}<span class="call-count" title="{callCountTitle(myCallCounts[spot.activator], spot.activator)}">{callCountEmoji(myCallCounts[spot.activator])}</span>{/if}
          </div>
          <!-- svelte-ignore a11y-click-events-have-key-events -->
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <div class="park-name clickable" on:click={() => openParkModal(spot.reference)}>{spot.name || spot.reference}</div>
          <!-- svelte-ignore a11y-click-events-have-key-events -->
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <div class="park-ref" title="{myParkQsos[spot.reference] ? parkQsoTitle(myParkQsos[spot.reference], spot.reference) : ''}">{#if myParkQsos[spot.reference]}{parkAward(myParkQsos[spot.reference].count)}{/if}<span class="clickable" on:click={() => openParkModal(spot.reference)}>{spot.reference}</span> — {spot.locationDesc}</div>
          <div class="card-details">
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <span class="freq clickable" on:click={() => tuneToSpot(spot)} title="Tune radio">{formatFreq(spot.frequency)} KHz</span>
            <span class="grid-sq">{spot.grid4 || ""}</span>
            <span class="time">{timeAgo(spot.spotTime)}</span>
          </div>
          {#if spot.comments}
            <div class="comments">{spot.comments}</div>
          {/if}
          <div class="card-footer">
            <span class="count">{spot.count} QSOs</span>
            <span class="spotter">via {spot.spotter}</span>
          </div>
        </div>
      {/each}
    </div>
  {/if}
  {/if}
  {/if}
</div>

{#if modalParkRef}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="modal-backdrop" on:click={closeParkModal}>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="modal-content" on:click|stopPropagation on:keydown={onModalKeydown}>
      <button class="modal-close" on:click={closeParkModal}>X</button>
      {#if modalParkLoading}
        <p class="status">Loading park details...</p>
      {:else if modalParkDetail}
        <ParkDetail park={modalParkDetail} on:close={closeParkModal} />
      {:else}
        {@const prefix = modalParkRef.match(/^([A-Z]{1,2})-/)?.[1] || ""}
        <p class="status">Park {modalParkRef} not found in cache.</p>
        <p class="cache-link">Go to <a href="#/parks/download">Cache</a> to download park data{prefix ? ` for country code ${prefix}` : ""}.</p>
      {/if}
    </div>
  </div>
{/if}

<svelte:window on:keydown={e => { if (modalParkRef && e.key === "Escape") closeParkModal(); }} />

<style>
  .hunting {
    width: 100%;
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

  .btn-clear-bands {
    background: var(--bg2, #333);
    color: var(--fg, #ccc);
    border: 1px solid var(--border, #555);
    border-radius: 4px;
    padding: 0.2rem 0.5rem;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  h2 {
    color: var(--accent);
    font-size: 1.2rem;
    margin: 0;
  }

  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
    justify-content: flex-end;
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

  select:focus {
    outline: none;
    border-color: var(--accent);
  }


  .status {
    color: var(--text-muted);
    font-style: italic;
  }
  .status a, .status a:visited {
    color: var(--accent);
  }

  .status.error {
    color: var(--accent-error);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 0.75rem;
  }

  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.75rem;
    transition: border-color 0.15s;
  }

  .card.worked {
    opacity: 0.5;
  }

  .card.new-spot {
    animation: flash 1.5s ease-in-out 5;
    border-color: var(--accent);
  }

  @keyframes flash {
    0%, 100% { background: var(--bg-card); }
    50% { background: var(--row-editing); }
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 0.4rem;
  }

  .activator {
    color: var(--accent-callsign);
    font-weight: bold;
    font-size: 1rem;
  }

  .activator.clickable {
    cursor: pointer;
  }

  .activator.clickable:hover {
    text-decoration: underline;
  }


  .clickable {
    cursor: pointer;
  }

  .clickable:hover {
    text-decoration: underline;
  }

  .call-count {
    font-size: 0.85rem;
    margin-left: 0.2rem;
  }

  .badge {
    font-size: 0.7rem;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    font-weight: bold;
  }

  .badge.mode {
    background: #00ccff;
    color: var(--bg);
  }

  .badge.band {
  }

  .park-name {
    color: var(--text);
    font-size: 0.85rem;
    font-weight: bold;
    margin-bottom: 0.15rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .park-ref {
    color: var(--text-muted);
    font-size: 0.75rem;
    margin-bottom: 0.4rem;
  }

  .card-details {
    display: flex;
    gap: 0.75rem;
    font-size: 0.8rem;
    margin-bottom: 0.3rem;
  }

  .freq {
    color: var(--accent-vfo);
    font-weight: bold;
  }

  .grid-sq {
    color: var(--text-muted);
  }

  .time {
    color: var(--text-muted);
    margin-left: auto;
  }

  .comments {
    color: var(--text-dim);
    font-size: 0.75rem;
    font-style: italic;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 0.3rem;
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    font-size: 0.7rem;
    color: var(--text-dimmer);
  }

  .count {
    color: #658a62;
  }

  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .modal-content {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    max-width: 900px;
    width: 95%;
    max-height: 80vh;
    overflow-y: auto;
    position: relative;
  }

  .modal-close {
    position: absolute;
    top: 0.5rem;
    right: 0.75rem;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 1rem;
    font-family: inherit;
    font-weight: bold;
    cursor: pointer;
  }

  .modal-close:hover {
    color: var(--text);
  }

  .cache-link {
    font-size: 0.9rem;
  }

  .cache-link a {
    color: var(--accent);
    text-decoration: none;
  }

  .cache-link a:hover {
    text-decoration: underline;
  }

</style>
