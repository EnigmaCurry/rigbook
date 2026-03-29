<script>
  import { onMount } from "svelte";
  import Autocomplete from "./Autocomplete.svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";

  // Tab state
  let activeTab = "import";
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
      // Re-fetch previews with updated template
      fetchExportPreview();
      if (importFile) fetchImportPreview();
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

  function handleDragStart(index) { dragIndex = index; }
  function handleDragOver(event, index) { event.preventDefault(); dropIndex = index; }
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
  function handleDragEnd() { dragIndex = null; dropIndex = null; }

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

  // Export filter state
  let dateFrom = "";
  let dateTo = "";
  let commentFilter = "";
  let skccValidated = false;
  let countryFilter = "";
  let modeFilter = "";
  let bandFilter = "";
  let exportTitle = "";

  // Export preview state
  let exportPreview = null;
  let debounceTimer = null;

  // Import state
  let importFile = null;
  let importFileName = "";
  let importPreview = null;
  let loadingImport = false;

  // Import filter
  let importFilter = "all";

  // Unified preview based on active tab
  $: currentPreview = activeTab === "export" ? exportPreview : importPreview;
  $: warningCount = importPreview ? (importPreview.contacts || []).filter(c => c.warnings && c.warnings.length > 0).length : 0;
  $: fixedCount = importPreview ? (importPreview.contacts || []).filter(c => c._fixed).length : 0;
  $: mergedCount = importPreview ? (importPreview.contacts || []).filter(c => c.merged).length : 0;

  function parseSegmentValue(seg, label) {
    const s = seg.trim();
    for (const fmt of [`${label}: `]) {
      if (s.startsWith(fmt)) {
        const rest = s.slice(fmt.length);
        const parts = rest.split(/\s+/);
        if (!parts.length || !parts[0]) return null;
        return { value: parts[0], remainder: parts.slice(1).join(" ") };
      }
    }
    return null;
  }

  function segmentMatches(seg, label, value, field) {
    const parsed = parseSegmentValue(seg, label);
    if (!parsed) return false;
    if (parsed.value === value) return true;
    if (field === "freq") {
      try { if (Math.abs(parseFloat(parsed.value) - parseFloat(value) * 1000) < 0.1) return true; } catch {}
    }
    return false;
  }

  function segmentMatchRemainder(seg, label, value, field) {
    const parsed = parseSegmentValue(seg, label);
    if (!parsed) return null;
    if (parsed.value === value) return parsed.remainder;
    if (field === "freq") {
      try { if (Math.abs(parseFloat(parsed.value) - parseFloat(value) * 1000) < 0.1) return parsed.remainder; } catch {}
    }
    return null;
  }

  function stripCommentClient(contact) {
    const original = contact.original_comment || "";
    if (!original || !commentTemplate.length) {
      contact.comments = original;
      return;
    }
    const sep = commentSeparator.trim();
    const padded = ` ${sep} `;
    const fieldMap = {
      call: contact.call, freq: contact.freq, mode: contact.mode,
      rst_sent: contact.rst_sent, rst_recv: contact.rst_recv,
      name: contact.name, qth: contact.qth, state: contact.state,
      country: contact.country, grid: contact.grid,
      pota_park: contact.pota_park, skcc: contact.skcc,
    };
    const expected = [];
    for (const entry of commentTemplate) {
      const val = fieldMap[entry.field];
      if (val) expected.push({ label: entry.label, val, field: entry.field });
    }
    // Check if entire comment matches a single expected segment
    for (const e of expected) {
      const rem = segmentMatchRemainder(original, e.label, e.val, e.field);
      if (rem !== null) {
        contact.comments = rem.trim();
        return;
      }
    }
    if (!original.includes(padded)) {
      contact.comments = original;
      return;
    }
    const parts = original.split(padded);
    let stripCount = 0;
    const remainders = [];
    for (let i = 0; i < parts.length && i < expected.length; i++) {
      const rem = segmentMatchRemainder(parts[i], expected[i].label, expected[i].val, expected[i].field);
      if (rem !== null) {
        stripCount++;
        if (rem.trim()) remainders.push(rem.trim());
      } else {
        break;
      }
    }
    if (stripCount > 0) {
      const kept = [...remainders, ...parts.slice(stripCount)];
      contact.comments = kept.length ? kept.join(padded) : "";
    } else {
      contact.comments = original;
    }
  }

  function applyWarningFix(contact, warning, useValue) {
    const field = warning.field;
    contact[field] = useValue;
    // Remove this warning
    contact.warnings = contact.warnings.filter(w => w !== warning);
    // Mark as fixed once all warnings are resolved
    if (!contact.warnings.length) contact._fixed = true;
    // Re-strip comment with updated field values
    stripCommentClient(contact);
    // Trigger reactivity
    if (importPreview) importPreview = { ...importPreview };
    // Switch to fixed view when no warnings remain
    const remaining = (importPreview?.contacts || []).filter(c => c.warnings && c.warnings.length > 0).length;
    if (remaining === 0) importFilter = "fixed";
  }
  $: displayContacts = currentPreview && currentPreview.contacts
    ? (activeTab === "import" && importFilter === "warnings"
      ? currentPreview.contacts.filter(c => c.warnings && c.warnings.length > 0)
      : activeTab === "import" && importFilter === "fixed"
        ? currentPreview.contacts.filter(c => c._fixed)
        : activeTab === "import" && importFilter === "merged"
          ? currentPreview.contacts.filter(c => c.merged)
          : currentPreview.contacts)
    : [];

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
    } catch { return ts; }
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

  async function fetchExportPreview() {
    try {
      const params = buildParams();
      const qs = params.toString();
      const url = "/api/adif/preview" + (qs ? "?" + qs : "");
      const res = await fetch(url);
      if (res.ok) exportPreview = await res.json();
    } catch { /* ignore */ }
  }

  function scheduleExportPreview() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fetchExportPreview, 300);
  }

  $: dateFrom, dateTo, commentFilter, skccValidated, countryFilter, modeFilter, bandFilter, scheduleExportPreview();

  // Column resize
  let resizeCol = null;
  let resizeStartX = 0;
  let resizeStartW = 0;

  function startResize(e, colIndex) {
    e.preventDefault();
    const th = e.target.parentElement;
    resizeCol = th;
    resizeStartX = e.clientX;
    resizeStartW = th.offsetWidth;
    window.addEventListener("mousemove", onResize);
    window.addEventListener("mouseup", stopResize);
  }

  function onResize(e) {
    if (!resizeCol) return;
    const diff = e.clientX - resizeStartX;
    const newW = Math.max(30, resizeStartW + diff);
    resizeCol.style.width = newW + "px";
  }

  function stopResize() {
    resizeCol = null;
    window.removeEventListener("mousemove", onResize);
    window.removeEventListener("mouseup", stopResize);
  }

  let expandedRow = null;
  let headerExpanded = false;

  function toggleRow(index) {
    expandedRow = expandedRow === index ? null : index;
  }

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

  async function fetchImportPreview() {
    if (!importFile) return;
    loadingImport = true;
    try {
      const formData = new FormData();
      formData.append("file", importFile);
      const res = await fetch("/api/adif/import/preview", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        importPreview = await res.json();
      } else {
        const data = await res.json().catch(() => null);
        message = data?.detail || `Error: ${res.status} ${res.statusText}`;
        messageType = "error";
        importPreview = null;
      }
    } catch (e) {
      message = `Network error: ${e.message}`;
      messageType = "error";
      importPreview = null;
    }
    loadingImport = false;
  }

  async function stageImportFile(event) {
    const file = event.target.files[0];
    if (!file) return;
    importFile = file;
    importFileName = file.name;
    message = "";
    await fetchImportPreview();
  }

  let suggesting = false;

  async function suggestTemplate() {
    if (!importFile) return;
    suggesting = true;
    try {
      const formData = new FormData();
      formData.append("file", importFile);
      const res = await fetch("/api/adif/import/suggest-template", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.fields && data.fields.length > 0) {
          commentTemplate = data.fields;
          commentSeparator = data.separator || "|";
          saveCommentTemplate();
        } else {
          message = "No template pattern detected in comments.";
          messageType = "error";
        }
      }
    } catch { /* ignore */ }
    suggesting = false;
  }

  function cancelImport() {
    importFile = null;
    importFileName = "";
    importPreview = null;
    importFilter = "all";
    message = "";
    expandedRow = null;
  }

  async function executeImport() {
    if (!importPreview || !importPreview.contacts) return;
    importing = true;
    message = "";
    try {
      const res = await fetch("/api/adif/import/confirmed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(importPreview.contacts),
      });
      if (res.ok) {
        const data = await res.json();
        message = `Imported ${data.imported} contacts.${data.duplicates ? ` ${data.duplicates} duplicates skipped.` : ""}${data.skipped ? ` ${data.skipped} invalid skipped.` : ""}`;
        messageType = "success";
        importFile = null;
        importFileName = "";
        importPreview = null;
        fetchExportPreview();
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
  }
</script>

<div class="export-import">
  <div class="tab-bar">
    <button class="tab" class:active={activeTab === "import"} on:click={() => { activeTab = "import"; message = ""; }}>Import</button>
    <button class="tab" class:active={activeTab === "export"} on:click={() => { activeTab = "export"; message = ""; }}>Export</button>
  </div>

  <div class="main-layout">
    <div class="sidebar">
      {#if activeTab === "export"}
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
      {:else}
        <p>Select an ADIF file to preview before importing.</p>
        <label class="file-label">
          <input type="file" accept=".adi,.adif,.ADI,.ADIF" on:change={stageImportFile} disabled={importing || loadingImport} />
          {loadingImport ? "Loading..." : "Choose ADIF File"}
        </label>
        {#if importFileName}
          <p class="file-name">{importFileName}</p>
        {/if}
      {/if}

      <div class="comment-template-section">
        <div class="template-header">
          <h3>Comment Template</h3>
          {#if activeTab === "import" && (importFile || importPreview)}
            <button class="suggest-btn" on:click={suggestTemplate} disabled={suggesting}>
              {suggesting ? "Analyzing..." : "Suggest from file"}
            </button>
          {/if}
        </div>
        <p class="help-text">Fields prepended to COMMENT on export, stripped on import.</p>

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

        <div class="template-controls">
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
          </div>
        </div>

        {#if commentTemplate.length > 0}
          <span class="preview-example">
            {commentTemplate.map(e => `${e.label}: …`).join(` ${commentSeparator.trim()} `)}{ commentTemplate.length > 0 ? ` ${commentSeparator.trim()} ` : "" }comment
          </span>
          {#if currentPreview && currentPreview.template_matches !== undefined}
            {#if currentPreview.template_matches > 0}
              <span class="template-match-count">
                {currentPreview.template_matches} of {currentPreview.contacts ? currentPreview.contacts.length : 0} {activeTab === "export" ? "comments modified" : "comments stripped"}
              </span>
            {:else if currentPreview.contacts && currentPreview.contacts.length > 0}
              <span class="template-no-match">No matches — comments {activeTab === "export" ? "exported" : "imported"} as-is. Check that the separator matches the comment format.</span>
            {/if}
          {/if}
        {:else if currentPreview && currentPreview.contacts && currentPreview.contacts.length > 0}
          <span class="template-no-match">No template configured — comments {activeTab === "export" ? "exported" : "imported"} as-is.</span>
        {/if}
      </div>

      {#if message}
        <p class="message" class:error={messageType === "error"}>{message}</p>
      {/if}
    </div>

    <div class="preview-pane">
      {#if currentPreview && (currentPreview.header_raw || currentPreview.header_adif || (currentPreview.header && Object.keys(currentPreview.header).length > 0))}
        <div class="adif-header-bar" on:click={() => headerExpanded = !headerExpanded}>
          <span class="adif-header-summary">
            {#if currentPreview.header && currentPreview.header.PROGRAMID}
              <strong>{currentPreview.header.PROGRAMID}</strong>{#if currentPreview.header.PROGRAMVERSION} v{currentPreview.header.PROGRAMVERSION}{/if}
            {:else if currentPreview.header_raw}
              <strong>{currentPreview.header_raw.split('\n')[0]}</strong>
            {:else}
              <strong>ADIF</strong>
            {/if}
            {#if currentPreview.header && currentPreview.header.ADIF_VER}
              <span class="adif-ver">ADIF {currentPreview.header.ADIF_VER}</span>
            {/if}
            <span class="expand-hint">{headerExpanded ? "▾" : "▸"}</span>
          </span>
        </div>
        {#if headerExpanded}
          <div class="adif-header-detail">
            {#if currentPreview.header_raw}
              <pre class="adif-header-raw">{currentPreview.header_raw}</pre>
            {:else if currentPreview.header_adif}
              <code class="adif-header-raw">{currentPreview.header_adif}</code>
            {:else}
              <div class="adif-header-fields">
                {#each Object.entries(currentPreview.header) as [key, val]}
                  <span class="adif-field"><strong>{key}:</strong> {val}</span>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      {/if}
      {#if activeTab === "import" && importPreview}
        <div class="filter-tabs">
          <button class="filter-tab" class:active={importFilter === "all"} on:click={() => importFilter = "all"}>All ({importPreview.contacts.length})</button>
          {#if warningCount > 0}
            <button class="filter-tab error-tab" class:active={importFilter === "warnings"} on:click={() => importFilter = "warnings"}>Errors ({warningCount})</button>
          {/if}
          {#if fixedCount > 0}
            <button class="filter-tab fixed-tab" class:active={importFilter === "fixed"} on:click={() => importFilter = "fixed"}>Fixed ({fixedCount})</button>
          {/if}
          {#if mergedCount > 0}
            <button class="filter-tab merged-tab" class:active={importFilter === "merged"} on:click={() => importFilter = "merged"}>Merged ({mergedCount})</button>
          {/if}
        </div>
      {/if}
      {#if displayContacts.length > 0}
        <div class="preview-table-wrap">
          <table class="preview-table">
            <thead>
              <tr>
                <th class="col-compact">UTC<span class="resize-handle" on:mousedown={e => startResize(e, 0)}></span></th>
                <th class="col-compact">Call<span class="resize-handle" on:mousedown={e => startResize(e, 1)}></span></th>
                <th class="col-comment">Comments<span class="resize-handle" on:mousedown={e => startResize(e, 2)}></span></th>
                <th class="col-freq">Freq<span class="resize-handle" on:mousedown={e => startResize(e, 3)}></span></th>
                <th class="col-compact">Mode<span class="resize-handle" on:mousedown={e => startResize(e, 4)}></span></th>
                <th class="col-compact">RST S<span class="resize-handle" on:mousedown={e => startResize(e, 5)}></span></th>
                <th class="col-compact">RST R<span class="resize-handle" on:mousedown={e => startResize(e, 6)}></span></th>
                <th class="col-flex">Name<span class="resize-handle" on:mousedown={e => startResize(e, 7)}></span></th>
                <th class="col-compact">POTA<span class="resize-handle" on:mousedown={e => startResize(e, 8)}></span></th>
                <th class="col-compact">Grid<span class="resize-handle" on:mousedown={e => startResize(e, 9)}></span></th>
                <th class="col-flex">QTH<span class="resize-handle" on:mousedown={e => startResize(e, 10)}></span></th>
                <th class="col-compact">State<span class="resize-handle" on:mousedown={e => startResize(e, 11)}></span></th>
                <th class="col-compact">Country<span class="resize-handle" on:mousedown={e => startResize(e, 12)}></span></th>
                <th class="col-compact">SKCC<span class="resize-handle" on:mousedown={e => startResize(e, 13)}></span></th>
                <th class="col-compact">Exch<span class="resize-handle" on:mousedown={e => startResize(e, 14)}></span></th>
                <th class="col-flex">Notes</th>
              </tr>
            </thead>
            <tbody>
              {#each displayContacts as c, i}
                <tr class="clickable" class:expanded={expandedRow === i} class:has-warning={c.warnings && c.warnings.length > 0} class:has-merged={c.merged} on:click={() => toggleRow(i)}>
                  <td>{formatTimestamp(c.timestamp)}</td>
                  <td class="call">{c.call}</td>
                  <td class="truncate">{#if activeTab === "import" && c.original_comment && c.original_comment !== (c.comments || "")}<span class="comment-modified" title="Original: {c.original_comment}">* </span>{/if}{activeTab === "export" ? renderComment(c, commentTemplate, commentSeparator) : (c.comments || "")}</td>
                  <td class="freq-cell">{formatFreq(c.freq)} {#if freqToBand(c.freq)}<span class="band-tag" style="background: {bandColor(freqToBand(c.freq))}; color: {bandTextColor(freqToBand(c.freq))}">{freqToBand(c.freq)}</span>{/if}</td>
                  <td>{c.mode || ""}</td>
                  <td>{c.rst_sent || ""}</td>
                  <td>{c.rst_recv || ""}</td>
                  <td>{c.name || ""}</td>
                  <td>{c.pota_park || ""}</td>
                  <td>{c.grid || ""}</td>
                  <td>{c.qth || ""}</td>
                  <td>{c.state || ""}</td>
                  <td>{c.country || ""}</td>
                  <td>{c.skcc || ""}</td>
                  <td>{c.skcc_exch ? "Y" : ""}</td>
                  <td class="truncate">{c.notes || ""}</td>
                </tr>
                {#if expandedRow === i}
                  <tr class="detail-row">
                    <td colspan="16">
                      {#if c.warnings && c.warnings.length > 0}
                        <div class="warning-list">
                          {#each c.warnings as w}
                            <div class="warning-item">
                              <div class="warning-message">{w.is_merge_conflict ? "🔀" : "⚠"} {w.message}</div>
                              <div class="warning-actions">
                                <span class="warning-label">Use:</span>
                                <button class="warning-fix-btn" on:click|stopPropagation={() => applyWarningFix(c, w, w.comment_val)} title="Use value from comment">
                                  "{w.comment_val}" <span class="fix-source">(comment)</span>
                                </button>
                                {#if w.field_val}
                                  <button class="warning-fix-btn" on:click|stopPropagation={() => applyWarningFix(c, w, w.field_val)} title="Use value from field">
                                    "{w.field_val}" <span class="fix-source">(field)</span>
                                  </button>
                                {/if}
                                <input
                                  type="text"
                                  class="warning-custom-input"
                                  placeholder="custom…"
                                  on:click|stopPropagation
                                  on:keydown|stopPropagation={e => { if (e.key === "Enter" && e.target.value.trim()) { applyWarningFix(c, w, e.target.value.trim()); } }}
                                />
                              </div>
                            </div>
                          {/each}
                        </div>
                      {/if}
                      <div class="detail-grid">
                        {#if c.timestamp}<div class="detail-field"><span class="detail-label">UTC</span> {formatTimestamp(c.timestamp)}</div>{/if}
                        {#if c.call}<div class="detail-field"><span class="detail-label">Call</span> {c.call}</div>{/if}
                        {#if c.freq}<div class="detail-field"><span class="detail-label">Freq</span> {formatFreq(c.freq)}{#if freqToBand(c.freq)} ({freqToBand(c.freq)}){/if}</div>{/if}
                        {#if c.mode}<div class="detail-field"><span class="detail-label">Mode</span> {c.mode}</div>{/if}
                        {#if c.rst_sent}<div class="detail-field"><span class="detail-label">RST Sent</span> {c.rst_sent}</div>{/if}
                        {#if c.rst_recv}<div class="detail-field"><span class="detail-label">RST Recv</span> {c.rst_recv}</div>{/if}
                        {#if c.name}<div class="detail-field"><span class="detail-label">Name</span> {c.name}</div>{/if}
                        {#if c.pota_park}<div class="detail-field"><span class="detail-label">POTA</span> {c.pota_park}</div>{/if}
                        {#if c.grid}<div class="detail-field"><span class="detail-label">Grid</span> {c.grid}</div>{/if}
                        {#if c.qth}<div class="detail-field"><span class="detail-label">QTH</span> {c.qth}</div>{/if}
                        {#if c.state}<div class="detail-field"><span class="detail-label">State</span> {c.state}</div>{/if}
                        {#if c.country}<div class="detail-field"><span class="detail-label">Country</span> {c.country}</div>{/if}
                        {#if c.skcc}<div class="detail-field"><span class="detail-label">SKCC</span> {c.skcc}{#if c.skcc_exch} (validated){/if}</div>{/if}
                        {#if c.notes}<div class="detail-field detail-full"><span class="detail-label">Notes</span> {c.notes}</div>{/if}
                        {#if activeTab === "export"}
                          {#if renderComment(c, commentTemplate, commentSeparator)}<div class="detail-field detail-full"><span class="detail-label">Comments</span> {renderComment(c, commentTemplate, commentSeparator)}</div>{/if}
                        {:else}
                          {#if c.original_comment && c.original_comment !== (c.comments || "")}
                            <div class="detail-field detail-full"><span class="detail-label">Original Comment</span> <span class="comment-original">{c.original_comment}</span></div>
                            <div class="detail-field detail-full"><span class="detail-label">Imported Comment</span> {c.comments || "(empty — fully stripped)"}</div>
                          {:else if c.comments}
                            <div class="detail-field detail-full"><span class="detail-label">Comments</span> {c.comments}</div>
                          {/if}
                        {/if}
                        {#if c.adif_lines}
                          {#each c.adif_lines as line, li}
                            <div class="detail-field detail-full detail-adif"><span class="detail-label">ADIF {li + 1}</span><code>{line}</code></div>
                          {/each}
                        {:else if c.adif_line}
                          <div class="detail-field detail-full detail-adif"><span class="detail-label">ADIF</span><code>{c.adif_line}</code></div>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>
      {:else if activeTab === "import" && !importFile && !loadingImport}
        <div class="empty-preview">No file selected</div>
      {:else if activeTab === "export" && exportPreview && exportPreview.contacts.length === 0}
        <div class="empty-preview">No contacts match filters</div>
      {/if}

    </div>
  </div>

  <div class="action-bar">
    {#if activeTab === "export"}
      <span class="action-summary">
        {#if exportPreview}
          Exporting {exportPreview.included} of {exportPreview.total} contacts
          {#if exportPreview.excluded > 0}({exportPreview.excluded} excluded by filters){/if}
        {/if}
      </span>
      <button class="action-btn" on:click={exportAdif} disabled={!exportPreview || exportPreview.included === 0}>
        Download ADIF
      </button>
    {:else}
      <span class="action-summary">
        {#if importPreview}
          Importing {importPreview.new_count} new QSOs
          {#if importPreview.merged_count > 0}({importPreview.merged_count} merged){/if}
          {#if importPreview.duplicate_count > 0}({importPreview.duplicate_count} duplicates skipped){/if}
          {#if importPreview.skipped_count > 0}({importPreview.skipped_count} invalid skipped){/if}
          {#if warningCount > 0}<span class="action-error">— {warningCount} error{warningCount !== 1 ? "s" : ""} must be resolved</span>{/if}
        {/if}
      </span>
      {#if importPreview}
        <button class="action-btn cancel-btn" on:click={cancelImport}>Cancel</button>
      {/if}
      <button class="action-btn" on:click={executeImport} disabled={!importPreview || importPreview.new_count === 0 || importing || warningCount > 0}>
        {importing ? "Importing..." : "Import"}
      </button>
    {/if}
  </div>
</div>

<style>
  .export-import {
    width: 100%;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .tab-bar {
    display: flex;
    gap: 0;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border, #555);
  }

  .tab {
    background: none;
    color: var(--text-muted);
    border: none;
    border-bottom: 2px solid transparent;
    padding: 0.5rem 1.5rem;
    font-family: inherit;
    font-size: 0.95rem;
    font-weight: bold;
    cursor: pointer;
    margin: 0;
    border-radius: 0;
  }

  .tab:hover {
    color: var(--text);
    background: none;
  }

  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
    background: none;
  }

  .main-layout {
    display: flex;
    gap: 1.5rem;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .sidebar {
    flex: 0 0 315px;
    overflow-y: auto;
    align-self: stretch;
  }

  .preview-pane {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-self: stretch;
  }

  @media (max-width: 900px) {
    .main-layout {
      flex-direction: column;
      overflow: auto;
    }

    .sidebar {
      flex: 0 0 auto;
      width: 100%;
      overflow-y: visible;
    }

    .preview-pane {
      width: 100%;
    }
  }

  h3 {
    color: var(--accent);
    font-size: 1rem;
    margin: 1.5rem 0 0.3rem 0;
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

  /* Action bar */
  .action-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 0.75rem;
    border: 1px solid var(--border, #555);
    border-radius: 3px;
    background: var(--bg-header, var(--bg));
    flex-shrink: 0;
    gap: 1rem;
  }

  .action-summary {
    color: var(--text-muted);
    font-size: 0.85rem;
    font-weight: bold;
  }

  .action-btn {
    background: var(--accent);
    color: var(--bg);
    border: none;
    padding: 0.4rem 1.2rem;
    font-family: inherit;
    font-size: 0.85rem;
    font-weight: bold;
    border-radius: 3px;
    cursor: pointer;
    margin: 0;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .action-btn:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .action-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .action-btn.cancel-btn {
    background: none;
    color: var(--text-muted);
    border: 1px solid var(--border, #555);
  }

  .action-btn.cancel-btn:hover {
    color: var(--text);
    border-color: var(--text-muted);
    background: none;
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

  .filter-tabs {
    display: flex;
    gap: 0;
    padding: 0.3rem 0.5rem;
    border: 1px solid var(--border, #555);
    border-bottom: none;
    background: var(--bg-header, var(--bg));
  }

  .filter-tab {
    background: none;
    color: var(--text-muted);
    border: 1px solid transparent;
    padding: 0.2rem 0.8rem;
    font-size: 0.75rem;
    font-weight: bold;
    cursor: pointer;
    border-radius: 3px;
    margin: 0;
  }

  .filter-tab:hover {
    background: none;
    color: var(--text);
  }

  .filter-tab.active {
    background: var(--bg);
    color: var(--text);
    border-color: var(--border, #555);
  }

  .filter-tab.error-tab {
    color: #c90;
  }

  .filter-tab.error-tab.active {
    color: #ea0;
  }

  .filter-tab.fixed-tab {
    color: #4a4;
  }

  .filter-tab.fixed-tab.active {
    color: #5c5;
  }

  .filter-tab.merged-tab {
    color: #39f;
  }

  .filter-tab.merged-tab.active {
    color: #5bf;
  }

  .has-warning td:first-child {
    box-shadow: inset 3px 0 0 #c90;
  }
  .has-merged td:first-child {
    box-shadow: inset 3px 0 0 #39f;
  }
  .has-merged.has-warning td:first-child {
    box-shadow: inset 3px 0 0 #c90;
  }

  .warning-list {
    padding: 0.4rem 0.75rem;
    border-bottom: 1px solid var(--border-dim, rgba(255,255,255,0.05));
  }

  .warning-item {
    font-size: 0.8rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid var(--border-dim, rgba(255,255,255,0.05));
  }

  .warning-item:last-child {
    border-bottom: none;
  }

  .warning-message {
    color: #ea0;
    margin-bottom: 0.3rem;
  }

  .warning-actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
  }

  .warning-label {
    color: var(--text-muted);
    font-size: 0.75rem;
  }

  .warning-fix-btn {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border, #555);
    padding: 0.15rem 0.5rem;
    font-size: 0.75rem;
    font-weight: normal;
    border-radius: 3px;
    cursor: pointer;
    margin: 0;
  }

  .warning-fix-btn:hover {
    border-color: var(--accent);
    background: var(--bg);
  }

  .fix-source {
    color: var(--text-muted);
    font-size: 0.65rem;
  }

  .warning-custom-input {
    background: var(--bg-input, var(--bg));
    color: var(--text);
    border: 1px solid var(--border, #555);
    padding: 0.15rem 0.4rem;
    font-family: inherit;
    font-size: 0.75rem;
    border-radius: 3px;
    width: 80px;
  }

  .action-error {
    color: #ea0;
  }

  .adif-header-bar {
    display: flex;
    align-items: center;
    padding: 0.4rem 0.75rem;
    border: 1px solid var(--border, #555);
    border-bottom: none;
    border-radius: 3px 3px 0 0;
    background: var(--bg-header, var(--bg));
    cursor: pointer;
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .adif-header-bar:hover {
    color: var(--text);
  }

  .adif-header-summary {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .adif-ver {
    font-size: 0.7rem;
    opacity: 0.7;
  }

  .expand-hint {
    font-size: 0.7rem;
    opacity: 0.5;
  }

  .adif-header-detail {
    border: 1px solid var(--border, #555);
    border-bottom: none;
    padding: 0.5rem 0.75rem;
    font-size: 0.8rem;
  }

  .adif-header-fields {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem 1.2rem;
    margin-bottom: 0.5rem;
  }

  .adif-field strong {
    color: var(--accent);
    font-size: 0.7rem;
    text-transform: uppercase;
  }

  .adif-header-raw {
    display: block;
    font-size: 0.7rem;
    color: var(--text-muted);
    word-break: break-all;
    white-space: pre-wrap;
  }

  .preview-table-wrap {
    flex: 1;
    min-height: 8rem;
    overflow: auto;
    border: 1px solid var(--border, #555);
    border-radius: 0 0 3px 3px;
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
    z-index: 1;
    background: var(--bg-header, var(--bg));
    text-align: left;
    padding: 0.4rem 0.5rem;
    color: var(--accent);
    border-bottom: 1px solid var(--border, #555);
    font-size: 0.75rem;
    text-transform: uppercase;
    overflow: hidden;
  }

  .resize-handle {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 5px;
    cursor: col-resize;
    background: transparent;
  }

  .resize-handle:hover,
  .resize-handle:active {
    background: var(--accent);
    opacity: 0.4;
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

  .preview-table .col-compact { width: 5rem; }
  .preview-table .col-flex { width: 8rem; }
  .preview-table .col-freq { width: 11rem; }
  .preview-table .col-comment { width: 15rem; }

  .preview-table .clickable {
    cursor: pointer;
  }

  .preview-table .clickable:hover td {
    background: var(--bg-header, rgba(255,255,255,0.03));
  }

  .preview-table .expanded td {
    background: rgba(200, 180, 50, 0.08);
    border-top: 1px solid rgba(200, 180, 50, 0.4);
  }

  .preview-table .expanded td:first-child {
    border-left: 2px solid rgba(200, 180, 50, 0.5);
  }

  .preview-table .expanded td:last-child {
    border-right: 2px solid rgba(200, 180, 50, 0.5);
  }

  .detail-row td {
    padding: 0 !important;
    border-bottom: 2px solid rgba(200, 180, 50, 0.5) !important;
    border-left: 2px solid rgba(200, 180, 50, 0.5) !important;
    border-right: 2px solid rgba(200, 180, 50, 0.5) !important;
    white-space: normal !important;
    overflow: visible !important;
    position: sticky;
    left: 0;
    background: rgba(200, 180, 50, 0.08);
  }

  .detail-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem 1.2rem;
    padding: 0.5rem 0.75rem;
    font-size: 0.8rem;
    max-width: calc(100vw - 480px);
    box-sizing: border-box;
  }

  @media (max-width: 900px) {
    .detail-grid {
      max-width: calc(100vw - 2rem);
    }
  }

  .detail-field {
    white-space: nowrap;
  }

  .detail-field.detail-full {
    width: 100%;
    white-space: normal;
    word-break: break-word;
  }

  .detail-label {
    color: var(--accent);
    font-weight: bold;
    font-size: 0.7rem;
    text-transform: uppercase;
    margin-right: 0.3rem;
  }

  .detail-adif code {
    font-size: 0.7rem;
    color: var(--text-muted);
    word-break: break-all;
    white-space: pre-wrap;
  }

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

  .empty-preview {
    flex: 1;
    min-height: 8rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-style: italic;
    padding: 2rem;
    text-align: center;
    border: 1px solid var(--border, #555);
    border-radius: 3px;
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
    margin-bottom: 0.5rem;
  }

  .file-label:hover {
    background: var(--accent-hover);
  }

  .file-label input[type="file"] {
    display: none;
  }

  .file-name {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin: 0 0 0.5rem 0;
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

  .template-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .suggest-btn {
    background: none;
    color: var(--accent);
    border: 1px solid var(--accent);
    padding: 0.2rem 0.6rem;
    font-size: 0.7rem;
    font-weight: bold;
    border-radius: 3px;
    cursor: pointer;
    margin: 0;
    white-space: nowrap;
  }

  .suggest-btn:hover:not(:disabled) {
    background: var(--accent);
    color: var(--bg);
  }

  .suggest-btn:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .template-controls {
    display: flex;
    gap: 1rem;
    align-items: flex-end;
    flex-wrap: wrap;
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
    margin-bottom: 0;
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
    display: block;
    font-size: 0.75rem;
    color: var(--text-muted);
    font-style: italic;
    margin-top: 0.5rem;
  }

  .template-match-count {
    display: block;
    font-size: 0.75rem;
    color: var(--accent);
    font-weight: bold;
    margin-top: 0.25rem;
  }

  .comment-modified {
    color: var(--accent);
    font-weight: bold;
  }

  .comment-original {
    text-decoration: line-through;
    color: var(--text-muted);
  }

  .template-no-match {
    display: block;
    font-size: 0.75rem;
    color: var(--text-muted);
    font-style: italic;
    margin-top: 0.25rem;
  }
</style>
