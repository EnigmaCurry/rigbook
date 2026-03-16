<script>
  import { createEventDispatcher } from "svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";

  export let currentFreq = "";
  export let currentMode = "";

  const dispatch = createEventDispatcher();

  // Map radio modes to band plan segment labels
  const MODE_MAP = {
    "CW": "CW", "CW-R": "CW", "CWR": "CW",
    "LSB": "SSB", "USB": "SSB", "SSB": "SSB", "AM": "SSB",
    "FM": "FM",
    "FT8": "Digi", "FT4": "Digi", "RTTY": "Digi", "RTTY-R": "Digi",
    "PSK31": "Digi", "PSK": "Digi", "DIGI": "Digi", "DATA": "Digi",
    "JS8": "Digi", "OLIVIA": "Digi",
  };

  $: freq = parseFloat(currentFreq) || 0;
  $: segLabel = MODE_MAP[currentMode?.toUpperCase()] || "";
  $: activeBandObj = BANDS.find(b => freq >= b.lo && freq <= b.hi);
  $: activeBand = activeBandObj?.name || "";

  // Find the segment matching the current mode within the active band
  $: activeSeg = activeBandObj?.segments.find(s => s.label === segLabel) || null;

  // Use mode segment boundaries for Lo/Mid/Hi, fall back to full band
  function segFor(band) {
    if (!segLabel) return { lo: band.lo, hi: band.hi };
    const seg = band.segments.find(s => s.label === segLabel);
    return seg || { lo: band.lo, hi: band.hi };
  }

  $: activeThird = activeBandObj ? (() => {
    const s = activeSeg || activeBandObj;
    const third = (s.hi - s.lo) / 3;
    if (freq < s.lo + third) return "lo";
    if (freq > s.hi - third) return "hi";
    return "mid";
  })() : "";

  const BANDS = [
    { name: "160m", lo: 1800, hi: 2000, segments: [
      { label: "CW", lo: 1800, hi: 2000 },
      { label: "SSB", lo: 1800, hi: 2000 },
    ]},
    { name: "80m", lo: 3500, hi: 4000, segments: [
      { label: "CW", lo: 3500, hi: 4000 },
      { label: "SSB", lo: 3600, hi: 4000 },
    ]},
    { name: "60m", lo: 5330, hi: 5410, segments: [
      { label: "CW", lo: 5330, hi: 5410 },
      { label: "Digi", lo: 5330, hi: 5410 },
      { label: "USB", lo: 5330, hi: 5410 },
    ]},
    { name: "40m", lo: 7000, hi: 7300, segments: [
      { label: "CW", lo: 7000, hi: 7300 },
      { label: "SSB", lo: 7125, hi: 7300 },
    ]},
    { name: "30m", lo: 10100, hi: 10150, segments: [
      { label: "CW", lo: 10100, hi: 10150 },
      { label: "SSB", lo: 10100, hi: 10150 },
    ]},
    { name: "20m", lo: 14000, hi: 14350, segments: [
      { label: "CW", lo: 14000, hi: 14350 },
      { label: "SSB", lo: 14150, hi: 14350 },
    ]},
    { name: "17m", lo: 18068, hi: 18168, segments: [
      { label: "CW", lo: 18068, hi: 18168 },
      { label: "SSB", lo: 18110, hi: 18168 },
    ]},
    { name: "15m", lo: 21000, hi: 21450, segments: [
      { label: "CW", lo: 21000, hi: 21450 },
      { label: "SSB", lo: 21200, hi: 21450 },
    ]},
    { name: "12m", lo: 24890, hi: 24990, segments: [
      { label: "CW", lo: 24890, hi: 24990 },
      { label: "SSB", lo: 24930, hi: 24990 },
    ]},
    { name: "10m", lo: 28000, hi: 29700, segments: [
      { label: "CW", lo: 28000, hi: 29700 },
      { label: "SSB", lo: 28300, hi: 29700 },
    ]},
    { name: "6m", lo: 50000, hi: 54000, segments: [
      { label: "CW", lo: 50000, hi: 54000 },
      { label: "SSB", lo: 50100, hi: 54000 },
    ]},
    { name: "2m", lo: 144000, hi: 148000, segments: [
      { label: "CW", lo: 144000, hi: 148000 },
      { label: "SSB", lo: 144100, hi: 148000 },
    ]},
  ];

  function tune(f) {
    dispatch("tune", f);
  }

  const EDGE_MARGIN = 1; // KHz default safety margin
  const SSB_BW = 3; // KHz typical SSB bandwidth

  $: upperMode = currentMode?.toUpperCase() || "";

  function loMargin() {
    if (upperMode === "LSB") return SSB_BW;
    return EDGE_MARGIN;
  }

  function hiMargin() {
    if (upperMode === "USB") return SSB_BW;
    return EDGE_MARGIN;
  }

  function mid(lo, hi) {
    return Math.round((lo + hi) / 2);
  }

  let bandplanEl;

  $: if (activeBand && bandplanEl) {
    setTimeout(() => {
      const active = bandplanEl?.querySelector(".band-row.active");
      if (active) active.scrollIntoView({ block: "nearest" });
    }, 0);
  }
</script>

<div class="bandplan" bind:this={bandplanEl}>
  {#each BANDS as band}
    <div class="band-row" class:active={activeBand === band.name}>
      <span class="band-name" style="background: {bandColor(band.name)}; color: {bandTextColor(band.name)}" on:mousedown|preventDefault={() => tune(mid(segFor(band).lo, segFor(band).hi))} title="{mid(segFor(band).lo, segFor(band).hi)} KHz">{band.name}</span>
      <div class="band-buttons">
        <button class="bp-btn" class:bp-active={activeBand === band.name && activeThird === "lo"} on:mousedown|preventDefault={() => tune(segFor(band).lo + loMargin())} title="{segFor(band).lo + loMargin()} KHz">Lo</button>
        <button class="bp-btn" class:bp-active={activeBand === band.name && activeThird === "mid"} on:mousedown|preventDefault={() => tune(mid(segFor(band).lo, segFor(band).hi))} title="{mid(segFor(band).lo, segFor(band).hi)} KHz">Mid</button>
        <button class="bp-btn" class:bp-active={activeBand === band.name && activeThird === "hi"} on:mousedown|preventDefault={() => tune(segFor(band).hi - hiMargin())} title="{segFor(band).hi - hiMargin()} KHz">Hi</button>
      </div>
      <div class="segments">
        {#each band.segments as seg}
          <span class="seg" title="{seg.lo}-{seg.hi} KHz">{seg.label} {seg.lo}-{seg.hi}</span>
        {/each}
      </div>
    </div>
  {/each}
</div>

<style>
  .bandplan {
    position: fixed;
    top: auto;
    left: 1rem;
    right: 1rem;
    max-width: 600px;
    max-height: 80vh;
    overflow-y: auto;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    z-index: 200;
    padding: 0.25rem 0;
  }

  .band-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid var(--border);
  }

  .band-row:last-child {
    border-bottom: none;
  }

  .band-row.active {
    background: var(--row-hover);
    border-left: 3px solid var(--accent);
    padding-left: calc(0.5rem - 3px);
  }

  .band-name {
    font-weight: bold;
    font-size: 0.7rem;
    padding: 0.1rem 0.35rem;
    border-radius: 8px;
    text-align: center;
    min-width: 35px;
    flex-shrink: 0;
    cursor: pointer;
  }

  .band-buttons {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }

  .bp-btn {
    background: var(--btn-secondary);
    color: var(--text);
    border: none;
    padding: 0.15rem 0.35rem;
    font-family: inherit;
    font-size: 0.65rem;
    font-weight: bold;
    border-radius: 2px;
    cursor: pointer;
  }

  .bp-btn:hover,
  .bp-btn.bp-active {
    background: var(--accent);
    color: var(--bg);
  }

  .segments {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
  }

  .seg {
    font-size: 0.6rem;
    color: var(--text-dim);
    white-space: nowrap;
  }
</style>
