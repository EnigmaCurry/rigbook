<script>
  import { onMount, onDestroy } from "svelte";
  import { bandColor } from "./bandColors.js";

  let spots = [];
  let status = { rbn: { connected: false, enabled: false }, hamalert: { connected: false, enabled: false }, callsigns: 0, entries: 0, total_spots: 0, avg_spots_per_callsign: 0 };
  let bands = {};
  let modes = [];
  let filterSource = "";
  let filterBand = "";
  let filterMode = "";
  let filterCallsign = "";
  let restarting = false;

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

  async function fetchSpots() {
    try {
      const params = new URLSearchParams();
      if (filterSource) params.set("source", filterSource);
      if (filterBand) params.set("band", filterBand);
      if (filterMode) params.set("mode", filterMode);
      if (filterCallsign) params.set("callsign", filterCallsign);
      params.set("limit", "200");
      const res = await fetch(`/api/spots/?${params}`);
      if (res.ok) spots = await res.json();
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

  function formatFreq(khz) {
    if (!khz) return "";
    return (khz / 1000).toFixed(3);
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

  onMount(() => {
    fetchStatus();
    fetchBands();
    fetchModes();
    fetchSpots();
    statusInterval = setInterval(() => { fetchStatus(); fetchBands(); fetchModes(); }, 5000);
    spotsInterval = setInterval(fetchSpots, 3000);
  });

  onDestroy(() => {
    clearInterval(statusInterval);
    clearInterval(spotsInterval);
  });

  $: bandList = Object.keys(bands).sort((a, b) => {
    const numA = parseInt(a);
    const numB = parseInt(b);
    return numB - numA;
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
    <select bind:value={filterSource} on:change={fetchSpots}>
      <option value="">All Sources</option>
      <option value="rbn">RBN</option>
      <option value="hamalert">HamAlert</option>
    </select>
    <select bind:value={filterBand} on:change={fetchSpots}>
      <option value="">All Bands</option>
      {#each bandList as b}
        <option value={b}>{b} ({bands[b]})</option>
      {/each}
    </select>
    <select bind:value={filterMode} on:change={fetchSpots}>
      <option value="">All Modes</option>
      {#each modes as m}
        <option value={m}>{m}</option>
      {/each}
    </select>
    <input type="text" placeholder="Callsign" bind:value={filterCallsign} on:input={fetchSpots} style="text-transform: uppercase" />
  </div>

  {#if bandList.length > 0}
    <div class="band-badges">
      {#each bandList as b}
        <span
          class="band-badge"
          class:active={filterBand === b}
          style="background: {bandColor(b)}; opacity: {filterBand && filterBand !== b ? 0.3 : 1}"
          on:click={() => { filterBand = filterBand === b ? "" : b; fetchSpots(); }}
          on:keydown={(e) => { if (e.key === 'Enter') { filterBand = filterBand === b ? "" : b; fetchSpots(); } }}
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
          <th>Time</th>
          <th>Callsign</th>
          <th>Freq (MHz)</th>
          <th>Band</th>
          <th>Mode</th>
          <th>Spotters</th>
          <th>SNR</th>
          <th>WPM</th>
          <th>Source</th>
          <th>Info</th>
        </tr>
      </thead>
      <tbody>
        {#each spots as spot (spot.callsign + spot.frequency + spot.mode)}
          <tr>
            <td class="mono">{formatTime(spot)}</td>
            <td class="mono call">{spot.callsign}</td>
            <td class="mono">{formatFreq(spot.frequency)}</td>
            <td><span class="band-tag" style="background: {bandColor(spot.band)}">{spot.band}</span></td>
            <td>{spot.mode}</td>
            <td class="mono" title={spot.spotters ? spot.spotters.join(", ") : ""}>{spot.spotter_count}</td>
            <td class="mono">{spot.best_snr ?? ""}</td>
            <td class="mono">{spot.wpm ?? ""}</td>
            <td class="source-tag {spot.source}">{spot.source}</td>
            <td class="info">{spot.state}{spot.wwff_ref ? ` ${spot.wwff_ref}` : ""}{spot.comment ? ` ${spot.comment}` : ""}</td>
          </tr>
        {/each}
        {#if spots.length === 0}
          <tr><td colspan="10" class="empty">No spots{filterSource || filterBand || filterMode || filterCallsign ? " matching filters" : ""}. {status.rbn.enabled || status.hamalert.enabled ? "Waiting for data..." : "Enable RBN or HamAlert in Settings."}</td></tr>
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
    color: #fff;
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
    color: var(--accent);
  }

  .band-tag {
    padding: 0.1rem 0.4rem;
    border-radius: 2px;
    color: #fff;
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
