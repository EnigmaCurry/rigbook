<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";
  import { QrzLookup, formatFreq, locationStr, timeAgo } from "./qrzLookup.js";

  const dispatch = createEventDispatcher();

  export let filterMode = "";
  export let filterBand = "";
  export let filterDistance = 0; // 0 = unlimited

  let spots = [];
  let loading = true;
  let pollInterval;
  const qrz = new QrzLookup(() => { spots = spots; });

  // Track spots with their first-seen time so they persist for at least TTL
  let spotMap = {}; // callsign -> { spot, firstSeen }
  const SPOT_TTL_MS = 10 * 60 * 1000; // 10 minutes

  $: visible = !filterMode || filterMode === "CW";

  async function fetchSkccSpots() {
    if (!visible) { spots = []; spotMap = {}; loading = false; return; }
    try {
      const params = new URLSearchParams();
      params.set("mode", "CW");
      params.set("skcc", "required");
      if (filterDistance > 0) params.set("max_distance", String(filterDistance));
      if (filterBand) params.set("band", filterBand);
      params.set("limit", "50");
      const res = await fetch(`/api/spots/?${params}`);
      if (res.ok) {
        const fresh = await res.json();
        const now = Date.now();

        // Merge: update existing, add new
        const freshKeys = new Set();
        for (const s of fresh) {
          freshKeys.add(s.callsign);
          if (spotMap[s.callsign]) {
            spotMap[s.callsign].spot = s;
          } else {
            spotMap[s.callsign] = { spot: s, firstSeen: now };
          }
        }

        // Keep old spots that haven't expired yet (even if not in latest results)
        for (const key of Object.keys(spotMap)) {
          if (!freshKeys.has(key) && now - spotMap[key].firstSeen > SPOT_TTL_MS) {
            delete spotMap[key];
          }
        }

        spots = Object.values(spotMap).map(e => e.spot);
        await qrz.enqueue(spots);
      }
    } catch {}
    loading = false;
  }

  // Re-fetch when filters actually change
  let prevFilterMode = filterMode;
  let prevFilterBand = filterBand;
  let prevFilterDistance = filterDistance;
  $: if (filterMode !== prevFilterMode || filterBand !== prevFilterBand || filterDistance !== prevFilterDistance) {
    prevFilterMode = filterMode;
    prevFilterBand = filterBand;
    prevFilterDistance = filterDistance;
    spotMap = {};
    fetchSkccSpots();
  }

  onMount(() => {
    fetchSkccSpots();
    pollInterval = setInterval(fetchSkccSpots, 10000);
  });

  onDestroy(() => {
    clearInterval(pollInterval);
    qrz.destroy();
  });
</script>

{#if visible && spots.length > 0}
  <div class="skcc-skimmer">
    <h2>SKCC Skimmer ({spots.length})</h2>
      <div class="grid">
        {#each spots as spot (spot.callsign)}
          <div class="card">
            <div class="card-header">
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <span class="callsign clickable" on:click={() => dispatch("addqso", spot)} title="Add QSO">{spot.callsign}</span>
              <span class="badge band" style="background: {bandColor(spot.band)}; color: {bandTextColor(spot.band)}">{spot.band}</span>
            </div>
            <div class="card-body">
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <span class="freq clickable" on:click={() => dispatch("tune", spot)} title="Tune radio">{spot.frequency} KHz</span>
              <span class="skcc-nr">SKCC #{spot.skcc}</span>
            </div>
            <div class="card-body">
              <span class="location">{locationStr(spot)}</span>
            </div>
            <div class="card-footer">
              <span class="distance">{spot.distance_mi != null ? `${spot.distance_mi}mi` : ""}{spot.closest_snr != null ? ` ${spot.closest_snr}dB` : ""}</span>
              <span class="time">{timeAgo(spot.received_at)}</span>
            </div>
          </div>
        {/each}
      </div>
  </div>
{/if}

<style>
  .skcc-skimmer {
    width: 100%;
    margin-top: 1.5rem;
    margin-bottom: 1.5rem;
  }

  h2 {
    color: var(--accent);
    font-size: 1.1rem;
    margin: 0 0 0.75rem 0;
  }

  .status {
    color: var(--text-muted);
    font-size: 0.85rem;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 0.5rem;
  }

  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.5rem 0.65rem;
    font-size: 0.8rem;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.3rem;
  }

  .callsign {
    font-weight: bold;
    color: var(--accent);
    font-size: 0.9rem;
  }

  .badge.band {
    padding: 0.1rem 0.4rem;
    border-radius: 2px;
    font-size: 0.7rem;
    font-weight: bold;
    margin-left: auto;
  }

  .card-body {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.2rem;
  }

  .freq {
    font-weight: bold;
    color: var(--accent-vfo, var(--accent));
    font-variant-numeric: tabular-nums;
  }

  .skcc-nr {
    color: var(--text-muted);
    font-size: 0.75rem;
  }

  .location {
    color: var(--text-muted);
    font-size: 0.75rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .clickable {
    cursor: pointer;
  }
  .clickable:hover {
    text-decoration: underline;
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: var(--text-dim);
    font-size: 0.7rem;
    margin-top: 0.2rem;
  }
</style>
