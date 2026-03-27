<script>
  import { onMount, onDestroy } from "svelte";

  let data = null;
  let loading = true;
  let error = "";
  let pollInterval;

  async function fetchConditions() {
    try {
      const res = await fetch("/api/solar/conditions");
      if (res.ok) {
        data = await res.json();
        error = "";
      } else {
        error = `Failed to fetch: ${res.status}`;
      }
    } catch (e) {
      error = e.message;
    }
    loading = false;
  }

  onMount(() => {
    fetchConditions();
    pollInterval = setInterval(fetchConditions, 30000);
  });

  onDestroy(() => {
    clearInterval(pollInterval);
  });

  function conditionColor(c) {
    switch ((c || "").toLowerCase()) {
      case "good": return "#00cc66";
      case "fair": return "#ccaa00";
      case "poor": return "#cc4444";
      default: return "var(--text-muted)";
    }
  }

  function isStale(updated) {
    if (!updated) return false;
    const d = new Date(updated.replace("GMT", "UTC"));
    if (isNaN(d)) return false;
    return (Date.now() - d.getTime()) > 20 * 60 * 1000;
  }

  function geoColor(g) {
    const v = (g || "").toLowerCase();
    if (v.includes("quiet")) return "#00cc66";
    if (v.includes("unsettled") || v.includes("active")) return "#ccaa00";
    if (v.includes("storm")) return "#cc4444";
    return "var(--text)";
  }
</script>

<div class="conditions">
  <h2>Band Conditions</h2>

  {#if loading}
    <p class="status">Loading solar data...</p>
  {:else if error}
    <p class="status error">{error}</p>
  {:else if data}
    <div class="solar-summary">
      <div class="solar-grid">
        <div class="solar-item">
          <span class="solar-label">Solar Flux</span>
          <span class="solar-value">{data.solarflux}</span>
        </div>
        <div class="solar-item">
          <span class="solar-label">Sunspots</span>
          <span class="solar-value">{data.sunspots}</span>
        </div>
        <div class="solar-item">
          <span class="solar-label">A-Index</span>
          <span class="solar-value">{data.aindex}</span>
        </div>
        <div class="solar-item">
          <span class="solar-label">K-Index</span>
          <span class="solar-value">{data.kindex}</span>
        </div>
        <div class="solar-item">
          <span class="solar-label">X-Ray</span>
          <span class="solar-value">{data.xray}</span>
        </div>
        <div class="solar-item">
          <span class="solar-label">Geomag</span>
          <span class="solar-value" style="color: {geoColor(data.geomagfield)}">{data.geomagfield}</span>
        </div>
        <div class="solar-item">
          <span class="solar-label">Solar Wind</span>
          <span class="solar-value">{data.solarwind} km/s</span>
        </div>
        <div class="solar-item">
          <span class="solar-label">Sig Noise</span>
          <span class="solar-value">{data.signalnoise}</span>
        </div>
      </div>
    </div>

    <h3>HF Bands</h3>
    <div class="band-table">
      <table>
        <thead>
          <tr>
            <th>Band</th>
            <th>Day</th>
            <th>Night</th>
          </tr>
        </thead>
        <tbody>
          {#each ["80m-40m", "30m-20m", "17m-15m", "12m-10m"] as bandName}
            {@const day = data.bands.find(b => b.name === bandName && b.time === "day")}
            {@const night = data.bands.find(b => b.name === bandName && b.time === "night")}
            <tr>
              <td class="band-name">{bandName}</td>
              <td style="color: {conditionColor(day?.condition)}">{day?.condition || "—"}</td>
              <td style="color: {conditionColor(night?.condition)}">{night?.condition || "—"}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    {#if data.vhf && data.vhf.length > 0}
      <h3>VHF Conditions</h3>
      <div class="band-table">
        <table>
          <thead>
            <tr>
              <th>Phenomenon</th>
              <th>Location</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {#each data.vhf as v}
              <tr>
                <td>{v.name}</td>
                <td>{v.location.replace(/_/g, " ")}</td>
                <td style="color: {v.condition.toLowerCase().includes('closed') ? '#cc4444' : '#00cc66'}">{v.condition}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    {#if isStale(data.updated)}
      <p class="stale-warning">Data may be outdated — last update was {data.updated}. Check your internet connection.</p>
    {/if}
    <p class="updated">Updated: {data.updated} — Source: N0NBH / <a href="https://www.hamqsl.com/solar.html" target="_blank" rel="noopener">hamqsl.com</a></p>
  {/if}
</div>

<style>
  .conditions {
    max-width: 600px;
  }

  h2 {
    margin-bottom: 0.75rem;
  }

  h3 {
    margin: 1rem 0 0.5rem;
    font-size: 1rem;
  }

  .status {
    color: var(--text-muted);
    font-style: italic;
  }
  .status.error {
    color: var(--accent-error);
  }

  .solar-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 0.5rem;
  }

  .solar-item {
    background: var(--bg-card, #2a2a2e);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.5rem;
    text-align: center;
  }

  .solar-label {
    display: block;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
  }

  .solar-value {
    font-size: 1.1rem;
    font-weight: bold;
    color: var(--accent);
  }

  .band-table {
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th {
    background: var(--bg-card, #2a2a2e);
    padding: 0.4rem 0.75rem;
    text-align: left;
    font-size: 0.85rem;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
  }

  td {
    padding: 0.4rem 0.75rem;
    font-size: 0.9rem;
    border-bottom: 1px solid var(--border);
  }

  tr:last-child td {
    border-bottom: none;
  }

  .band-name {
    font-weight: bold;
    color: var(--accent);
  }

  .stale-warning {
    margin-top: 1rem;
    padding: 0.5rem 0.75rem;
    background: rgba(204, 170, 0, 0.15);
    border: 1px solid #ccaa00;
    border-radius: 4px;
    color: #ccaa00;
    font-size: 0.85rem;
  }

  .updated {
    margin-top: 1rem;
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  a {
    color: var(--accent-vfo);
    text-decoration: none;
  }

  a:hover {
    color: var(--accent);
  }
</style>
