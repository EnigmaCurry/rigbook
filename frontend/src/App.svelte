<script>
  import { onMount, onDestroy } from "svelte";

  let myCallsign = "";
  let contacts = [];

  let flrigInterval;

  // Form fields
  let call = "";
  let freq = "";
  let mode = "";
  let rst_sent = "599";
  let rst_recv = "599";
  let pota_park = "";
  let name = "";
  let qth = "";
  let state = "";
  let country = "";
  let grid = "";
  let skcc = "";
  let comments = "";
  let notes = "";

  let countries = [];
  let subdivisions = [];
  let submitting = false;

  async function fetchCallsign() {
    try {
      const res = await fetch("/api/settings/my_callsign");
      if (res.ok) {
        const data = await res.json();
        myCallsign = data.value || "";
      }
    } catch {}
  }

  async function fetchContacts() {
    try {
      const res = await fetch("/api/contacts");
      if (res.ok) {
        contacts = await res.json();
      }
    } catch {}
  }

  async function fetchCountries() {
    try {
      const res = await fetch("/api/geo/countries");
      if (res.ok) countries = await res.json();
    } catch {}
  }

  async function fetchSubdivisions(code) {
    if (!code) { subdivisions = []; return; }
    try {
      const res = await fetch(`/api/geo/subdivisions/${code}`);
      if (res.ok) subdivisions = await res.json();
      else subdivisions = [];
    } catch { subdivisions = []; }
  }

  function onCountryChange() {
    state = "";
    const match = countries.find(c => c.name === country);
    fetchSubdivisions(match ? match.code : "");
  }

  async function pollFlrig() {
    try {
      const res = await fetch("/api/flrig/status");
      if (res.ok) {
        const data = await res.json();
        if (data.freq) freq = data.freq;
        if (data.mode) mode = data.mode;
      }
    } catch {}
  }

  async function submitContact() {
    if (!call.trim() || !freq.trim() || !mode.trim()) return;
    submitting = true;
    try {
      const body = {
        call: call.trim().toUpperCase(),
        freq: freq.trim(),
        mode: mode.trim().toUpperCase(),
        rst_sent: rst_sent || null,
        rst_recv: rst_recv || null,
        pota_park: pota_park || null,
        name: name || null,
        qth: qth || null,
        state: state || null,
        country: country || null,
        grid: grid || null,
        skcc: skcc || null,
        comments: comments || null,
        notes: notes || null,
      };
      const res = await fetch("/api/contacts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        // Reset form (freq/mode kept — likely same for next QSO)
        call = "";
        pota_park = "";
        name = "";
        qth = "";
        state = "";
        country = "";
        grid = "";
        skcc = "";
        comments = "";
        notes = "";
        await fetchContacts();
      }
    } catch {}
    submitting = false;
  }

  onMount(() => {
    fetchCallsign();
    fetchContacts();
    fetchCountries();
    pollFlrig();
    flrigInterval = setInterval(pollFlrig, 2000);
  });

  onDestroy(() => {
    if (flrigInterval) clearInterval(flrigInterval);
  });

  function formatFreq(f) {
    if (!f) return "--";
    const n = parseFloat(f);
    if (isNaN(n)) return f;
    return n.toFixed(4) + " MHz";
  }

  function formatTimestamp(ts) {
    if (!ts) return "";
    try {
      const d = new Date(ts);
      return d.toISOString().replace("T", " ").substring(0, 19) + "z";
    } catch {
      return ts;
    }
  }
</script>

<main>
  <header>
    <h1>Rigbook</h1>
    {#if myCallsign}
      <span class="callsign">{myCallsign}</span>
    {/if}
  </header>

  <form on:submit|preventDefault={submitContact}>
    <div class="form-row">
      <div class="field">
        <label for="call">Call *</label>
        <input
          id="call"
          type="text"
          bind:value={call}
          required
          autocomplete="off"
          style="text-transform: uppercase"
        />
      </div>
      <div class="field">
        <label for="freq">Freq (MHz) *</label>
        <input id="freq" type="text" bind:value={freq} required />
      </div>
      <div class="field">
        <label for="mode">Mode *</label>
        <input id="mode" type="text" bind:value={mode} required style="text-transform: uppercase" />
      </div>
      <div class="field">
        <label for="rst_sent">RST Sent</label>
        <input id="rst_sent" type="text" bind:value={rst_sent} />
      </div>
      <div class="field">
        <label for="rst_recv">RST Recv</label>
        <input id="rst_recv" type="text" bind:value={rst_recv} />
      </div>
      <div class="field">
        <label for="name">Name</label>
        <input id="name" type="text" bind:value={name} />
      </div>
    </div>

    <div class="form-row">
      <div class="field">
        <label for="qth">QTH</label>
        <input id="qth" type="text" bind:value={qth} />
      </div>
      <div class="field">
        <label for="country">Country</label>
        <select id="country" bind:value={country} on:change={onCountryChange}>
          <option value=""></option>
          {#each countries as c}
            <option value={c.name}>{c.name}</option>
          {/each}
        </select>
      </div>
      <div class="field">
        <label for="state">State</label>
        {#if subdivisions.length > 0}
          <select id="state" bind:value={state}>
            <option value=""></option>
            {#each subdivisions as s}
              <option value={s.name}>{s.name}</option>
            {/each}
          </select>
        {:else}
          <input id="state" type="text" bind:value={state} />
        {/if}
      </div>
      <div class="field">
        <label for="grid">Grid</label>
        <input id="grid" type="text" bind:value={grid} />
      </div>
    </div>

    <div class="form-row">
      <div class="field">
        <label for="pota_park">POTA Park</label>
        <input id="pota_park" type="text" bind:value={pota_park} />
      </div>
      <div class="field">
        <label for="skcc">SKCC</label>
        <input id="skcc" type="text" bind:value={skcc} />
      </div>
      <div class="field wide">
        <label for="comments">Comments</label>
        <input id="comments" type="text" bind:value={comments} />
      </div>
    </div>

    <div class="form-row">
      <div class="field wide">
        <label for="notes">Notes</label>
        <textarea id="notes" bind:value={notes} rows="2"></textarea>
      </div>
    </div>

    <div class="form-row">
      <button type="submit" disabled={submitting || !call.trim() || !freq.trim() || !mode.trim()}>
        {submitting ? "Logging..." : "Log QSO"}
      </button>
    </div>
  </form>

  <section class="log">
    <h2>Log ({contacts.length})</h2>
    {#if contacts.length === 0}
      <p class="empty">No contacts logged yet.</p>
    {:else}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>UTC</th>
              <th>Call</th>
              <th>Freq</th>
              <th>Mode</th>
              <th>RST S</th>
              <th>RST R</th>
              <th>Name</th>
              <th>QTH</th>
              <th>POTA</th>
              <th>Comments</th>
            </tr>
          </thead>
          <tbody>
            {#each contacts as c}
              <tr>
                <td>{formatTimestamp(c.timestamp)}</td>
                <td class="call">{c.call}</td>
                <td>{formatFreq(c.freq)}</td>
                <td>{c.mode || ""}</td>
                <td>{c.rst_sent || ""}</td>
                <td>{c.rst_recv || ""}</td>
                <td>{c.name || ""}</td>
                <td>{c.qth || ""}</td>
                <td>{c.pota_park || ""}</td>
                <td>{c.comments || ""}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</main>

<style>
  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    background: #3b3d4a;
    color: #eaeaea;
    font-family: "Courier New", Courier, monospace;
    font-size: 14px;
  }

  main {
    max-width: 1100px;
    margin: 0 auto;
    padding: 1rem;
  }

  header {
    display: flex;
    align-items: baseline;
    gap: 1rem;
    border-bottom: 1px solid #5a5c6a;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
  }

  h1 {
    margin: 0;
    color: #00ff88;
    font-size: 1.6rem;
  }

  .callsign {
    color: #ffcc00;
    font-size: 1.2rem;
    font-weight: bold;
  }

  form {
    background: #4a4c5a;
    border: 1px solid #5a5c6a;
    border-radius: 4px;
    padding: 0.75rem;
    margin-bottom: 1rem;
  }

  .form-row {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
  }

  .field {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 120px;
  }

  .field.wide {
    flex: 2;
    min-width: 240px;
  }

  .field label {
    font-size: 0.75rem;
    color: #b0b2be;
    margin-bottom: 2px;
  }

  input,
  textarea,
  select {
    background: #5a5c6a;
    border: 1px solid #6e7080;
    color: #f0f0f0;
    padding: 0.35rem 0.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    border-radius: 3px;
  }

  input:focus,
  textarea:focus,
  select:focus {
    outline: none;
    border-color: #00ff88;
  }

  textarea {
    resize: vertical;
  }

  button {
    background: #00ff88;
    color: #1a1a2e;
    border: none;
    padding: 0.5rem 1.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: bold;
    border-radius: 3px;
    cursor: pointer;
  }

  button:hover:not(:disabled) {
    background: #00cc6a;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .log h2 {
    color: #00ff88;
    font-size: 1.1rem;
    margin: 0 0 0.5rem 0;
  }

  .empty {
    color: #8a8c98;
    font-style: italic;
  }

  .table-wrap {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }

  th {
    text-align: left;
    color: #b0b2be;
    border-bottom: 1px solid #5a5c6a;
    padding: 0.3rem 0.5rem;
    white-space: nowrap;
  }

  td {
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid #4a4c5a;
    white-space: nowrap;
  }

  td.call {
    color: #ffcc00;
    font-weight: bold;
  }

  tbody tr:hover {
    background: #44465a;
  }
</style>
