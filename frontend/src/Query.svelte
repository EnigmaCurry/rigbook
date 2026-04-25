<script>
  import { onMount } from "svelte";

  export let initialSql = "";

  let sql = initialSql || "";
  let columns = [];
  let rows = [];
  let error = "";
  let loading = false;
  let rowCount = 0;
  let truncated = false;
  let colWidths = [];
  let resizing = null;
  let cannedSelect = "";
  let schema = null;
  let showSchema = true;
  let textareaEl;
  let taHeight = 60;
  let taResizing = false;

  const cannedQueries = [
    { label: "All records (latest 100)", sql: "SELECT * FROM records ORDER BY timestamp DESC LIMIT 100" },
    { label: "Records per day", sql: "SELECT date(timestamp) AS day, count(*) AS count FROM records GROUP BY day ORDER BY day DESC" },
    { label: "Records by tag", sql: "SELECT tags, count(*) AS count FROM records WHERE tags IS NOT NULL AND tags != '' GROUP BY tags ORDER BY count DESC" },
    { label: "All notifications", sql: "SELECT * FROM notifications ORDER BY timestamp DESC" },
    { label: "Blocked Access: settings table", sql: "-- Blocked: the settings table is not in the allowed table list\nSELECT value FROM settings WHERE key = 'secret'" },
    { label: "Blocked Access: insert record", sql: "-- Blocked: only SELECT statements are allowed (read-only connection)\nINSERT INTO records (title, timestamp) VALUES ('Test', '2026-01-01 00:00:00')" },
  ];

  function applyCanned(e) {
    const val = e.target.value;
    if (val) {
      sql = val;
      cannedSelect = "";
      runQuery();
    }
  }

  async function runQuery() {
    error = "";
    loading = true;
    columns = [];
    rows = [];
    try {
      const resp = await fetch(`/api/query/?sql=${encodeURIComponent(sql)}`);
      const data = await resp.json();
      if (!resp.ok) {
        error = data.detail || "Query failed";
        return;
      }
      columns = data.columns;
      rows = data.rows;
      rowCount = data.count;
      truncated = data.truncated;
      colWidths = autoSizeColumns(columns, rows);
      showSchema = false;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
      updateUrl();
    }
  }

  function downloadCsv() {
    const url = `/api/query/csv?sql=${encodeURIComponent(sql)}`;
    window.open(url, "_blank");
  }

  function downloadJson() {
    const url = `/api/query/json?sql=${encodeURIComponent(sql)}`;
    window.open(url, "_blank");
  }

  function autoSizeColumns(cols, data) {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    ctx.font = "0.8rem monospace";
    const padding = 20; // cell padding + resize handle
    return cols.map((col, i) => {
      let max = ctx.measureText(col).width;
      const limit = Math.min(data.length, 200); // sample first 200 rows
      for (let r = 0; r < limit; r++) {
        const val = String(data[r][i] ?? "");
        const w = ctx.measureText(val).width;
        if (w > max) max = w;
      }
      return Math.max(40, Math.ceil(max + padding));
    });
  }

  async function toggleSchema() {
    showSchema = !showSchema;
    if (showSchema && !schema) {
      try {
        const resp = await fetch("/api/query/schema");
        const data = await resp.json();
        if (resp.ok) schema = data.tables;
        else error = data.detail || "Failed to load schema";
      } catch (e) {
        error = e.message;
      }
    }
  }

  function clearQuery() {
    sql = "";
    columns = [];
    rows = [];
    error = "";
    rowCount = 0;
    truncated = false;
    cannedSelect = "";
    updateUrl();
  }

  function updateUrl() {
    history.replaceState(null, "", `#/query?sql=${encodeURIComponent(sql)}`);
  }

  function handleKeydown(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      runQuery();
    }
  }

  onMount(async () => {
    try {
      const resp = await fetch("/api/query/schema");
      const data = await resp.json();
      if (resp.ok) schema = data.tables;
    } catch {}
    if (initialSql) runQuery();
  });

  function startResize(e, i) {
    e.preventDefault();
    resizing = i;
    const startX = e.clientX || e.touches?.[0]?.clientX;
    const startW = colWidths[i];
    const onMove = (ev) => {
      const clientX = ev.clientX || ev.touches?.[0]?.clientX;
      const delta = clientX - startX;
      colWidths[i] = Math.max(40, startW + delta);
      colWidths = colWidths;
    };
    const onUp = () => {
      resizing = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchmove", onMove);
    window.addEventListener("touchend", onUp);
  }

  function startTaResize(e) {
    e.preventDefault();
    taResizing = true;
    const startY = e.clientY || e.touches?.[0]?.clientY;
    const startH = taHeight;
    const onMove = (ev) => {
      const clientY = ev.clientY || ev.touches?.[0]?.clientY;
      const maxH = Math.floor(window.innerHeight / 2);
      taHeight = Math.min(maxH, Math.max(60, startH + clientY - startY));
    };
    const onUp = () => {
      taResizing = false;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchmove", onMove);
    window.addEventListener("touchend", onUp);
  }
</script>

<div class="query-page">
  <div class="query-top">
    <h2>SQL Query</h2>

    <div class="editor">
      <div class="ta-wrap" class:ta-resizing={taResizing}>
        <textarea
          bind:this={textareaEl}
          bind:value={sql}
          on:keydown={handleKeydown}
          on:blur={updateUrl}
          style="height: {taHeight}px"
          spellcheck="false"
          placeholder="SELECT * FROM contacts WHERE ..."
        ></textarea>
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div class="ta-resize-handle" on:mousedown={startTaResize} on:touchstart={startTaResize}>
          <span class="ta-grip"></span>
        </div>
      </div>
      <details class="hint-details">
        <summary>Query Information</summary>
        <p class="hint">Read-only access to logbook tables: <code>contacts</code>, <code>notifications</code>. Global tables (via <code>meta.</code> prefix): <code>meta.cache</code>, <code>meta.pota_programs</code>, <code>meta.pota_locations</code>, <code>meta.pota_parks</code>.<br>Max 10000 rows shown on this page. Downloading JSON/CSV returns all rows.<br>After writing your query, you may bookmark this page, and the query will be saved in the bookmark.</p>
      </details>
      <div class="buttons">
        <select class="canned-select" bind:value={cannedSelect} on:change={applyCanned}>
          <option value="">Examples...</option>
          {#each cannedQueries as q}
            <option value={q.sql}>{q.label}</option>
          {/each}
        </select>
        <button class="run-btn" on:click={runQuery} disabled={loading}>
          {loading ? "Running…" : "Run Query"}
        </button>
        <button class="csv-btn" on:click={clearQuery}>Clear</button>
        <button class="csv-btn" on:click={toggleSchema}>{showSchema ? "Hide Schema" : "View Schema"}</button>
        {#if columns.length > 0}
          <button class="csv-btn" on:click={downloadJson}>Download JSON</button>
          <button class="csv-btn" on:click={downloadCsv}>Download CSV</button>
        {/if}
      </div>
    </div>

    {#if error}
      <div class="error">{error}</div>
    {/if}

    {#if columns.length > 0}
      <div class="result-info">
        {rowCount} row{rowCount !== 1 ? "s" : ""}
        {#if truncated}<span class="truncated-warning"> — results truncated to {rowCount} rows. Use CSV download for full results.</span>{/if}
      </div>
    {/if}
  </div>

  {#if showSchema && schema}
    <div class="schema">
      {#each Object.entries(schema) as [table, cols]}
        <div class="schema-table">
          <h4>{table}</h4>
          <table class="schema-col-table">
            <tbody>
              {#each cols as col}
                <tr>
                  <td class:pk={col.pk}>{col.name}</td>
                  <td class="col-type">{col.type}{#if col.pk}, PK{/if}{#if col.notnull}, NOT NULL{/if}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/each}
    </div>
  {/if}

  {#if columns.length > 0 && !showSchema}
    <div class="table-wrap" class:resizing={resizing !== null}>
      <table style="width: {colWidths.reduce((a, b) => a + b, 0)}px; min-width: 100%;">
        <thead>
          <tr>
            {#each columns as col, i}
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <th style="width: {colWidths[i]}px; min-width: {colWidths[i]}px; max-width: {colWidths[i]}px;">
                <span class="th-content">{col}</span>
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <span class="resize-handle" on:mousedown={(e) => startResize(e, i)} on:touchstart={(e) => startResize(e, i)}></span>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each rows as row}
            <tr>
              {#each row as cell, i}
                <td style="width: {colWidths[i]}px; min-width: {colWidths[i]}px; max-width: {colWidths[i]}px;">{cell ?? ""}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .query-page {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    padding: 1rem;
    overflow: hidden;
  }
  .query-top {
    flex-shrink: 0;
  }
  h2 {
    margin: 0 0 0.25rem;
  }
  .hint-details {
    font-size: 0.85rem;
    color: var(--text-muted);
  }
  .hint-details summary {
    cursor: pointer;
    user-select: none;
  }
  .hint {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin: 0.25rem 0 0;
  }
  .hint code {
    background: var(--bg-card);
    padding: 0.1em 0.35em;
    border-radius: 3px;
    font-size: 0.9em;
  }
  .editor {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }
  .canned-select {
    padding: 0.35rem 0.5rem;
    border: 1px solid var(--border-input);
    border-radius: 4px;
    background: var(--bg-input);
    color: var(--text);
    font-size: 0.85rem;
    cursor: pointer;
    align-self: flex-start;
  }
  .ta-wrap {
    position: relative;
  }
  .ta-wrap.ta-resizing {
    user-select: none;
  }
  textarea {
    width: 100%;
    font-family: monospace;
    font-size: 0.9rem;
    padding: 0.5rem;
    border: 1px solid var(--border-input);
    border-radius: 4px 4px 0 0;
    background: var(--bg-input);
    color: var(--text);
    resize: none;
    box-sizing: border-box;
  }
  textarea:focus {
    outline: none;
    border-color: var(--accent);
  }
  .ta-resize-handle {
    width: 100%;
    height: 10px;
    cursor: ns-resize;
    background: var(--bg-card);
    border: 1px solid var(--border-input);
    border-top: none;
    border-radius: 0 0 4px 4px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .ta-resize-handle:hover {
    background: var(--btn-secondary);
  }
  .ta-grip {
    display: block;
    width: 30px;
    height: 2px;
    border-top: 1px solid var(--text-muted);
    border-bottom: 1px solid var(--text-muted);
  }
  .buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .run-btn, .csv-btn {
    padding: 0.4rem 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85rem;
    white-space: nowrap;
  }
  .run-btn {
    background: var(--accent);
    color: var(--accent-text);
    border-color: var(--accent);
    font-weight: bold;
  }
  .run-btn:hover:not(:disabled) {
    background: var(--accent-hover);
  }
  .run-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .csv-btn {
    background: var(--bg-card);
    color: var(--text);
  }
  .csv-btn:hover {
    background: var(--btn-secondary);
  }
  .error {
    background: var(--bg-card);
    color: var(--accent-error);
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--accent-error);
    border-radius: 4px;
    margin-bottom: 0.75rem;
    font-family: monospace;
    font-size: 0.85rem;
    white-space: pre-wrap;
  }
  .result-info {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.35rem;
  }
  .truncated-warning {
    color: var(--accent-error);
  }
  .schema {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    font-size: 0.8rem;
    font-family: monospace;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
    gap: 0.75rem;
  }
  .schema-table h4 {
    margin: 0 0 0.25rem;
    color: var(--accent);
    font-size: 0.85rem;
  }
  .schema-col-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.75rem;
    table-layout: fixed;
  }
  .schema-col-table td {
    padding: 0.1rem 0.4rem;
    border: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .schema-col-table td:first-child {
    width: 45%;
  }
  .schema-col-table td.pk {
    color: var(--accent);
    font-weight: bold;
  }
  .col-type {
    color: var(--text-dim);
  }
  .table-wrap {
    flex: 1;
    min-height: 0;
    overflow: auto;
    border: 1px solid var(--border);
    border-radius: 4px;
  }
  .table-wrap.resizing {
    user-select: none;
  }
  table {
    border-collapse: collapse;
    font-size: 0.8rem;
    font-family: monospace;
  }
  th, td {
    padding: 0.3rem 0.5rem;
    border: 1px solid var(--border);
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    box-sizing: border-box;
  }
  th {
    background: var(--bg-card);
    position: sticky;
    top: 0;
    font-weight: 600;
    z-index: 1;
  }
  .th-content {
    pointer-events: none;
  }
  .resize-handle {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 5px;
    cursor: col-resize;
  }
  .resize-handle:hover {
    background: var(--accent);
    opacity: 0.4;
  }
  tr:nth-child(even) {
    background: var(--bg-deep);
  }
</style>
