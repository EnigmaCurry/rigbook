<script>
  import { onMount, onDestroy } from "svelte";
  import Autocomplete from "./Autocomplete.svelte";

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
  let country = "United States";
  let grid = "";
  let skcc = "";
  let timestamp = "";
  let comments = "";
  let notes = "";

  function nowUTC() {
    return new Date().toISOString().slice(0, 16);
  }

  let countries = [];
  let subdivisions = [];
  $: countryItems = countries.map(c => ({ name: c.name, aliases: c.aliases || [] }));
  $: subdivisionNames = subdivisions.map(s => s.name);
  let submitting = false;
  let errorMsg = "";
  let editingId = null;

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
      const res = await fetch("/api/contacts/");
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
    if (editingId) return;
    try {
      const res = await fetch("/api/flrig/status");
      if (res.ok) {
        const data = await res.json();
        if (data.freq) freq = data.freq;
        if (data.mode) mode = data.mode;
      }
    } catch {}
  }

  $: stripCall = () => { call = call.replace(/\s/g, ""); };
  $: stripGrid = () => { grid = grid.replace(/[^A-Za-z0-9]/g, ""); };
  $: stripPota = () => { pota_park = pota_park.replace(/[^A-Za-z0-9\-]/g, ""); };
  $: stripSkcc = () => { skcc = skcc.replace(/[^0-9]/g, ""); };

  function editContact(c) {
    editingId = c.id;
    call = c.call || "";
    freq = c.freq || "";
    mode = c.mode || "";
    rst_sent = c.rst_sent || "";
    rst_recv = c.rst_recv || "";
    pota_park = c.pota_park || "";
    name = c.name || "";
    qth = c.qth || "";
    state = c.state || "";
    country = c.country || "";
    grid = c.grid || "";
    skcc = c.skcc != null ? String(c.skcc) : "";
    comments = c.comments || "";
    notes = c.notes || "";
    timestamp = c.timestamp ? new Date(c.timestamp).toISOString().slice(0, 16) : "";
    errorMsg = "";
    // Load subdivisions for the contact's country without clearing state
    const match = countries.find(co => co.name === country);
    fetchSubdivisions(match ? match.code : "");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() {
    editingId = null;
    clearForm();
  }

  async function deleteContact() {
    if (!editingId) return;
    if (!confirm(`Delete contact ${call}?`)) return;
    try {
      const res = await fetch(`/api/contacts/${editingId}`, { method: "DELETE" });
      if (res.ok) {
        editingId = null;
        clearForm();
        await fetchContacts();
      } else {
        errorMsg = `Delete failed: ${res.status} ${res.statusText}`;
      }
    } catch (e) {
      errorMsg = `Network error: ${e.message}`;
    }
  }

  async function saveEdit() {
    if (!editingId) return;
    submitting = true;
    errorMsg = "";
    try {
      const body = {
        call: call.trim().toUpperCase(),
        freq: freq.trim(),
        mode: mode.trim().toUpperCase(),
        rst_sent: rst_sent.trim(),
        rst_recv: rst_recv.trim(),
        pota_park: pota_park.trim().toUpperCase(),
        name: name || null,
        qth: qth.trim(),
        state: state.trim(),
        country: country.trim(),
        grid: grid.trim().toUpperCase(),
        skcc: parseInt(skcc, 10),
        comments: comments || null,
        notes: notes || null,
        timestamp: timestamp ? new Date(timestamp + "Z").toISOString() : null,
      };
      const res = await fetch(`/api/contacts/${editingId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        editingId = null;
        clearForm();
        await fetchContacts();
      } else {
        const data = await res.json().catch(() => null);
        errorMsg = data?.detail || `Error: ${res.status} ${res.statusText}`;
      }
    } catch (e) {
      errorMsg = `Network error: ${e.message}`;
    }
    submitting = false;
  }

  function clearForm() {
    call = "";
    freq = "";
    mode = "";
    rst_sent = "599";
    rst_recv = "599";
    pota_park = "";
    name = "";
    qth = "";
    state = "";
    country = "United States";
    grid = "";
    skcc = "";
    comments = "";
    notes = "";
    timestamp = "";
    fetchSubdivisions("US");
  }

  async function submitContact() {
    const required = { call, freq, mode, rst_sent, rst_recv, qth, country, state, grid, pota_park, skcc };
    const missing = Object.entries(required).filter(([, v]) => !v || !String(v).trim());
    if (missing.length) {
      errorMsg = `Required: ${missing.map(([k]) => k).join(", ")}`;
      return;
    }
    submitting = true;
    errorMsg = "";
    try {
      const body = {
        call: call.trim().toUpperCase(),
        freq: freq.trim(),
        mode: mode.trim().toUpperCase(),
        rst_sent: rst_sent.trim(),
        rst_recv: rst_recv.trim(),
        pota_park: pota_park.trim().toUpperCase(),
        name: name || null,
        qth: qth.trim(),
        state: state.trim(),
        country: country.trim(),
        grid: grid.trim().toUpperCase(),
        skcc: parseInt(skcc, 10),
        comments: comments || null,
        notes: notes || null,
        timestamp: timestamp ? new Date(timestamp + "Z").toISOString() : new Date().toISOString(),
      };
      const res = await fetch("/api/contacts/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        // Reset form (freq/mode/country/state kept — likely same for next QSO)
        call = "";
        pota_park = "";
        name = "";
        qth = "";
        grid = "";
        skcc = "";
        comments = "";
        notes = "";
        await fetchContacts();
      } else {
        const data = await res.json().catch(() => null);
        errorMsg = data?.detail || `Error: ${res.status} ${res.statusText}`;
      }
    } catch (e) {
      errorMsg = `Network error: ${e.message}`;
    }
    submitting = false;
  }

  onMount(() => {
    fetchCallsign();
    fetchContacts();
    fetchCountries();
    fetchSubdivisions("US");
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
    // Strip trailing zeros after decimal
    return parseFloat(n.toFixed(4)).toString() + " KHz";
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

  <form on:submit|preventDefault={editingId ? saveEdit : submitContact}>
    <div class="form-row">
      <div class="field">
        <label for="call">Call *</label>
        <input
          id="call"
          type="text"
          bind:value={call}
          on:input={stripCall}
          required
          maxlength="10"
          autocomplete="off"
          style="text-transform: uppercase"
        />
      </div>
      <div class="field">
        <label for="freq">Freq (KHz) *</label>
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
        <label>Country</label>
        <Autocomplete bind:value={country} items={countryItems} on:pick={onCountryChange} on:input={onCountryChange} />
      </div>
      <div class="field">
        <label>State</label>
        <Autocomplete bind:value={state} items={subdivisionNames} />
      </div>
      <div class="field">
        <label for="grid">Grid</label>
        <input id="grid" type="text" bind:value={grid} on:input={stripGrid} style="text-transform: uppercase" />
      </div>
    </div>

    <div class="form-row">
      <div class="field">
        <label for="pota_park">POTA Park</label>
        <input id="pota_park" type="text" bind:value={pota_park} on:input={stripPota} style="text-transform: uppercase" />
      </div>
      <div class="field">
        <label for="skcc">SKCC</label>
        <input id="skcc" type="text" bind:value={skcc} on:input={stripSkcc} inputmode="numeric" />
      </div>
      <div class="field wide">
        <label for="comments">Comments</label>
        <input id="comments" type="text" bind:value={comments} />
      </div>
    </div>

    <div class="form-row">
      <div class="field">
        <label for="timestamp">Timestamp (UTC)</label>
        <input id="timestamp" type="datetime-local" bind:value={timestamp} placeholder="now" />
      </div>
      <div class="field wide">
        <label for="notes">Notes</label>
        <textarea id="notes" bind:value={notes} rows="2"></textarea>
      </div>
    </div>

    <div class="form-row">
      <button type="submit" disabled={submitting || !call.trim() || !freq.trim() || !mode.trim() || !rst_sent.trim() || !rst_recv.trim() || !qth.trim() || !country.trim() || !state.trim() || !grid.trim() || !pota_park.trim() || !skcc.trim()}>
        {#if editingId}
          {submitting ? "Saving..." : "Save Edit"}
        {:else}
          {submitting ? "Logging..." : "Log QSO"}
        {/if}
      </button>
      {#if editingId}
        <button type="button" class="btn-clear" on:click={cancelEdit}>Cancel</button>
        <button type="button" class="btn-delete" on:click={deleteContact}>Delete</button>
      {:else}
        <button type="button" class="btn-clear" on:click={clearForm}>Clear</button>
      {/if}
      {#if errorMsg}
        <span class="error">{errorMsg}</span>
      {/if}
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
              <tr class="clickable" class:editing={editingId === c.id} on:click={() => editContact(c)}>
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
  textarea {
    background: #5a5c6a;
    border: 1px solid #6e7080;
    color: #f0f0f0;
    padding: 0.35rem 0.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    border-radius: 3px;
  }

  input:focus,
  textarea:focus {
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

  .btn-clear {
    background: #6e7080;
    color: #eaeaea;
  }

  .btn-clear:hover {
    background: #5a5c6a;
  }

  .btn-delete {
    background: #cc3333;
    color: #fff;
  }

  .btn-delete:hover {
    background: #aa2222;
  }

  .error {
    color: #ff6b6b;
    font-size: 0.85rem;
    margin-left: 0.5rem;
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

  tr.clickable {
    cursor: pointer;
  }

  tbody tr:hover {
    background: #44465a;
  }

  tr.editing {
    background: #3a5a3a;
  }
</style>
