<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";
  import { QrzLookup, locationStr, timeAgo } from "./qrzLookup.js";
  import Icon from "@iconify/svelte";
  import iconTree from "@iconify-icons/twemoji/evergreen-tree";

  const dispatch = createEventDispatcher();

  export let filterMode = "";
  export let filterBands = new Set();
  export let workedTodayKeys = new Set();
  export let potaEnabled = true;
  export let paused = false;

  let spots = [];
  let loading = true;
  let pollInterval;
  let seenCalls = new Set();
  let newCalls = new Set();
  const qrz = new QrzLookup(() => { spots = spots; });
  let potaKeys = new Set();
  let potaByKey = {};

  const BAND_RANGES = {
    "160m": [1800, 2000], "80m": [3500, 4000], "60m": [5330, 5410],
    "40m": [7000, 7300], "30m": [10100, 10150], "20m": [14000, 14350],
    "17m": [18068, 18168], "15m": [21000, 21450], "12m": [24890, 24990],
    "10m": [28000, 29700], "6m": [50000, 54000], "2m": [144000, 148000],
  };

  function freqToBand(freqKhz) {
    const f = parseFloat(freqKhz);
    if (isNaN(f)) return "";
    for (const [band, [lo, hi]] of Object.entries(BAND_RANGES)) {
      if (f >= lo && f <= hi) return band;
    }
    return "";
  }

  async function fetchPotaSpots() {
    if (!potaEnabled) { potaKeys = new Set(); potaByKey = {}; return; }
    try {
      const res = await fetch("/api/pota/spots");
      if (res.ok) {
        const pota = await res.json();
        const keys = new Set();
        const byKey = {};
        for (const s of pota) {
          const call = (s.activator || "").toUpperCase();
          const band = freqToBand(parseFloat(s.frequency));
          if (call && band) {
            const key = `${call}|${band}`;
            keys.add(key);
            byKey[key] = s;
          }
        }
        potaKeys = keys;
        potaByKey = byKey;
      }
    } catch {}
  }

  function isPotaActivator(spot) {
    const call = (spot.callsign || "").toUpperCase();
    return potaKeys.has(`${call}|${spot.band}`);
  }

  function addQsoWithPota(spot) {
    const call = (spot.callsign || "").toUpperCase();
    const pota = potaByKey[`${call}|${spot.band}`];
    if (pota) {
      dispatch("addqso", {
        activator: String(spot.callsign || ""),
        frequency: String(spot.frequency || ""),
        mode: String(spot.mode || "CW"),
        reference: String(pota.reference || ""),
        grid4: String(pota.grid4 || ""),
        locationDesc: String(pota.locationDesc || ""),
        skcc: String(spot.skcc || ""),
      });
    } else {
      dispatch("addqso", spot);
    }
  }

  $: visible = !filterMode || filterMode === "CW";

  // Force spots re-render when workedTodayKeys changes
  $: if (workedTodayKeys) { spots = [...spots]; }

  function isWorked(spot) {
    const key = `${spot.callsign.toUpperCase()}|${spot.band}|CW`;
    return workedTodayKeys.has(key);
  }

  async function fetchSkccSpots() {
    if (!visible) { spots = []; loading = false; return; }
    try {
      const params = new URLSearchParams();
      if (filterBands.size > 0) params.set("band", [...filterBands].join(","));
      const res = await fetch(`/api/spots/skcc?${params}`);
      if (res.ok) {
        const fresh = await res.json();
        if (seenCalls.size > 0) {
          const justNew = new Set();
          for (const s of fresh) {
            if (!seenCalls.has(s.callsign)) justNew.add(s.callsign);
          }
          newCalls = justNew;
          if (justNew.size > 0) {
            setTimeout(() => { newCalls = new Set(); }, 15000);
          }
        }
        for (const s of fresh) seenCalls.add(s.callsign);
        spots = fresh;
        await qrz.enqueue(spots);
      }
    } catch {}
    loading = false;
  }

  // Re-fetch when filters actually change
  let prevFilterMode = filterMode;
  let prevFilterBandsKey = [...filterBands].sort().join(",");
  $: {
    const bandsKey = [...filterBands].sort().join(",");
    if (filterMode !== prevFilterMode || bandsKey !== prevFilterBandsKey) {
      prevFilterMode = filterMode;
      prevFilterBandsKey = bandsKey;
      fetchSkccSpots();
    }
  }

  onMount(() => {
    fetchSkccSpots();
    fetchPotaSpots();
    pollInterval = setInterval(() => { if (!paused) { fetchSkccSpots(); fetchPotaSpots(); } }, 10000);
  });

  onDestroy(() => {
    clearInterval(pollInterval);
    qrz.destroy();
  });
</script>

{#if visible && spots.length > 0}
  <div class="skcc-skimmer">
    <h2>SKCC Skimmer ({spots.length}){#if paused} - Paused{/if}</h2>
      <div class="grid">
        {#each spots as spot (spot.callsign)}
          <div class="card" class:new-spot={newCalls.has(spot.callsign)} class:worked={isWorked(spot)}>
            <div class="card-header">
              {#if isWorked(spot)}
                <span class="callsign worked-call" title="Already worked today">{spot.callsign}{#if isPotaActivator(spot)} <Icon icon={iconTree} width={14} inline={true} />{/if}</span>
              {:else}
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <span class="callsign clickable" on:click={() => addQsoWithPota(spot)} title="Add QSO">{spot.callsign}{#if isPotaActivator(spot)} <Icon icon={iconTree} width={14} inline={true} />{/if}</span>
              {/if}
              <span class="skcc-nr">#{spot.skcc}</span>
              <span class="badge band" style="background: {bandColor(spot.band)}; color: {bandTextColor(spot.band)}">{spot.band}</span>
            </div>
            <div class="card-body">
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <span class="freq clickable" on:click={() => dispatch("tune", spot)} title="Tune radio">{spot.frequency} KHz</span>
            </div>
            <div class="card-body">
              <span class="location">{locationStr(spot) || ((spot._qrz_status || spot.qrz_status) === "not_found" ? "(No QRZ record)" : (spot._qrz_status || spot.qrz_status) === "no_location" ? "(No QRZ location)" : "")}</span>
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

  .card.new-spot {
    animation: flash 1.5s ease-in-out 5;
    border-color: var(--accent);
  }

  @keyframes flash {
    0%, 100% { background: var(--bg-card); }
    50% { background: var(--row-editing); }
  }

  .card.worked {
    opacity: 0.5;
  }

  .worked-call {
    color: var(--text-dim);
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
