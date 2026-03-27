<script>
  import { onMount } from "svelte";
  import Autocomplete from "./Autocomplete.svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";

  let importing = false;
  let message = "";
  let messageType = "";

  // Comment template
  const TEMPLATE_FIELDS = [
    { field: "pota_park", label: "POTA" },
    { field: "skcc", label: "SKCC" },
    { field: "grid", label: "Grid" },
    { field: "call", label: "Call" },
    { field: "freq", label: "Freq" },
    { field: "mode", label: "Mode" },
    { field: "rst_sent", label: "RST Sent" },
    { field: "rst_recv", label: "RST Recv" },
    { field: "name", label: "Name" },
    { field: "qth", label: "QTH" },
    { field: "state", label: "State" },
    { field: "country", label: "Country" },
  ];

  let commentTemplate = [];
  let commentSeparator = "|";
  let templateExpanded = false;
  let addField = "";
  let dragIndex = null;
  let dropIndex = null;
  let templateSaveTimer = null;

  $: availableFields = TEMPLATE_FIELDS.filter(
    f => !commentTemplate.some(t => t.field === f.field)
  );

  async function loadCommentTemplate() {
    try {
      const [tplRes, sepRes] = await Promise.all([
        fetch("/api/settings/comment_template"),
        fetch("/api/settings/comment_separator"),
      ]);
      if (tplRes.ok) {
        const data = await tplRes.json();
        if (data.value) {
          try { commentTemplate = JSON.parse(data.value); } catch { commentTemplate = []; }
        }
      }
      if (sepRes.ok) {
        const data = await sepRes.json();
        if (data.value) commentSeparator = data.value;
      }
    } catch { /* ignore */ }
  }

  async function saveCommentTemplate() {
    clearTimeout(templateSaveTimer);
    templateSaveTimer = setTimeout(async () => {
      try {
        await Promise.all([
          fetch("/api/settings/comment_template", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: JSON.stringify(commentTemplate) }),
          }),
          fetch("/api/settings/comment_separator", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: commentSeparator }),
          }),
        ]);
      } catch { /* ignore */ }
    }, 300);
  }

  function addTemplateField() {
    if (!addField) return;
    const def = TEMPLATE_FIELDS.find(f => f.field === addField);
    if (def) {
      commentTemplate = [...commentTemplate, { field: def.field, label: def.label }];
      addField = "";
      saveCommentTemplate();
    }
  }

  function removeTemplateField(index) {
    commentTemplate = commentTemplate.filter((_, i) => i !== index);
    saveCommentTemplate();
  }

  function handleDragStart(index) {
    dragIndex = index;
  }

  function handleDragOver(event, index) {
    event.preventDefault();
    dropIndex = index;
  }

  function handleDrop(index) {
    if (dragIndex !== null && dragIndex !== index) {
      const items = [...commentTemplate];
      const [moved] = items.splice(dragIndex, 1);
      items.splice(index, 0, moved);
      commentTemplate = items;
      saveCommentTemplate();
    }
    dragIndex = null;
    dropIndex = null;
  }

  function handleDragEnd() {
    dragIndex = null;
    dropIndex = null;
  }

  // Country autocomplete
  let countries = [];
  $: countryItems = countries.map(c => ({ name: c.name, aliases: c.aliases || [], display: `${c.code} — ${c.name}` }));

  async function fetchCountries() {
    try {
      const res = await fetch("/api/geo/countries");
      if (res.ok) countries = await res.json();
    } catch { /* ignore */ }
  }

  function normalizeCountry() {
    if (!countryFilter || !countries.length) return;
    const upper = countryFilter.toUpperCase().trim();
    if (countries.some(c => c.name === countryFilter)) return;
    const byCode = countries.find(c => c.code.toUpperCase() === upper);
    if (byCode) { countryFilter = byCode.name; return; }
    const byAlias = countries.find(c => (c.aliases || []).some(a => a.toUpperCase() === upper));
    if (byAlias) { countryFilter = byAlias.name; return; }
  }

  onMount(() => {
    fetchCountries();
    loadCommentTemplate();
  });

  // Filter state
  let dateFrom = "";
  let dateTo = "";
  let commentFilter = "";
  let skccValidated = false;
  let countryFilter = "";
  let modeFilter = "";
  let bandFilter = "";
  let exportTitle = "";

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

  function renderComment(c, template, separator) {
    if (!template.length) return c.comments || c.notes || "";
    const fieldMap = {
      call: c.call, freq: c.freq, mode: c.mode,
      rst_sent: c.rst_sent, rst_recv: c.rst_recv,
      name: c.name, qth: c.qth, state: c.state,
      country: c.country, grid: c.grid,
      pota_park: c.pota_park, skcc: c.skcc,
    };
    const parts = [];
    for (const entry of template) {
      const val = fieldMap[entry.field];
      if (val) parts.push(`${entry.label}: ${val}`);
    }
    if ((c.comments || "").trim()) parts.push(c.comments.trim());
    const sep = ` ${separator.trim()} `;
    return parts.join(sep);
  }

  function exportAdif() {
    const params = buildParams();
    if (exportTitle.trim()) params.set("title", exportTitle.trim());
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
  <div class="export-layout">
    <div class="export-form">
      <h2>Export</h2>

      <div class="title-row">
        <label>
          Title
          <input type="text" bind:value={exportTitle} placeholder="optional — included in filename" />
        </label>
      </div>

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
            <Autocomplete bind:value={countryFilter} items={countryItems} on:blur={normalizeCountry} />
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

      <div class="comment-template-section">
        <button class="toggle-btn" on:click={() => templateExpanded = !templateExpanded}>
          {templateExpanded ? "▾" : "▸"} Comment Template {#if commentTemplate.length > 0}<span class="template-count">({commentTemplate.length} field{commentTemplate.length !== 1 ? "s" : ""})</span>{/if}
        </button>

        {#if templateExpanded}
          <div class="template-body">
            <p class="help-text">Selected fields are prepended to COMMENT in exported ADIF. Empty fields are skipped.</p>

            {#if commentTemplate.length > 0}
              <div class="template-list">
                {#each commentTemplate as entry, i}
                  <div
                    class="template-row"
                    class:drag-over={dropIndex === i && dragIndex !== i}
                    draggable="true"
                    on:dragstart={() => handleDragStart(i)}
                    on:dragover={(e) => handleDragOver(e, i)}
                    on:drop={() => handleDrop(i)}
                    on:dragend={handleDragEnd}
                  >
                    <span class="drag-handle" title="Drag to reorder">⠿</span>
                    <span class="field-name">{entry.field}</span>
                    <input
                      type="text"
                      class="label-input"
                      bind:value={entry.label}
                      on:input={saveCommentTemplate}
                      placeholder="Label"
                    />
                    <button class="remove-btn" on:click={() => removeTemplateField(i)} title="Remove">×</button>
                  </div>
                {/each}
              </div>
            {/if}

            <div class="template-add-row">
              <select bind:value={addField} on:change={addTemplateField}>
                <option value="">Add field…</option>
                {#each availableFields as f}
                  <option value={f.field}>{f.label} ({f.field})</option>
                {/each}
              </select>
            </div>

            <div class="separator-row">
              <label>
                Separator
                <input
                  type="text"
                  class="separator-input"
                  bind:value={commentSeparator}
                  on:input={saveCommentTemplate}
                  placeholder="|"
                />
              </label>
              {#if commentTemplate.length > 0}
                <span class="preview-example">
                  Preview: {commentTemplate.map(e => `${e.label}: …`).join(` ${commentSeparator.trim()} `)}{ commentTemplate.length > 0 ? ` ${commentSeparator.trim()} ` : "" }your comment
                </span>
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <button on:click={exportAdif}>Download ADIF{preview ? ` (${preview.included})` : ""}</button>
    </div>

    {#if preview && preview.contacts.length > 0}
      <div class="export-preview">
        <h2>Preview</h2>
        <div class="preview-table-wrap">
          <table class="preview-table">
            <thead>
              <tr>
                <th class="col-ts">Timestamp</th>
                <th class="col-call">Call</th>
                <th class="col-freq">Freq</th>
                <th class="col-mode">Mode</th>
                <th class="col-country">Country</th>
                <th class="col-comments">Comments</th>
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
                  <td class="truncate">{renderComment(c, commentTemplate, commentSeparator)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {/if}
  </div>

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
    width: 100%;
  }

  .export-layout {
    display: flex;
    gap: 1.5rem;
    align-items: flex-start;
  }

  .export-form {
    flex: 0 0 auto;
    min-width: 0;
  }

  .export-preview {
    flex: 1 1 0;
    min-width: 0;
  }

  .export-preview .preview-table-wrap {
    max-height: calc(100vh - 10rem);
  }

  @media (max-width: 900px) {
    .export-layout {
      flex-direction: column;
    }

    .export-form {
      width: 100%;
    }

    .export-preview {
      width: 100%;
    }

    .export-preview .preview-table-wrap {
      max-height: 400px;
    }
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

  .title-row {
    margin-bottom: 0.75rem;
  }

  .title-row label {
    display: flex;
    flex-direction: column;
    font-size: 0.8rem;
    color: var(--text-muted);
    gap: 0.2rem;
  }

  .title-row input {
    background: var(--bg-input, var(--bg));
    color: var(--text);
    border: 1px solid var(--border, #555);
    padding: 0.35rem 0.5rem;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
    max-width: 400px;
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
    table-layout: fixed;
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
    overflow: hidden;
    resize: horizontal;
  }

  .preview-table td {
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid var(--border-dim, rgba(255,255,255,0.05));
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .preview-table .call {
    font-weight: bold;
    color: var(--accent);
  }

  .preview-table .col-ts { width: 11rem; }
  .preview-table .col-call { width: 6rem; }
  .preview-table .col-freq { width: 9rem; }
  .preview-table .col-mode { width: 3.5rem; }
  .preview-table .col-country { width: 6rem; }
  .preview-table .col-comments { width: auto; }

  .preview-table .truncate {
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

  .comment-template-section {
    margin-bottom: 1rem;
  }

  .toggle-btn {
    background: none;
    color: var(--text-muted);
    border: none;
    padding: 0.3rem 0;
    font-size: 0.85rem;
    font-weight: normal;
    cursor: pointer;
    margin-bottom: 0;
  }

  .toggle-btn:hover {
    background: none;
    color: var(--text);
  }

  .template-count {
    color: var(--accent);
    font-size: 0.8rem;
  }

  .template-body {
    border: 1px solid var(--border, #555);
    border-radius: 3px;
    padding: 0.75rem;
    margin-top: 0.25rem;
  }

  .help-text {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin: 0 0 0.5rem 0;
  }

  .template-list {
    margin-bottom: 0.5rem;
  }

  .template-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.4rem;
    border: 1px solid transparent;
    border-radius: 3px;
    margin-bottom: 0.2rem;
    background: var(--bg);
  }

  .template-row:hover {
    border-color: var(--border, #555);
  }

  .template-row.drag-over {
    border-color: var(--accent);
    background: var(--bg-header, var(--bg));
  }

  .drag-handle {
    cursor: grab;
    color: var(--text-muted);
    font-size: 1rem;
    user-select: none;
  }

  .field-name {
    color: var(--text-muted);
    font-size: 0.75rem;
    min-width: 70px;
  }

  .label-input {
    background: var(--bg-input, var(--bg));
    color: var(--text);
    border: 1px solid var(--border, #555);
    padding: 0.2rem 0.4rem;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 3px;
    width: 100px;
  }

  .remove-btn {
    background: none;
    color: var(--text-muted);
    border: none;
    padding: 0.1rem 0.4rem;
    font-size: 1rem;
    cursor: pointer;
    margin: 0;
    line-height: 1;
  }

  .remove-btn:hover {
    color: var(--accent-error);
    background: none;
  }

  .template-add-row {
    margin-bottom: 0.5rem;
  }

  .template-add-row select {
    background: var(--bg-input, var(--bg));
    color: var(--text);
    border: 1px solid var(--border, #555);
    padding: 0.3rem 0.5rem;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 3px;
  }

  .separator-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .separator-row label {
    display: flex;
    flex-direction: column;
    font-size: 0.8rem;
    color: var(--text-muted);
    gap: 0.2rem;
  }

  .separator-input {
    background: var(--bg-input, var(--bg));
    color: var(--text);
    border: 1px solid var(--border, #555);
    padding: 0.2rem 0.4rem;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 3px;
    width: 50px;
    text-align: center;
  }

  .preview-example {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-style: italic;
    padding-top: 0.8rem;
  }
</style>
