<script>
  import { createEventDispatcher } from "svelte";
  export let value = "";

  const dispatch = createEventDispatcher();

  let level = "field"; // "field" or "square"
  let selectedField = "";

  const LETTERS = "ABCDEFGHIJKLMNOPQR".split("");

  // Parse a grid value to determine what's selected
  $: parsedField = value.length >= 2 ? value.substring(0, 2).toUpperCase() : "";
  $: parsedSquare = value.length >= 4 ? value.substring(0, 4).toUpperCase() : "";

  let fieldLonIdx = 0;
  let fieldLatIdx = 0;

  function selectField(lonIdx, latIdx) {
    fieldLonIdx = lonIdx;
    fieldLatIdx = latIdx;
    selectedField = LETTERS[lonIdx] + LETTERS[latIdx];
    level = "square";
  }

  function selectSquare(sqLon, sqLat) {
    const grid = selectedField + sqLon + sqLat;
    value = grid;
    dispatch("select", grid);
    level = "field";
  }

  function backToFields() {
    level = "field";
  }

  // --- OSM tile math for zoomed view ---
  const ZOOM = 5;
  const N = Math.pow(2, ZOOM);

  function lon2tile(lon) { return ((lon + 180) / 360) * N; }
  function lat2tile(lat) {
    // Clamp to avoid infinity at poles
    const clamped = Math.max(-85, Math.min(85, lat));
    const rad = (clamped * Math.PI) / 180;
    return ((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * N;
  }

  // Field bounding box in lon/lat
  $: fieldLon = fieldLonIdx * 20 - 180;
  $: fieldLat = fieldLatIdx * 10 - 90;
  $: fieldLatTop = Math.min(fieldLat + 10, 85);
  $: fieldLatBot = Math.max(fieldLat, -85);

  // Only compute tiles when zoomed in
  $: tileX0 = level === "square" ? Math.floor(lon2tile(fieldLon)) : 0;
  $: tileX1 = level === "square" ? Math.ceil(lon2tile(fieldLon + 20)) : 0;
  $: tileY0 = level === "square" ? Math.floor(lat2tile(fieldLatTop)) : 0;
  $: tileY1 = level === "square" ? Math.ceil(lat2tile(fieldLatBot)) : 0;

  $: pxFieldLeft = lon2tile(fieldLon) - tileX0;
  $: pxFieldRight = lon2tile(fieldLon + 20) - tileX0;
  $: pxFieldTop2 = lat2tile(fieldLatTop) - tileY0;
  $: pxFieldBottom = lat2tile(fieldLatBot) - tileY0;
  $: pxFieldW = (pxFieldRight - pxFieldLeft) * 256;
  $: pxFieldH = (pxFieldBottom - pxFieldTop2) * 256;

  // Build tile list (max 100 tiles safety)
  $: tiles = (() => {
    if (level !== "square") return [];
    const list = [];
    const maxTiles = Math.min(tileY1, tileY0 + 10);
    const maxTilesX = Math.min(tileX1, tileX0 + 10);
    for (let ty = tileY0; ty < maxTiles; ty++) {
      for (let tx = tileX0; tx < maxTilesX; tx++) {
        list.push({
          x: tx,
          y: ty,
          left: (tx - tileX0) * 256 - pxFieldLeft * 256,
          top: (ty - tileY0) * 256 - pxFieldTop2 * 256,
        });
      }
    }
    return list;
  })();

  // Grid square positions using Mercator projection to match OSM tiles
  function sqStyle(lonIdx, latIdx) {
    // lonIdx: 0-9 across, latIdx: 0=top (highest lat) to 9=bottom (lowest lat)
    const sqLatTop = fieldLatTop - latIdx * 1;  // each square is 1° tall
    const sqLatBot = sqLatTop - 1;
    const sqLonLeft = fieldLon + lonIdx * 2;  // each square is 2° wide

    // Convert to Mercator pixel position relative to the field's tile area
    const yTop = lat2tile(sqLatTop) - tileY0;
    const yBot = lat2tile(sqLatBot) - tileY0;
    const xLeft = lon2tile(sqLonLeft) - tileX0;
    const xRight = lon2tile(sqLonLeft + 2) - tileX0;

    // Convert to percentages of the field area
    const totalW = pxFieldRight - pxFieldLeft;
    const totalH = pxFieldBottom - pxFieldTop2;

    const left = ((xLeft - pxFieldLeft) / totalW) * 100;
    const top = ((yTop - pxFieldTop2) / totalH) * 100;
    const width = ((xRight - xLeft) / totalW) * 100;
    const height = ((yBot - yTop) / totalH) * 100;

    return `left:${left}%;top:${top}%;width:${width}%;height:${height}%`;
  }
</script>

<div class="gridmap">
  {#if level === "field"}
    <div class="map-header">
      <span class="map-title">Select Grid Field</span>
      {#if parsedField}
        <span class="current">Current: {value}</span>
      {/if}
    </div>
    <svg viewBox="0 0 100 100" class="map-svg">
      <image
        href="/world-map.jpg"
        x="0" y="0" width="100" height="100"
        preserveAspectRatio="none"
        opacity="0.4"
      />
      {#each LETTERS as lonL, lonIdx}
        {#each LETTERS as latL, latIdx}
          {@const code = LETTERS[lonIdx] + LETTERS[latIdx]}
          {@const x = (lonIdx / 18) * 100}
          {@const y = ((17 - latIdx) / 18) * 100}
          {@const w = 100 / 18}
          {@const h = 100 / 18}
          <rect
            {x} {y} width={w} height={h}
            class="cell"
            class:selected={code === parsedField}
            on:click={() => selectField(lonIdx, latIdx)}
          />
          <text
            x={x + w / 2}
            y={y + h / 2}
            class="cell-label"
            class:selected-text={code === parsedField}
          >{code}</text>
        {/each}
      {/each}
    </svg>
  {:else}
    <div class="map-header">
      <button class="back-btn" on:click={backToFields}>← Back</button>
      <span class="map-title">{selectedField} — Select Square</span>
      {#if parsedSquare}
        <span class="current">Current: {value}</span>
      {/if}
    </div>
    <div class="zoomed-container" style="aspect-ratio: {pxFieldW}/{pxFieldH}">
      <!-- OSM tiles -->
      <div class="tiles-layer">
        {#each tiles as tile}
          <img
            src="/api/tiles/{ZOOM}/{tile.x}/{tile.y}.png"
            alt=""
            class="tile"
            style="left:{tile.left}px;top:{tile.top}px"
          />
        {/each}
      </div>
      <!-- Grid overlay -->
      <div class="grid-overlay">
        {#each Array(10) as _, lonIdx}
          {#each Array(10) as _, latIdx}
            {@const code = selectedField + lonIdx + (9 - latIdx)}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <div
              class="sq-cell"
              class:selected={code === parsedSquare}
              style={sqStyle(lonIdx, latIdx)}
              on:click={() => selectSquare(lonIdx, 9 - latIdx)}
              role="button"
              tabindex="0"
            >
              <span class="sq-label">{lonIdx}{9 - latIdx}</span>
            </div>
          {/each}
        {/each}
      </div>
      <div class="osm-attr">© OpenStreetMap</div>
    </div>
  {/if}
</div>

<style>
  .gridmap {
    width: 100%;
    max-width: 600px;
  }

  .map-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .map-title {
    color: var(--accent);
    font-weight: bold;
    font-size: 0.9rem;
  }

  .current {
    color: var(--text-muted);
    font-size: 0.8rem;
    margin-left: auto;
  }

  .back-btn {
    background: var(--btn-secondary);
    color: var(--text);
    border: none;
    padding: 0.2rem 0.5rem;
    font-family: inherit;
    font-size: 0.75rem;
    border-radius: 3px;
    cursor: pointer;
  }

  .back-btn:hover {
    background: var(--btn-secondary-hover);
  }

  .map-svg {
    width: 100%;
    background: var(--bg-deep);
    border: 1px solid var(--border);
    border-radius: 4px;
  }

  .cell {
    fill: transparent;
    stroke: var(--border);
    stroke-width: 0.1;
    cursor: pointer;
    opacity: 0.8;
  }

  .cell:hover {
    fill: var(--accent);
    opacity: 0.3;
  }

  .cell.selected {
    fill: var(--accent);
    opacity: 0.4;
  }

  .cell-label {
    font-size: 1.8px;
    fill: var(--text-dim);
    text-anchor: middle;
    dominant-baseline: central;
    pointer-events: none;
    font-family: inherit;
  }

  .cell-label.selected-text {
    fill: var(--accent);
    font-weight: bold;
  }

  /* Zoomed view */
  .zoomed-container {
    position: relative;
    width: 100%;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-deep);
  }

  .tiles-layer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0.6;
  }

  .tile {
    position: absolute;
    width: 256px;
    height: 256px;
    image-rendering: auto;
  }

  .grid-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }

  .sq-cell {
    position: absolute;
    border: 1px solid rgba(128, 128, 128, 0.3);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
  }

  .sq-cell:hover {
    background: rgba(0, 255, 136, 0.3);
    border-color: var(--accent);
  }

  .sq-cell.selected {
    background: rgba(0, 255, 136, 0.35);
    border-color: var(--accent);
  }

  .sq-label {
    color: var(--text);
    font-size: 0.7rem;
    font-weight: bold;
    text-shadow: 0 0 3px var(--bg), 0 0 6px var(--bg);
    pointer-events: none;
  }

  .sq-cell.selected .sq-label {
    color: var(--accent);
  }

  .osm-attr {
    position: absolute;
    bottom: 2px;
    right: 4px;
    font-size: 0.55rem;
    color: var(--text-dim);
    opacity: 0.7;
  }
</style>
