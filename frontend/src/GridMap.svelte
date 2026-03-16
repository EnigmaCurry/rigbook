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

  // Convert grid square to center lat/lon
  function gridToLatLon(grid) {
    if (!grid || grid.length < 4) return null;
    const g = grid.toUpperCase();
    const lonField = g.charCodeAt(0) - 65;
    const latField = g.charCodeAt(1) - 65;
    const lonSq = parseInt(g[2]);
    const latSq = parseInt(g[3]);
    let lon = lonField * 20 - 180 + lonSq * 2 + 1;
    let lat = latField * 10 - 90 + latSq * 1 + 0.5;
    if (grid.length >= 6) {
      const lonSub = g.charCodeAt(4) - 65;
      const latSub = g.charCodeAt(5) - 65;
      lon = lonField * 20 - 180 + lonSq * 2 + lonSub * (2/24) + (1/24);
      lat = latField * 10 - 90 + latSq * 1 + latSub * (1/24) + (1/48);
    }
    return { lat, lon };
  }

  function fmtDecimal(coord) {
    if (!coord) return "";
    return `${coord.lat.toFixed(5)}, ${coord.lon.toFixed(5)}`;
  }

  function fmtDMS(coord) {
    if (!coord) return "";
    function toDMS(dd, pos, neg) {
      const dir = dd >= 0 ? pos : neg;
      const abs = Math.abs(dd);
      const d = Math.floor(abs);
      const m = Math.floor((abs - d) * 60);
      const s = ((abs - d - m / 60) * 3600).toFixed(1);
      return `${d}°${String(m).padStart(2, "0")}'${String(s).padStart(4, "0")}"${dir}`;
    }
    return `${toDMS(coord.lat, "N", "S")} ${toDMS(coord.lon, "E", "W")}`;
  }

  function fmtUTM(coord) {
    if (!coord) return "";
    const { lat, lon } = coord;
    if (lat < -80 || lat > 84) return "outside UTM range";
    const zoneNum = Math.floor((lon + 180) / 6) + 1;
    const zoneLetter = "CDEFGHJKLMNPQRSTUVWX"[Math.floor((lat + 80) / 8)];
    const lonRad = (lon * Math.PI) / 180;
    const latRad = (lat * Math.PI) / 180;
    const a = 6378137;
    const f = 1 / 298.257223563;
    const e = Math.sqrt(2 * f - f * f);
    const e2 = e * e / (1 - e * e);
    const n = a / Math.sqrt(1 - e * e * Math.sin(latRad) ** 2);
    const t = Math.tan(latRad) ** 2;
    const c = e2 * Math.cos(latRad) ** 2;
    const A = Math.cos(latRad) * (lonRad - ((zoneNum - 1) * 6 - 180 + 3) * Math.PI / 180);
    const M = a * ((1 - e*e/4 - 3*e**4/64 - 5*e**6/256) * latRad
      - (3*e*e/8 + 3*e**4/32 + 45*e**6/1024) * Math.sin(2*latRad)
      + (15*e**4/256 + 45*e**6/1024) * Math.sin(4*latRad)
      - (35*e**6/3072) * Math.sin(6*latRad));
    let easting = 0.9996 * n * (A + (1-t+c)*A**3/6 + (5-18*t+t*t+72*c-58*e2)*A**5/120) + 500000;
    let northing = 0.9996 * (M + n * Math.tan(latRad) * (A*A/2 + (5-t+9*c+4*c*c)*A**4/24 + (61-58*t+t*t+600*c-330*e2)*A**6/720));
    if (lat < 0) northing += 10000000;
    return `${zoneNum}${zoneLetter} ${Math.round(easting)}E ${Math.round(northing)}N`;
  }

  $: gridCoord = gridToLatLon(value);

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

  // Mercator tile units for the field bounds
  $: fTileLeft = level === "square" ? lon2tile(fieldLon) : 0;
  $: fTileRight = level === "square" ? lon2tile(fieldLon + 20) : 0;
  $: fTileTop = level === "square" ? lat2tile(fieldLatTop) : 0;
  $: fTileBot = level === "square" ? lat2tile(fieldLatBot) : 0;
  $: fTileW = fTileRight - fTileLeft;
  $: fTileH = fTileBot - fTileTop;

  // Integer tile range
  $: tileX0 = Math.floor(fTileLeft);
  $: tileX1 = Math.ceil(fTileRight);
  $: tileY0 = Math.floor(fTileTop);
  $: tileY1 = Math.ceil(fTileBot);

  // Build tile list with percentage positions relative to the field
  $: tiles = (() => {
    if (level !== "square" || fTileW === 0) return [];
    const list = [];
    for (let ty = tileY0; ty < Math.min(tileY1, tileY0 + 10); ty++) {
      for (let tx = tileX0; tx < Math.min(tileX1, tileX0 + 10); tx++) {
        list.push({
          x: tx, y: ty,
          left: ((tx - fTileLeft) / fTileW) * 100,
          top: ((ty - fTileTop) / fTileH) * 100,
          width: (1 / fTileW) * 100,
          height: (1 / fTileH) * 100,
        });
      }
    }
    return list;
  })();

  // Grid square positions using Mercator to match tiles
  function sqStyle(lonIdx, latIdx) {
    const sqLatTop = fieldLatTop - latIdx * 1;
    const sqLatBot = sqLatTop - 1;
    const sqLonLeft = fieldLon + lonIdx * 2;

    const left = ((lon2tile(sqLonLeft) - fTileLeft) / fTileW) * 100;
    const right = ((lon2tile(sqLonLeft + 2) - fTileLeft) / fTileW) * 100;
    const top = ((lat2tile(sqLatTop) - fTileTop) / fTileH) * 100;
    const bottom = ((lat2tile(sqLatBot) - fTileTop) / fTileH) * 100;

    return `left:${left}%;top:${top}%;width:${right - left}%;height:${bottom - top}%`;
  }
</script>

<div class="gridmap">
  {#if level === "field"}
    <div class="map-header">
      <span class="map-title">Select Field</span>
      {#if parsedField}
        <span class="current">Current: {value}</span>
      {/if}
    </div>
    {#if gridCoord}
      <div class="coord-info">
        <span>Center: {fmtDecimal(gridCoord)}</span>
        <span>{fmtDMS(gridCoord)}</span>
        <span>{fmtUTM(gridCoord)}</span>
      </div>
    {/if}
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
    {#if gridCoord}
      <div class="coord-info">
        <span>Center: {fmtDecimal(gridCoord)}</span>
        <span>{fmtDMS(gridCoord)}</span>
        <span>{fmtUTM(gridCoord)}</span>
      </div>
    {/if}
    <div class="zoomed-container" style="aspect-ratio: {fTileW}/{fTileH}">
      <!-- OSM tiles -->
      <div class="tiles-layer">
        {#each tiles as tile}
          <img
            src="/api/tiles/{ZOOM}/{tile.x}/{tile.y}.png"
            alt=""
            class="tile"
            style="left:{tile.left}%;top:{tile.top}%;width:{tile.width}%;height:{tile.height}%"
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
    max-width: 100%;
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

  .coord-info {
    display: flex;
    gap: 1.5rem;
    font-size: 0.75rem;
    color: var(--text-dim);
    margin-bottom: 0.4rem;
    font-family: monospace;
    overflow: hidden;
    white-space: nowrap;
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
