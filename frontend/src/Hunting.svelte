<script>
  import { onMount, onDestroy } from "svelte";
  import { createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  let spots = [];
  let loading = true;
  let error = "";
  let pollInterval;
  let filterMode = "";
  let filterBand = "";

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

  function formatFreq(f) {
    if (!f) return "";
    const n = parseFloat(f);
    if (isNaN(n)) return f;
    return parseFloat(n.toFixed(1)).toString();
  }

  function timeAgo(spotTime) {
    if (!spotTime) return "";
    const now = new Date();
    const then = new Date(spotTime + "Z");
    const mins = Math.floor((now - then) / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    return `${Math.floor(mins / 60)}h ${mins % 60}m ago`;
  }

  $: modes = [...new Set(spots.map(s => s.mode).filter(Boolean))].sort();
  $: bands = [...new Set(spots.map(s => freqToBand(s.frequency)).filter(Boolean))].sort((a, b) => {
    const order = Object.keys(BANDS);
    return order.indexOf(a) - order.indexOf(b);
  });

  $: filteredSpots = spots.filter(s => {
    if (filterMode && s.mode !== filterMode) return false;
    if (filterBand && freqToBand(s.frequency) !== filterBand) return false;
    return true;
  });

  async function fetchSpots() {
    try {
      const res = await fetch("/api/pota/spots");
      if (res.ok) {
        spots = await res.json();
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
    dispatch("tune", { freq: spot.frequency, mode: spot.mode });
  }

  onMount(() => {
    fetchSpots();
    pollInterval = setInterval(fetchSpots, 30000);
  });

  onDestroy(() => {
    if (pollInterval) clearInterval(pollInterval);
  });
</script>

<div class="hunting">
  <div class="controls">
    <h2>POTA Spots ({filteredSpots.length})</h2>
    <div class="filters">
      <select bind:value={filterMode}>
        <option value="">All Modes</option>
        {#each modes as m}
          <option value={m}>{m}</option>
        {/each}
      </select>
      <select bind:value={filterBand}>
        <option value="">All Bands</option>
        {#each bands as b}
          <option value={b}>{b}</option>
        {/each}
      </select>
      <button class="btn-refresh" on:click={() => { loading = true; fetchSpots(); }}>Refresh</button>
    </div>
  </div>

  {#if loading}
    <p class="status">Loading spots...</p>
  {:else if error}
    <p class="status error">{error}</p>
  {:else if filteredSpots.length === 0}
    <p class="status">No spots found.</p>
  {:else}
    <div class="grid">
      {#each filteredSpots as spot}
        <div class="card" on:click={() => tuneToSpot(spot)} on:keydown={e => e.key === "Enter" && tuneToSpot(spot)} tabindex="0" role="button">
          <div class="card-header">
            <span class="activator">{spot.activator}</span>
            <span class="badge mode">{spot.mode || "?"}</span>
            <span class="badge band">{freqToBand(spot.frequency) || "?"}</span>
          </div>
          <div class="park-name">{spot.name || spot.reference}</div>
          <div class="park-ref">{spot.reference} — {spot.locationDesc}</div>
          <div class="card-details">
            <span class="freq">{formatFreq(spot.frequency)} KHz</span>
            <span class="grid">{spot.grid4 || ""}</span>
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
</div>

<style>
  .hunting {
    width: 100%;
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
    color: #00ff88;
    font-size: 1.2rem;
    margin: 0;
  }

  .filters {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  select {
    background: #5a5c6a;
    border: 1px solid #6e7080;
    color: #f0f0f0;
    padding: 0.3rem 0.5rem;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 3px;
  }

  select:focus {
    outline: none;
    border-color: #00ff88;
  }

  .btn-refresh {
    background: #6e7080;
    color: #eaeaea;
    border: none;
    padding: 0.3rem 0.75rem;
    font-family: inherit;
    font-size: 0.8rem;
    font-weight: bold;
    border-radius: 3px;
    cursor: pointer;
  }

  .btn-refresh:hover {
    background: #5a5c6a;
  }

  .status {
    color: #b0b2be;
    font-style: italic;
  }

  .status.error {
    color: #ff6b6b;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 0.75rem;
  }

  .card {
    background: #4a4c5a;
    border: 1px solid #5a5c6a;
    border-radius: 6px;
    padding: 0.75rem;
    cursor: pointer;
    transition: border-color 0.15s;
  }

  .card:hover {
    border-color: #00ff88;
  }

  .card:focus {
    outline: none;
    border-color: #00ff88;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 0.4rem;
  }

  .activator {
    color: #ffcc00;
    font-weight: bold;
    font-size: 1rem;
  }

  .badge {
    font-size: 0.7rem;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    font-weight: bold;
  }

  .badge.mode {
    background: #00ccff;
    color: #1a1a2e;
  }

  .badge.band {
    background: #a6e3a1;
    color: #1a1a2e;
  }

  .park-name {
    color: #eaeaea;
    font-size: 0.85rem;
    font-weight: bold;
    margin-bottom: 0.15rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .park-ref {
    color: #b0b2be;
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
    color: #00ccff;
    font-weight: bold;
  }

  .grid {
    color: #b0b2be;
  }

  .time {
    color: #b0b2be;
    margin-left: auto;
  }

  .comments {
    color: #8a8c98;
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
    color: #6e7080;
  }

  .count {
    color: #a6e3a1;
  }
</style>
