<script>
  let sql = "SELECT * FROM contacts ORDER BY timestamp DESC LIMIT 100";
  let columns = [];
  let rows = [];
  let error = "";
  let loading = false;
  let rowCount = 0;

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

  function handleKeydown(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      runQuery();
    }
  }
</script>

<div class="query-page">
  <h2>SQL Query</h2>
  <p class="hint">Read-only access to the <code>contacts</code> table. Max {10000} rows.</p>

  <div class="editor">
    <textarea
      bind:value={sql}
      on:keydown={handleKeydown}
      rows="4"
      spellcheck="false"
      placeholder="SELECT * FROM contacts WHERE ..."
    ></textarea>
    <div class="buttons">
      <button class="run-btn" on:click={runQuery} disabled={loading}>
        {loading ? "Running…" : "Run Query"}
      </button>
      {#if columns.length > 0}
        <button class="csv-btn" on:click={downloadCsv}>Download CSV</button>
      {/if}
    </div>
  </div>

  {#if error}
    <div class="error">{error}</div>
  {/if}

  {#if columns.length > 0}
    <div class="result-info">{rowCount} row{rowCount !== 1 ? "s" : ""}</div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            {#each columns as col}
              <th>{col}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each rows as row}
            <tr>
              {#each row as cell}
                <td>{cell ?? ""}</td>
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
    max-width: 100%;
    padding: 1rem;
  }
  h2 {
    margin: 0 0 0.25rem;
  }
  .hint {
    color: var(--text-secondary, #888);
    font-size: 0.85rem;
    margin: 0 0 0.75rem;
  }
  .hint code {
    background: var(--bg-secondary, #2a2a2a);
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
  textarea {
    width: 100%;
    font-family: monospace;
    font-size: 0.9rem;
    padding: 0.5rem;
    border: 1px solid var(--border, #444);
    border-radius: 4px;
    background: var(--bg-secondary, #1e1e1e);
    color: var(--text, #eee);
    resize: vertical;
    box-sizing: border-box;
  }
  textarea:focus {
    outline: none;
    border-color: var(--accent, #58a6ff);
  }
  .buttons {
    display: flex;
    gap: 0.5rem;
  }
  .run-btn, .csv-btn {
    padding: 0.4rem 1rem;
    border: 1px solid var(--border, #444);
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85rem;
  }
  .run-btn {
    background: var(--accent, #58a6ff);
    color: var(--bg, #000);
    border-color: var(--accent, #58a6ff);
    font-weight: bold;
  }
  .run-btn:hover:not(:disabled) {
    opacity: 0.85;
  }
  .run-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .csv-btn {
    background: var(--bg-secondary, #2a2a2a);
    color: var(--text, #eee);
  }
  .csv-btn:hover {
    background: var(--bg-tertiary, #333);
  }
  .error {
    background: #3a1111;
    color: #ff6b6b;
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    margin-bottom: 0.75rem;
    font-family: monospace;
    font-size: 0.85rem;
    white-space: pre-wrap;
  }
  .result-info {
    font-size: 0.8rem;
    color: var(--text-secondary, #888);
    margin-bottom: 0.35rem;
  }
  .table-wrap {
    overflow-x: auto;
    border: 1px solid var(--border, #444);
    border-radius: 4px;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    font-size: 0.8rem;
    font-family: monospace;
  }
  th, td {
    padding: 0.3rem 0.5rem;
    border: 1px solid var(--border, #333);
    text-align: left;
    white-space: nowrap;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  th {
    background: var(--bg-secondary, #2a2a2a);
    position: sticky;
    top: 0;
    font-weight: 600;
  }
  tr:nth-child(even) {
    background: var(--bg-secondary, #1a1a1a);
  }
</style>
