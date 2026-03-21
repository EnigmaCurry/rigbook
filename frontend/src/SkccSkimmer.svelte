<script>
  import { onMount, onDestroy } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";
  import { countryFlag } from "./countryFlag.js";

  export let filterMode = "";
  export let filterBand = "";

  let spots = [];
  let loading = true;
  let pollInterval;

  // QRZ lookup state (same pattern as Spots page)
  let qrzQueue = [];
  let qrzLookedUp = new Set();
  let qrzDripTimer = null;
  let qrzBurstUsed = 0;
  let qrzPending = 0;

  $: visible = !filterMode || filterMode === "CW";

  async function qrzLookupOne(call) {
    try {
      const qres = await fetch(`/api/qrz/lookup/${call}`);
      if (qres.ok) {
        const data = await qres.json();
        for (const s of spots) {
          if (s.callsign === call && data.country) {
            s.country = data.country || "";
            s.qrz_state = data.state || "";
          }
        }
      }
    } catch {}
  }

  async function fetchSkccSpots() {
    if (!visible) { spots = []; loading = false; return; }
    try {
      const params = new URLSearchParams();
      params.set("mode", "CW");
      params.set("skcc", "required");
      params.set("max_distance", "500");
      if (filterBand) params.set("band", filterBand);
      params.set("limit", "50");
      const res = await fetch(`/api/spots/?${params}`);
      if (res.ok) {
        spots = await res.json();

        // QRZ lookups for missing locations
        if (qrzDripTimer) { clearInterval(qrzDripTimer); qrzDripTimer = null; }
        const allMissing = [...new Set(
          spots.filter(s => !s.country).map(s => s.callsign)
        )];

        if (allMissing.length < 100) {
          const newCalls = allMissing.filter(c => !qrzLookedUp.has(c));
          for (const c of newCalls) qrzLookedUp.add(c);

          const burstAvail = Math.max(0, 20 - qrzBurstUsed);
          const burstCalls = newCalls.slice(0, burstAvail);
          const dripCalls = newCalls.slice(burstAvail);
          qrzBurstUsed += burstCalls.length;

          if (burstCalls.length > 0) {
            await Promise.all(burstCalls.map(call => qrzLookupOne(call)));
            spots = spots;
          }

          const visibleCalls = new Set(spots.map(s => s.callsign));
          qrzQueue = [
            ...dripCalls,
            ...qrzQueue.filter(c => visibleCalls.has(c) && !qrzLookedUp.has(c))
          ];
          qrzPending = qrzQueue.length;

          if (qrzQueue.length > 0 && !qrzDripTimer) {
            qrzDripTimer = setInterval(async () => {
              if (qrzQueue.length === 0) {
                clearInterval(qrzDripTimer);
                qrzDripTimer = null;
                qrzPending = 0;
                return;
              }
              const call = qrzQueue.shift();
              qrzPending = qrzQueue.length;
              await qrzLookupOne(call);
              spots = spots;
            }, 1000);
          }
        }
      }
    } catch {}
    loading = false;
  }

  function formatFreq(khz) {
    if (!khz) return "";
    return (khz / 1000).toFixed(1);
  }

  function locationStr(spot) {
    if (spot.qrz_state && spot.country) return `${spot.qrz_state}, ${spot.country}`;
    return spot.country || spot.qrz_state || "";
  }

  // Re-fetch when filters change
  $: if (typeof filterMode === "string" && typeof filterBand === "string") {
    fetchSkccSpots();
  }

  onMount(() => {
    fetchSkccSpots();
    pollInterval = setInterval(fetchSkccSpots, 10000);
  });

  onDestroy(() => {
    clearInterval(pollInterval);
    if (qrzDripTimer) clearInterval(qrzDripTimer);
  });
</script>

{#if visible}
  <div class="skcc-skimmer">
    <h2>SKCC Skimmer ({spots.length})</h2>
    {#if loading}
      <p class="status">Loading...</p>
    {:else if spots.length === 0}
      <p class="status">No nearby SKCC members on CW{filterBand ? ` (${filterBand})` : ""}.</p>
    {:else}
      <div class="grid">
        {#each spots as spot (spot.callsign)}
          <div class="card">
            <div class="card-header">
              <span class="callsign">{#if spot.country_code}{countryFlag(spot.country_code)} {/if}{spot.callsign}</span>
              <span class="badge band" style="background: {bandColor(spot.band)}; color: {bandTextColor(spot.band)}">{spot.band}</span>
            </div>
            <div class="card-body">
              <span class="freq">{formatFreq(spot.frequency)} KHz</span>
              <span class="skcc-nr">SKCC #{spot.skcc}</span>
            </div>
            <div class="card-body">
              <span class="location">{locationStr(spot)}</span>
            </div>
            <div class="card-footer">
              <span class="distance">{spot.distance_mi != null ? `${spot.distance_mi}mi` : ""}{spot.closest_snr != null ? ` ${spot.closest_snr}dB` : ""}</span>
              <span class="spotters">{spot.spotter_count} spotter{spot.spotter_count !== 1 ? "s" : ""}</span>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .skcc-skimmer {
    width: 100%;
    margin-top: 1.5rem;
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

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: var(--text-dim);
    font-size: 0.7rem;
    margin-top: 0.2rem;
  }
</style>
