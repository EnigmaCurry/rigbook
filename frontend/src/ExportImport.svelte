<script>
  import { bandColor, bandTextColor } from "./bandColors.js";

  let importing = false;
  let message = "";
  let messageType = "";

  // Filter state
  let dateFrom = "";
  let dateTo = "";
  let commentFilter = "";
  let skccValidated = false;
  let countryFilter = "";
  let modeFilter = "";
  let bandFilter = "";

  // Preview state
  let preview = null;
  let loadingPreview = false;
  let debounceTimer = null;

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

  function buildParams() {
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (commentFilter) params.set("comment", commentFilter);
    if (skccValidated) params.set("skcc_validated", "true");
    if (countryFilter) params.set("country", countryFilter);
    if (modeFilter) params.set("mode", modeFilter);
    if (bandFilter) params.set("band", bandFilter);
    return params;
  }

  async function fetchPreview() {
    loadingPreview = true;
    try {
      const params = buildParams();
      const qs = params.toString();
      const url = "/api/adif/preview" + (qs ? "?" + qs : "");
      const res = await fetch(url);
      if (res.ok) {
        preview = await res.json();
      }
    } catch {
      // ignore fetch errors
    }
    loadingPreview = false;
  }

  function schedulePreview() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fetchPreview, 300);
  }

  // Trigger on any filter change
  $: dateFrom, dateTo, commentFilter, skccValidated, countryFilter, modeFilter, bandFilter, schedulePreview();

  function exportAdif() {
    const params = buildParams();
    const qs = params.toString();
    window.location.href = "/api/adif/export" + (qs ? "?" + qs : "");
  }

  async function importAdif(event) {
    const file = event.target.files[0];
    if (!file) return;
    importing = true;
    message = "";
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/adif/import", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        message = `Imported ${data.imported} contacts.${data.duplicates ? ` ${data.duplicates} duplicates skipped.` : ""}${data.skipped ? ` ${data.skipped} invalid skipped.` : ""}`;
        messageType = "success";
        fetchPreview();
      } else {
        const data = await res.json().catch(() => null);
        message = data?.detail || `Error: ${res.status} ${res.statusText}`;
        messageType = "error";
      }
    } catch (e) {
      message = `Network error: ${e.message}`;
      messageType = "error";
    }
    importing = false;
    event.target.value = "";
  }
</script>

<div class="export-import">
  <h2>Export</h2>

  <div class="filters">
    <div class="filter-row">
      <label>
        Date from
        <input type="date" bind:value={dateFrom} />
      </label>
      <label>
        Date to
        <input type="date" bind:value={dateTo} />
      </label>
    </div>
    <div class="filter-row">
      <label>
        Comment / Notes
        <input type="text" bind:value={commentFilter} placeholder="substring search" />
      </label>
      <label>
        Country
        <input type="text" bind:value={countryFilter} placeholder="exact match" />
      </label>
    </div>
    <div class="filter-row">
      <label>
        Mode
        <input type="text" bind:value={modeFilter} placeholder="e.g. CW, SSB" />
      </label>
      <label>
        Band
        <select bind:value={bandFilter}>
          <option value="">All</option>
          {#each BANDS as b}
            <option value={b.name}>{b.name}</option>
          {/each}
        </select>
      </label>
      <label class="checkbox-label">
        <input type="checkbox" bind:checked={skccValidated} />
        SKCC Validated
      </label>
    </div>
  </div>

  {#if preview}
    <div class="stats-bar">
      Showing {preview.included} of {preview.total} contacts ({preview.excluded} excluded)
    </div>
  {/if}

  <button on:click={exportAdif}>Download ADIF{preview ? ` (${preview.included})` : ""}</button>

  {#if preview && preview.contacts.length > 0}
    <div class="preview-table-wrap">
      <table class="preview-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Callsign</th>
            <th>Freq</th>
            <th>Mode</th>
            <th>Country</th>
            <th>Comments</th>
          </tr>
        </thead>
        <tbody>
          {#each preview.contacts as c}
            <tr>
              <td>{formatTimestamp(c.timestamp)}</td>
              <td class="call">{c.call}</td>
              <td class="freq-cell">{formatFreq(c.freq)} {#if freqToBand(c.freq)}<span class="band-tag" style="background: {bandColor(freqToBand(c.freq))}; color: {bandTextColor(freqToBand(c.freq))}">{freqToBand(c.freq)}</span>{/if}</td>
              <td>{c.mode || ""}</td>
              <td>{c.country || ""}</td>
              <td class="truncate">{c.comments || c.notes || ""}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  <h2>Import</h2>
  <p>Import contacts from an ADIF (.adi) file. Duplicates (same callsign + timestamp) are automatically skipped.</p>
  <label class="file-label">
    <input type="file" accept=".adi,.adif,.ADI,.ADIF" on:change={importAdif} disabled={importing} />
    {importing ? "Importing..." : "Choose ADIF File"}
  </label>

  {#if message}
    <p class="message" class:error={messageType === "error"}>{message}</p>
  {/if}
</div>

<style>
  .export-import {
    max-width: 900px;
  }

  h2 {
    color: var(--accent);
    font-size: 1.2rem;
    margin: 1.5rem 0 0.5rem 0;
  }

  h2:first-child {
    margin-top: 0;
  }

  p {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin: 0 0 0.75rem 0;
  }

  .filters {
    margin-bottom: 1rem;
  }

  .filter-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
    align-items: end;
  }

  .filter-row label {
    display: flex;
    flex-direction: column;
    font-size: 0.8rem;
    color: var(--text-muted);
    gap: 0.2rem;
  }

  .filter-row input[type="date"],
  .filter-row input[type="text"],
  .filter-row select {
    background: var(--bg-input, var(--bg));
    color: var(--text);
    border: 1px solid var(--border, #555);
    padding: 0.35rem 0.5rem;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
  }

  .checkbox-label {
    flex-direction: row !important;
    align-items: center !important;
    gap: 0.4rem !important;
    padding-bottom: 0.35rem;
  }

  .checkbox-label input[type="checkbox"] {
    margin: 0;
  }

  .stats-bar {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin-bottom: 0.75rem;
    font-weight: bold;
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
    margin-bottom: 1rem;
  }

  button:hover {
    background: var(--accent-hover);
  }

  .preview-table-wrap {
    max-height: 400px;
    overflow-y: auto;
    margin-bottom: 1.5rem;
    border: 1px solid var(--border, #555);
    border-radius: 3px;
  }

  .preview-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }

  .preview-table th {
    position: sticky;
    top: 0;
    background: var(--bg-header, var(--bg));
    text-align: left;
    padding: 0.4rem 0.5rem;
    color: var(--accent);
    border-bottom: 1px solid var(--border, #555);
    font-size: 0.75rem;
    text-transform: uppercase;
  }

  .preview-table td {
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid var(--border-dim, rgba(255,255,255,0.05));
    white-space: nowrap;
  }

  .preview-table .call {
    font-weight: bold;
    color: var(--accent);
  }

  .preview-table .truncate {
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .band-tag {
    display: inline-block;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    font-size: 0.7rem;
    font-weight: bold;
    margin-left: 0.3rem;
    vertical-align: middle;
  }

  .freq-cell {
    white-space: nowrap;
  }

  .file-label {
    display: inline-block;
    background: var(--accent);
    color: var(--bg);
    padding: 0.5rem 1.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: bold;
    border-radius: 3px;
    cursor: pointer;
  }

  .file-label:hover {
    background: var(--accent-hover);
  }

  .file-label input[type="file"] {
    display: none;
  }

  .message {
    color: var(--accent);
    font-weight: bold;
    margin-top: 1rem;
  }

  .message.error {
    color: var(--accent-error);
  }
</style>
