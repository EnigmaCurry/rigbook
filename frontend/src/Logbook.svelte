<script>
  import { onMount, createEventDispatcher } from "svelte";
  import Autocomplete from "./Autocomplete.svelte";
  import GridMap from "./GridMap.svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";

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
  let defaultRst = "599";
  let rst_sent = "599";
  let rst_recv = "599";
  let pota_park = "";
  let name = "";
  let qth = "";
  let state = "";
  let country = "";
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
  let showGridPicker = false;
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

  $: prevContactCount = call.trim() ? contacts.filter(c => c.call?.toUpperCase() === call.trim().toUpperCase()).length : 0;

  let logFilter = "all";
  $: if (prevContactCount === 0) logFilter = "all";

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

  $: displayedContacts = logFilter === "all" || !call.trim()
    ? sortedContacts
    : sortedContacts.filter(c => c.call?.toUpperCase() === call.trim().toUpperCase());

  async function fetchContacts() {
    try {
      const res = await fetch("/api/contacts/");
      if (res.ok) {
        contacts = await res.json();
      }
    } catch {}
  }

  async function fetchDefaultRst() {
    try {
      const res = await fetch("/api/settings/default_rst");
      if (res.ok) {
        const data = await res.json();
        if (data.value) {
          defaultRst = data.value;
          rst_sent = defaultRst;
          rst_recv = defaultRst;
        }
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
    prefillSource = "hunting";
    if (prefill.call) call = prefill.call;
    if (prefill.freq) freq = prefill.freq;
    if (prefill.mode) mode = prefill.mode;
    if (prefill.pota_park) pota_park = prefill.pota_park;
    if (prefill.grid) grid = prefill.grid;
    if (prefill.country) country = prefill.country;
    if (prefill.skcc) skcc = prefill.skcc;
    dispatch("prefillconsumed");
    // Lookup name from QRZ
    if (prefill.call) lookupCallsign(prefill.call.toUpperCase());
  }

  // Auto-fill freq/mode from VFO when not editing and no prefill
  $: if (!editingId && !prefill && vfoFreq) {
    freq = String(parseFloat(vfoFreq) / 1000);
  }
  $: if (!editingId && !prefill && vfoMode) {
    mode = vfoMode;
  }

  let lastQrzCall = "";
  let prefillSource = null; // tracks if prefill came from hunting

  async function lookupCallsign(callsign) {
    if (!callsign || callsign.length < 3 || callsign === lastQrzCall) return;
    lastQrzCall = callsign;

    // SKCC lookup
    try {
      const res = await fetch(`/api/skcc/lookup/${callsign}`);
      if (res.ok) {
        const data = await res.json();
        skcc = data.skcc || "";
      }
    } catch {}

    // QRZ lookup
    try {
      const res = await fetch(`/api/qrz/lookup/${callsign}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.error) return;
      // If from hunting spot, only fill name. Otherwise fill all empty fields.
      if (prefillSource === "hunting") {
        if (!name && data.name) name = data.name;
      } else {
        if (!name && data.name) name = data.name;
        if (!qth && data.qth) qth = data.qth;
        if (!state && data.state) state = data.state;
        if (!country && data.country) country = data.country;
        if (!grid && data.grid) grid = data.grid;
      }
    } catch {}
  }

  function onCallInput() {
    call = call.replace(/\s/g, "");
  }

  function onCallBlur() {
    if (call.length >= 3) {
      lookupCallsign(call.toUpperCase());
    }
  }

  $: stripCall = () => { call = call.replace(/\s/g, ""); };
  $: stripGrid = () => { grid = grid.replace(/[^A-Za-z0-9]/g, ""); };
  $: stripSkcc = () => { skcc = skcc.replace(/[^A-Za-z0-9]/g, ""); };

  // POTA park autocomplete
  let potaResults = [];
  let potaOpen = false;
  let potaHighlight = -1;
  let potaTimer = null;

  function onPotaInput() {
    pota_park = pota_park.replace(/[^A-Za-z0-9\- ]/g, "");
    potaHighlight = -1;
    clearTimeout(potaTimer);
    const q = pota_park.trim();
    if (q.length < 2) { potaResults = []; potaOpen = false; return; }
    potaTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/pota/parks/search?q=${encodeURIComponent(q)}`);
        if (res.ok) {
          potaResults = await res.json();
          potaOpen = potaResults.length > 0;
        }
      } catch {}
    }, 200);
  }

  function onPotaFocus() {
    if (potaResults.length > 0) potaOpen = true;
  }

  function onPotaBlur() {
    setTimeout(() => { potaOpen = false; }, 150);
  }

  function pickPota(park) {
    pota_park = park.reference;
    if (park.grid && !grid) grid = park.grid;
    potaOpen = false;
    potaResults = [];
  }

  function onPotaKeydown(e) {
    if (!potaOpen || potaResults.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      potaHighlight = (potaHighlight + 1) % potaResults.length;
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      potaHighlight = potaHighlight <= 0 ? potaResults.length - 1 : potaHighlight - 1;
    } else if (e.key === "Enter") {
      e.preventDefault();
      pickPota(potaResults[potaHighlight >= 0 ? potaHighlight : 0]);
    } else if (e.key === "Tab" && potaHighlight >= 0) {
      pickPota(potaResults[potaHighlight]);
    } else if (e.key === "Escape") {
      potaOpen = false;
    }
  }

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
    skcc = c.skcc || "";
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
    dispatch("navigate", "back");
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
        dispatch("navigate", "back");
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
        skcc: skcc.trim().toUpperCase() || null,
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
    lastQrzCall = "";
    prefillSource = null;
    call = "";
    freq = "";
    mode = "CW";
    rst_sent = defaultRst;
    rst_recv = defaultRst;
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
        skcc: skcc.trim().toUpperCase() || null,
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
    fetchDefaultRst();
    fetchCountries();
    fetchModes();
    fetchSubdivisions("US");
  });

  const BANDS = [
    { name: "160m", lo: 1800, hi: 2000 },
    { name: "80m", lo: 3500, hi: 4000 },
    { name: "60m", lo: 5330, hi: 5410 },
    { name: "40m", lo: 7000, hi: 7300 },
    { name: "30m", lo: 10100, hi: 10150 },
    { name: "20m", lo: 14000, hi: 14350 },
    { name: "17m", lo: 18068, hi: 18168 },
    { name: "15m", lo: 21000, hi: 21450 },
    { name: "12m", lo: 24890, hi: 24990 },
    { name: "10m", lo: 28000, hi: 29700 },
    { name: "6m", lo: 50000, hi: 54000 },
    { name: "2m", lo: 144000, hi: 148000 },
  ];

  function freqToBand(f) {
    const n = parseFloat(f);
    if (isNaN(n)) return "";
    const b = BANDS.find(b => n >= b.lo && n <= b.hi);
    return b ? b.name : "";
  }

  function formatFreq(f) {
    if (!f) return "--";
    const n = parseFloat(f);
    if (isNaN(n)) return f;
    return n.toFixed(1).padStart(9, "\u2007") + " KHz";
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

  function relativeTime(ts) {
    if (!ts) return "";
    try {
      const s = String(ts);
      const d = new Date(s.endsWith("Z") || s.includes("+") ? s : s + "Z");
      if (isNaN(d)) return "";
      const now = new Date();
      const diffMs = now - d;
      const absDiffMs = Math.abs(diffMs);
      const suffix = diffMs < 0 ? "from now" : "ago";
      const mins = Math.floor(absDiffMs / 60000);
      if (mins < 1) return "just now";
      if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ${suffix}`;
      const hours = Math.floor(mins / 60);
      if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ${suffix}`;
      const days = Math.floor(hours / 24);
      if (days < 30) return `${days} day${days === 1 ? "" : "s"} ${suffix}`;
      const months = Math.floor(days / 30);
      if (months < 12) return `${months} month${months === 1 ? "" : "s"} ${suffix}`;
      const years = Math.floor(days / 365);
      return `${years} year${years === 1 ? "" : "s"} ${suffix}`;
    } catch {
      return "";
    }
  }
</script>

{#if showForm}
<form on:submit|preventDefault={editingId ? saveEdit : submitContact} on:keydown={e => e.key === "Enter" && e.target.tagName !== "TEXTAREA" && e.preventDefault()}>
  <h3 class="form-heading">{editingId ? `Edit QSO — ${call || ""}` : "New QSO"}{#if editingId}{" "}<span class="prev-contact">({relativeTime(`${datePart}T${timePart || "00:00:00"}Z`)})</span>{:else if prevContactCount > 0}{" "}<span class="prev-contact">(you've contacted {call.trim().toUpperCase()} {prevContactCount} time{prevContactCount === 1 ? "" : "s"} before)</span>{/if}</h3>
  <div class="form-row">
    <div class="field">
      <label for="call">Call *</label>
      <input
        id="call"
        type="text"
        bind:value={call}
        on:input={onCallInput}
        on:blur={onCallBlur}
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
      <div class="grid-input-row">
        <input id="grid" type="text" bind:value={grid} on:input={stripGrid} style="text-transform: uppercase" />
        <button type="button" class="grid-picker-btn" on:click={() => showGridPicker = !showGridPicker} title="Pick from map">🌍</button>
      </div>
      {#if showGridPicker}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div class="grid-picker-overlay" on:click|self={() => showGridPicker = false}>
          <div class="grid-picker-modal">
            <div class="grid-picker-header">
              <span>Grid Square</span>
              <button type="button" class="grid-picker-close" on:click={() => showGridPicker = false}>✕</button>
            </div>
            <GridMap bind:value={grid} on:select={() => showGridPicker = false} />
          </div>
        </div>
      {/if}
    </div>
  </div>

  <div class="form-row">
    <div class="field">
      <label for="pota_park">POTA Park</label>
      <div class="pota-ac">
        <input id="pota_park" type="text" bind:value={pota_park} on:input={onPotaInput} on:focus={onPotaFocus} on:blur={onPotaBlur} on:keydown={onPotaKeydown} style="text-transform: uppercase" autocomplete="off" />
        {#if potaOpen && potaResults.length > 0}
          <ul class="pota-dropdown">
            {#each potaResults as park, i}
              <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
              <li class:highlighted={i === potaHighlight} on:mousedown|preventDefault={() => pickPota(park)}>
                <span class="pota-ref">{park.reference}</span>
                <span class="pota-name">{park.name}</span>
                <span class="pota-loc">{park.location_desc}{park.grid ? " " + park.grid : ""}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
    <div class="field">
      <label for="skcc">SKCC</label>
      <input id="skcc" type="text" bind:value={skcc} on:input={stripSkcc} style="text-transform: uppercase" />
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
      <button type="button" class="btn-clear" on:click={() => { dispatch("navigate", "back"); clearForm(); }}>Cancel</button>
    {/if}
    {#if errorMsg}
      <span class="error">{errorMsg}</span>
    {/if}
  </div>
</form>
{/if}

<section class="log">
  <div class="log-title-row">
    <h2>Log ({displayedContacts.length})</h2>
    {#if !editingId && prevContactCount > 0 && showForm}
      <div class="log-tabs">
        <button class="log-tab" class:active={logFilter === "all"} on:click={() => logFilter = "all"}>All</button>
        <button class="log-tab" class:active={logFilter === "call"} on:click={() => logFilter = "call"}>{call.trim().toUpperCase()}</button>
      </div>
    {/if}
  </div>
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
          {#each displayedContacts as c}
            <tr class="clickable" class:editing={editingId === c.id} title={relativeTime(c.timestamp)} on:click={() => editContact(c)}>
              <td>{formatTimestamp(c.timestamp)}</td>
              <td class="call">{c.call}</td>
              <td>{formatFreq(c.freq)} {#if freqToBand(c.freq)}<span class="band-tag" style="background: {bandColor(freqToBand(c.freq))}; color: {bandTextColor(freqToBand(c.freq))}">{freqToBand(c.freq)}</span>{/if}</td>
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

  .form-heading {
    margin: 0 0 0.5rem 0;
    font-size: 0.95rem;
    color: var(--accent);
  }

  .log-title-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
  }

  .log-title-row h2 {
    margin: 0;
  }

  .log-tabs {
    display: flex;
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
  }

  .log-tab {
    background: transparent;
    color: var(--text-muted);
    border: none;
    border-right: 1px solid var(--border);
    padding: 0.2rem 0.6rem;
    font-family: inherit;
    font-size: 0.75rem;
    font-weight: bold;
    cursor: pointer;
    border-radius: 0;
  }

  .log-tab:last-child {
    border-right: none;
  }

  .log-tab.active {
    background: var(--accent);
    color: var(--bg);
  }

  .log-tab:not(.active):hover {
    background: var(--btn-secondary);
    color: var(--text);
  }

  .prev-contact {
    font-size: 0.8rem;
    font-weight: normal;
    color: var(--text-muted);
  }

  .error {
    color: var(--accent-error);
    font-size: 0.85rem;
    margin-left: 0.5rem;
  }

  .grid-input-row {
    display: flex;
    gap: 0.25rem;
  }

  .grid-input-row input {
    flex: 1;
    min-width: 0;
  }

  .grid-picker-btn {
    background: var(--btn-secondary);
    border: none;
    padding: 0.2rem 0.4rem;
    font-size: 0.85rem;
    border-radius: 3px;
    cursor: pointer;
    line-height: 1;
  }

  .grid-picker-btn:hover {
    background: var(--btn-secondary-hover);
  }

  .grid-picker-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 300;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
  }

  .grid-picker-modal {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem;
    width: 100%;
    max-width: 800px;
    max-height: 90vh;
    overflow-y: auto;
  }

  .grid-picker-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
    color: var(--accent);
    font-weight: bold;
    font-size: 1rem;
  }

  .grid-picker-close {
    background: var(--btn-secondary);
    color: var(--text);
    border: none;
    padding: 0.2rem 0.5rem;
    font-size: 0.9rem;
    border-radius: 3px;
    cursor: pointer;
  }

  .grid-picker-close:hover {
    background: var(--btn-secondary-hover);
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

  .band-tag {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: bold;
    padding: 0.1rem 0.35rem;
    border-radius: 8px;
    margin-left: 0.3rem;
    vertical-align: middle;
  }

  .pota-ac {
    position: relative;
  }

  .pota-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    min-width: 500px;
    max-height: 200px;
    overflow-y: auto;
    background: var(--bg-card);
    border: 1px solid var(--border-input);
    border-top: none;
    border-radius: 0 0 3px 3px;
    margin: 0;
    padding: 0;
    list-style: none;
    z-index: 100;
  }

  .pota-dropdown li {
    padding: 0.3rem 0.5rem;
    cursor: pointer;
    font-size: 0.8rem;
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
    line-height: 1.4;
  }

  .pota-dropdown li:hover,
  .pota-dropdown li.highlighted {
    background: var(--accent);
    color: var(--bg);
  }

  .pota-ref {
    color: var(--accent-vfo);
    font-weight: bold;
    flex-shrink: 0;
  }

  .pota-dropdown li:hover .pota-ref,
  .pota-dropdown li.highlighted .pota-ref {
    color: var(--bg);
  }

  .pota-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .pota-loc {
    color: var(--text-dim);
    font-size: 0.75rem;
    flex-shrink: 0;
    margin-left: auto;
  }

  .pota-dropdown li:hover .pota-loc,
  .pota-dropdown li.highlighted .pota-loc {
    color: var(--bg);
  }
</style>
