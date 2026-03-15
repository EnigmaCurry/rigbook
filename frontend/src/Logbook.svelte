<script>
  import { onMount, createEventDispatcher } from "svelte";
  import Autocomplete from "./Autocomplete.svelte";

  export let editId = null;
  export let prefill = null;
  export let vfoFreq = "";
  export let vfoMode = "";

  const dispatch = createEventDispatcher();

  let contacts = [];

  // Form fields
  let call = "";
  let freq = "";
  let mode = "CW";
  let rst_sent = "599";
  let rst_recv = "599";
  let pota_park = "";
  let name = "";
  let qth = "";
  let state = "";
  let country = "United States";
  let grid = "";
  let skcc = "";
  function utcNowDate() { return new Date().toISOString().slice(0, 10); }
  function utcNowTime() { return new Date().toISOString().slice(11, 19); }
  let datePart = utcNowDate();
  let timePart = utcNowTime();
  let comments = "";
  let notes = "";

  let countries = [];
  let subdivisions = [];
  let availableModes = [];
  $: countryItems = countries.map(c => ({ name: c.name, aliases: c.aliases || [] }));
  $: subdivisionNames = subdivisions.map(s => s.name);
  let submitting = false;
  let errorMsg = "";
  let editingId = null;
  export let showForm = true;

  let sortCol = "timestamp";
  let sortAsc = false;

  const columns = [
    { key: "timestamp", label: "UTC" },
    { key: "call", label: "Call" },
    { key: "freq", label: "Freq" },
    { key: "mode", label: "Mode" },
    { key: "rst_sent", label: "RST S" },
    { key: "rst_recv", label: "RST R" },
    { key: "name", label: "Name" },
    { key: "qth", label: "QTH" },
    { key: "pota_park", label: "POTA" },
    { key: "comments", label: "Comments" },
  ];

  function toggleSort(key) {
    if (sortCol === key) {
      sortAsc = !sortAsc;
    } else {
      sortCol = key;
      sortAsc = key === "timestamp" ? false : true;
    }
  }

  $: sortedContacts = [...contacts].sort((a, b) => {
    let va = a[sortCol] ?? "";
    let vb = b[sortCol] ?? "";
    if (sortCol === "freq" || sortCol === "skcc") {
      va = parseFloat(va) || 0;
      vb = parseFloat(vb) || 0;
    } else if (typeof va === "string") {
      va = va.toLowerCase();
      vb = (vb || "").toLowerCase();
    }
    if (va < vb) return sortAsc ? -1 : 1;
    if (va > vb) return sortAsc ? 1 : -1;
    return 0;
  });

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

  async function fetchModes() {
    try {
      const res = await fetch("/api/flrig/modes");
      if (res.ok) availableModes = await res.json();
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

  // Auto-fill freq/mode from VFO when not editing
  // Apply prefill from hunting spot
  $: if (prefill && !editingId) {
    if (prefill.freq) freq = prefill.freq;
    if (prefill.mode) mode = prefill.mode;
    if (prefill.pota_park) pota_park = prefill.pota_park;
    if (prefill.grid) grid = prefill.grid;
    if (prefill.country) country = prefill.country;
    dispatch("prefillconsumed");
  }

  // Auto-fill freq/mode from VFO when not editing and no prefill
  $: if (!editingId && !prefill && vfoFreq) {
    freq = String(parseFloat(vfoFreq) / 1000);
  }
  $: if (!editingId && !prefill && vfoMode) {
    mode = vfoMode;
  }

  $: stripCall = () => { call = call.replace(/\s/g, ""); };
  $: stripGrid = () => { grid = grid.replace(/[^A-Za-z0-9]/g, ""); };
  $: stripPota = () => { pota_park = pota_park.replace(/[^A-Za-z0-9\-]/g, ""); };
  $: stripSkcc = () => { skcc = skcc.replace(/[^0-9]/g, ""); };

  function editContact(c) {
    editingId = c.id;
    showForm = true;
    dispatch("editchange", c.id);
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
    if (c.timestamp) {
      const iso = new Date(c.timestamp).toISOString();
      datePart = iso.slice(0, 10);
      timePart = iso.slice(11, 19);
    } else {
      datePart = "";
      timePart = "";
    }
    errorMsg = "";
    const match = countries.find(co => co.name === country);
    fetchSubdivisions(match ? match.code : "");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() {
    editingId = null;
    dispatch("editchange", null);
    dispatch("navigate", "log");
    clearForm();
  }

  async function deleteContact() {
    if (!editingId) return;
    if (!confirm(`Delete contact ${call}?`)) return;
    try {
      const res = await fetch(`/api/contacts/${editingId}`, { method: "DELETE" });
      if (res.ok) {
        editingId = null;
        dispatch("editchange", null);
        dispatch("navigate", "log");
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
        rst_sent: rst_sent.trim() || null,
        rst_recv: rst_recv.trim() || null,
        pota_park: pota_park.trim().toUpperCase() || null,
        name: name || null,
        qth: qth.trim() || null,
        state: state.trim() || null,
        country: country.trim() || null,
        grid: grid.trim().toUpperCase() || null,
        skcc: skcc ? parseInt(skcc, 10) : null,
        comments: comments || null,
        notes: notes || null,
        timestamp: `${datePart}T${timePart || "00:00:00"}Z`,
      };
      const res = await fetch(`/api/contacts/${editingId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        editingId = null;
        dispatch("editchange", null);
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
    mode = "CW";
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
    datePart = utcNowDate();
    timePart = utcNowTime();
    fetchSubdivisions("US");
  }

  async function submitContact() {
    const required = { call, freq, mode };
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
        rst_sent: rst_sent.trim() || null,
        rst_recv: rst_recv.trim() || null,
        pota_park: pota_park.trim().toUpperCase() || null,
        name: name || null,
        qth: qth.trim() || null,
        state: state.trim() || null,
        country: country.trim() || null,
        grid: grid.trim().toUpperCase() || null,
        skcc: skcc ? parseInt(skcc, 10) : null,
        comments: comments || null,
        notes: notes || null,
        timestamp: `${datePart}T${timePart || "00:00:00"}Z`,
      };
      const res = await fetch("/api/contacts/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        call = "";
        pota_park = "";
        name = "";
        qth = "";
        grid = "";
        skcc = "";
        comments = "";
        notes = "";
        datePart = utcNowDate();
        timePart = utcNowTime();
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

  async function loadEditFromId(id) {
    if (!id) return;
    try {
      const res = await fetch(`/api/contacts/${id}`);
      if (res.ok) {
        const c = await res.json();
        editContact(c);
      }
    } catch {}
  }

  let handledEditId = null;

  $: if (editId && editId !== handledEditId && contacts.length > 0) {
    handledEditId = editId;
    const c = contacts.find(x => x.id === editId);
    if (c) editContact(c);
    else loadEditFromId(editId);
  } else if (!editId) {
    handledEditId = null;
  }

  onMount(() => {
    fetchContacts();
    fetchCountries();
    fetchModes();
    fetchSubdivisions("US");
  });

  function formatFreq(f) {
    if (!f) return "--";
    const n = parseFloat(f);
    if (isNaN(n)) return f;
    return parseFloat(n.toFixed(1)).toString() + " KHz";
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

{#if showForm}
<form on:submit|preventDefault={editingId ? saveEdit : submitContact} on:keydown={e => e.key === "Enter" && e.target.tagName !== "TEXTAREA" && e.preventDefault()}>
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
      <label>Mode *</label>
      <Autocomplete bind:value={mode} items={availableModes} />
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
      <label for="comments">Comments (public)</label>
      <input id="comments" type="text" bind:value={comments} />
    </div>
  </div>

  <div class="form-row">
    <div class="field">
      <label for="date">Date (UTC)</label>
      <input id="date" type="date" bind:value={datePart} />
    </div>
    <div class="field">
      <label for="time">Time (UTC)</label>
      <input id="time" type="time" step="1" bind:value={timePart} />
    </div>
    <div class="field wide">
      <label for="notes">Notes (private)</label>
      <textarea id="notes" bind:value={notes} rows="2"></textarea>
    </div>
  </div>

  <div class="form-row">
    <button type="submit" disabled={submitting || !call.trim() || !freq.trim() || !mode.trim()}>
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
      <button type="button" class="btn-clear" on:click={() => { dispatch("navigate", "log"); clearForm(); }}>Cancel</button>
    {/if}
    {#if errorMsg}
      <span class="error">{errorMsg}</span>
    {/if}
  </div>
</form>
{/if}

<section class="log">
  <h2>Log ({contacts.length})</h2>
  {#if contacts.length === 0}
    <p class="empty">No contacts logged yet.</p>
  {:else}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            {#each columns as col}
              <th class="sortable" on:click={() => toggleSort(col.key)}>
                {col.label}{#if sortCol === col.key}{sortAsc ? " ▲" : " ▼"}{/if}
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each sortedContacts as c}
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

<style>
  form {
    background: var(--bg-card);
    border: 1px solid var(--border);
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
    color: var(--text-muted);
    margin-bottom: 2px;
  }

  input,
  textarea {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 0.35rem 0.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    border-radius: 3px;
  }

  input:focus,
  textarea:focus {
    outline: none;
    border-color: var(--accent);
  }

  textarea {
    resize: vertical;
  }

  button {
    background: var(--accent);
    color: var(--bg);
    border: none;
    padding: 0.5rem 1.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: bold;
    border-radius: 3px;
    cursor: pointer;
  }

  button:hover:not(:disabled):not(.btn-clear):not(.btn-delete) {
    background: var(--accent-hover);
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-clear {
    background: var(--btn-secondary);
    color: var(--text);
  }

  .btn-clear:hover {
    background: var(--btn-secondary-hover);
  }

  .btn-delete {
    background: var(--accent-delete);
    color: #fff;
  }

  .btn-delete:hover {
    background: var(--accent-delete-hover);
  }

  .error {
    color: var(--accent-error);
    font-size: 0.85rem;
    margin-left: 0.5rem;
  }

  .log h2 {
    color: var(--accent);
    font-size: 1.1rem;
    margin: 0 0 0.5rem 0;
  }

  .empty {
    color: var(--text-dim);
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
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    padding: 0.3rem 0.5rem;
    white-space: nowrap;
  }

  th.sortable {
    cursor: pointer;
    user-select: none;
  }

  th.sortable:hover {
    color: var(--accent);
  }

  td {
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid var(--bg-card);
    white-space: nowrap;
  }

  td.call {
    color: var(--accent-callsign);
    font-weight: bold;
  }

  tr.clickable {
    cursor: pointer;
  }

  tbody tr:hover {
    background: var(--row-hover);
  }

  tr.editing {
    background: var(--row-editing);
  }
</style>
