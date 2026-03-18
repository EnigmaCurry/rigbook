<script>
  import { onDestroy, tick, createEventDispatcher } from "svelte";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";
  import { parkAward, parkAwardTitle } from "./parkAward.js";

  const dispatch = createEventDispatcher();

  export let park = null;
  export let showAddQso = false;

  let mapEl;
  let map = null;

  function destroyMap() {
    if (map) { map.remove(); map = null; }
  }

  async function renderMap() {
    await tick();
    destroyMap();
    if (!mapEl || !park || park.latitude == null) return;
    map = L.map(mapEl, { scrollWheelZoom: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
      maxZoom: 18,
    }).addTo(map);
    const ll = [park.latitude, park.longitude];
    L.marker(ll).addTo(map)
      .bindPopup(`<b>${park.reference}</b><br>${park.name || ""}`)
      .openPopup();
    map.setView(ll, 12);
  }

  $: if (park) renderMap();

  onDestroy(() => {
    destroyMap();
  });
</script>

<div class="park-detail">
  <h3>{park.reference}</h3>
  <p class="park-detail-name">{park.name}</p>
  <div class="park-detail-layout">
    <div class="park-detail-info">
      <div class="park-detail-grid">
        <div class="detail-row"><span class="detail-label">Location</span> <span>{park.location_name || ""} ({park.location_desc || ""})</span></div>
        <div class="detail-row"><span class="detail-label">Country</span> <span>{park.program_name || ""}</span></div>
        {#if park.grid}
          <div class="detail-row"><span class="detail-label">Grid</span> <span>{park.grid}</span></div>
        {/if}
        {#if park.latitude != null && park.longitude != null}
          <div class="detail-row"><span class="detail-label">Coordinates</span> <span>{park.latitude}, {park.longitude}</span></div>
        {/if}
        {#if park.activations != null}
          <div class="detail-row"><span class="detail-label">Activations</span> <span>{park.activations}</span></div>
        {/if}
        {#if park.attempts != null}
          <div class="detail-row"><span class="detail-label">Attempts</span> <span>{park.attempts}</span></div>
        {/if}
        {#if park.qsos != null}
          <div class="detail-row"><span class="detail-label">QSOs</span> <span>{park.qsos}</span></div>
        {/if}
        <div class="detail-row">
          <span class="detail-label">My QSOs</span>
          <span>{park.my_qsos || 0} <span title="{parkAwardTitle(park.my_qsos || 0)}">{parkAward(park.my_qsos || 0)}</span></span>
        </div>
      </div>
      <div class="park-detail-links">
        <a href="https://pota.app/#/park/{park.reference}" target="_blank" rel="noopener">View on POTA</a>
        {#if showAddQso}
          <button class="add-qso-btn" on:click={() => dispatch("addqso", { pota_park: park.reference, grid: park.grid || "", country: park.program_name || "", state: park.location_name || "" })}>+ Add QSO</button>
        {/if}
      </div>
    </div>
    {#if park.latitude != null && park.longitude != null}
      <div class="park-detail-map-wrap">
        <div class="park-detail-map" bind:this={mapEl}></div>
      </div>
    {/if}
  </div>
  {#if park.contacts && park.contacts.length > 0}
    <h4 class="park-qsos-heading">My QSOs ({park.contacts.length})</h4>
    <div class="park-qsos-table">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Call</th>
            <th>Name</th>
            <th>Freq</th>
            <th>Mode</th>
            <th>RST S</th>
            <th>RST R</th>
          </tr>
        </thead>
        <tbody>
          {#each park.contacts as c}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
            <tr class="qso-row" on:click={() => { window.location.hash = `/log/${c.id}`; }}>
              <td>{c.timestamp ? c.timestamp.slice(0, 10) : ""}</td>
              <td class="call">{c.call}</td>
              <td>{c.name || ""}</td>
              <td>{c.freq || ""}</td>
              <td>{c.mode || ""}</td>
              <td>{c.rst_sent || ""}</td>
              <td>{c.rst_recv || ""}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .park-detail h3 {
    color: var(--accent-vfo);
    font-size: 1.3rem;
    margin: 0 0 0.25rem 0;
  }

  .park-detail-name {
    font-size: 1.1rem;
    color: var(--text);
    margin: 0 0 1rem 0;
  }

  .park-detail-grid {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin-bottom: 1rem;
  }

  .detail-row {
    display: flex;
    gap: 0.75rem;
    font-size: 0.9rem;
  }

  .detail-label {
    color: var(--text-dim);
    min-width: 10ch;
    flex-shrink: 0;
  }

  .park-detail-layout {
    display: flex;
    gap: 1.5rem;
    align-items: flex-start;
  }

  .park-detail-info {
    flex: 1;
    min-width: 0;
  }

  .park-detail-map-wrap {
    flex-shrink: 0;
    width: 350px;
  }

  .park-detail-map {
    width: 100%;
    height: 280px;
    border: 1px solid var(--border);
    border-radius: 3px;
  }

  @media (max-width: 700px) {
    .park-detail-layout {
      flex-direction: column;
    }

    .park-detail-map-wrap {
      width: 100%;
    }
  }

  .park-detail-links {
    margin-top: 0.75rem;
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .park-detail-links a {
    color: var(--accent);
    text-decoration: none;
    font-size: 0.85rem;
  }

  .park-detail-links a:hover {
    text-decoration: underline;
  }

  .add-qso-btn {
    background: var(--accent);
    color: var(--bg);
    border: none;
    padding: 0.3rem 0.8rem;
    font-family: inherit;
    font-size: 0.85rem;
    font-weight: bold;
    border-radius: 3px;
    cursor: pointer;
  }

  .add-qso-btn:hover {
    background: var(--accent-hover);
  }

  .park-qsos-heading {
    color: var(--text-muted);
    font-size: 0.95rem;
    margin: 1rem 0 0.5rem 0;
  }

  .park-qsos-table {
    overflow-x: auto;
  }

  .park-qsos-table table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }

  .park-qsos-table th {
    text-align: left;
    color: var(--text-dim);
    font-weight: normal;
    padding: 0.25rem 0.5rem;
    border-bottom: 1px solid var(--border);
  }

  .park-qsos-table td {
    padding: 0.3rem 0.5rem;
  }

  .park-qsos-table td.call {
    color: var(--accent-callsign);
    font-weight: bold;
  }

  .qso-row {
    cursor: pointer;
  }

  .qso-row:hover {
    background: var(--row-hover);
  }
</style>
