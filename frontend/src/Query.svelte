<script>
  let sql = "SELECT * FROM contacts ORDER BY timestamp DESC LIMIT 100";
  let columns = [];
  let rows = [];
  let error = "";
  let loading = false;
  let rowCount = 0;
  let truncated = false;
  let colWidths = [];
  let resizing = null;
  let cannedSelect = "";

  const cannedQueries = [
    { label: "All contacts (latest 100)", sql: "SELECT * FROM contacts ORDER BY timestamp DESC LIMIT 100" },
    { label: "Contact count by mode", sql: "SELECT mode, count(*) AS count FROM contacts GROUP BY mode ORDER BY count DESC" },
    { label: "Contact count by band", sql: "SELECT freq, count(*) AS count FROM contacts GROUP BY freq ORDER BY count DESC" },
    { label: "Contacts per day", sql: "SELECT date(timestamp) AS day, count(*) AS count FROM contacts GROUP BY day ORDER BY day DESC" },
    { label: "Unique callsigns worked", sql: "SELECT DISTINCT call FROM contacts ORDER BY call" },
    { label: "POTA activations", sql: "SELECT pota_park, count(*) AS count FROM contacts WHERE pota_park IS NOT NULL AND pota_park != '' GROUP BY pota_park ORDER BY count DESC" },
    { label: "States worked", sql: "SELECT state, count(*) AS count FROM contacts WHERE state IS NOT NULL AND state != '' GROUP BY state ORDER BY count DESC" },
    { label: "Countries worked", sql: "SELECT country, count(*) AS count FROM contacts WHERE country IS NOT NULL AND country != '' GROUP BY country ORDER BY count DESC" },
    { label: "All POTA parks", sql: "SELECT reference, name, location_desc, grid, latitude, longitude FROM pota_parks ORDER BY reference" },
    { label: "All notifications", sql: "SELECT * FROM notifications ORDER BY timestamp DESC" },
    { label: "Blocked Access: settings table", sql: "SELECT value FROM settings WHERE key = 'qrz_password'" },
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
      colWidths = columns.map(() => 150);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
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

  function handleKeydown(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      runQuery();
    }
  }

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
</script>

<div class="query-page">
  <div class="query-top">
    <h2>SQL Query</h2>

    <div class="editor">
      <textarea
        bind:value={sql}
        on:keydown={handleKeydown}
        rows="4"
        spellcheck="false"
        placeholder="SELECT * FROM contacts WHERE ..."
      ></textarea>
      <p class="hint">Read-only access to <code>contacts</code>, <code>notifications</code>, <code>pota_programs</code>, <code>pota_locations</code>, <code>pota_parks</code>. Max 10000 rows interactively. JSON/CSV unlimited.</p>
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
        {#if columns.length > 0}
          <button class="csv-btn" on:click={downloadCsv}>Download CSV</button>
          <button class="csv-btn" on:click={downloadJson}>Download JSON</button>
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

  {#if columns.length > 0}
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
  .hint {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin: 0 0 0.75rem;
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
  textarea {
    width: 100%;
    font-family: monospace;
    font-size: 0.9rem;
    padding: 0.5rem;
    border: 1px solid var(--border-input);
    border-radius: 4px;
    background: var(--bg-input);
    color: var(--text);
    resize: vertical;
    box-sizing: border-box;
  }
  textarea:focus {
    outline: none;
    border-color: var(--accent);
  }
  .buttons {
    display: flex;
    gap: 0.5rem;
  }
  .run-btn, .csv-btn {
    padding: 0.4rem 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85rem;
  }
  .run-btn {
    background: var(--accent);
    color: var(--bg);
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
