<script>
  import { onMount, createEventDispatcher } from "svelte";

  export let showShutdown = false;

  const dispatch = createEventDispatcher();

  let logbooks = [];
  let newName = "";
  let error = "";
  let loading = true;
  let shuttingDown = false;
  let confirmingShutdown = false;

  function requestShutdown() {
    confirmingShutdown = true;
  }

  function cancelShutdown() {
    confirmingShutdown = false;
  }

  async function shutdownServer() {
    shuttingDown = true;
    dispatch("shutdown-pending");
    try {
      const res = await fetch("/api/logbooks/shutdown", { method: "POST" });
      if (res.ok) dispatch("shutdown");
    } catch {
      dispatch("shutdown");
    }
  }

  async function fetchLogbooks() {
    try {
      const res = await fetch("/api/logbooks/");
      if (res.ok) logbooks = await res.json();
    } catch {}
    loading = false;
  }

  async function openLogbook(name) {
    error = "";
    try {
      const res = await fetch("/api/logbooks/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        dispatch("logbookopened", name);
      } else {
        const data = await res.json();
        error = data.detail || "Failed to open logbook";
      }
    } catch (e) {
      error = "Failed to open logbook";
    }
  }

  async function createLogbook() {
    if (!newName.trim()) return;
    error = "";
    const name = newName.trim();
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      error = "Name must contain only letters, digits, hyphens, and underscores";
      return;
    }
    try {
      const res = await fetch("/api/logbooks/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        newName = "";
        dispatch("logbookopened", name);
      } else {
        const data = await res.json();
        error = data.detail || "Failed to create logbook";
      }
    } catch (e) {
      error = "Failed to create logbook";
    }
  }

  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  onMount(fetchLogbooks);
</script>

<div class="picker-container">
  <div class="picker-card">
    <div class="picker-header">
      <h2>Select Logbook</h2>
      <p class="picker-subtitle">Most recent logbooks shown first</p>
    </div>

    {#if error}
      <div class="picker-error">{error}</div>
    {/if}

    <div class="picker-body">
      {#if loading}
        <p class="picker-loading">Loading...</p>
      {:else if logbooks.length === 0}
        <p class="picker-empty">No logbooks found. Create one below.</p>
      {:else}
        <div class="picker-list">
          {#each logbooks as lb}
            <button class="picker-item" on:click={() => openLogbook(lb.name)}>
              <span class="picker-item-name">{lb.name}</span>
              <span class="picker-item-size">{formatSize(lb.size_bytes)}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="picker-create">
      <h3>Create New Logbook</h3>
      <div class="picker-create-row">
        <input
          type="text"
          bind:value={newName}
          placeholder="logbook-name"
          on:keydown={e => { if (e.key === "Enter") createLogbook(); }}
        />
        <button on:click={createLogbook}>Create</button>
      </div>
    </div>

    {#if showShutdown}
      <div class="picker-shutdown">
        {#if confirmingShutdown}
          <p class="confirm-text">Are you sure you want to shut down the server?</p>
          <div class="confirm-row">
            <button class="confirm-btn confirm-yes" on:click={shutdownServer} disabled={shuttingDown}>
              {shuttingDown ? "Shutting down…" : "Yes, Shutdown"}
            </button>
            <button class="confirm-btn confirm-no" on:click={cancelShutdown} disabled={shuttingDown}>Cancel</button>
          </div>
        {:else}
          <button class="shutdown-btn" on:click={requestShutdown}>Shutdown Server</button>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .picker-container {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    padding: 1rem;
    box-sizing: border-box;
  }

  .picker-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 2rem;
    width: 100%;
    max-width: 480px;
    max-height: calc(100vh - 2rem);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .picker-header {
    flex-shrink: 0;
  }

  .picker-card h2 {
    margin: 0 0 0.25rem;
    color: var(--accent);
    font-size: 1.4rem;
    text-align: center;
  }

  .picker-subtitle {
    margin: 0 0 1rem;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.85rem;
  }

  .picker-error {
    background: #ff444422;
    color: #ff6666;
    border: 1px solid #ff444444;
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    flex-shrink: 0;
  }

  .picker-body {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }

  .picker-loading, .picker-empty {
    text-align: center;
    color: var(--text-muted);
    padding: 1rem 0;
  }

  .picker-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .picker-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    cursor: pointer;
    font-size: 1rem;
    transition: background 0.15s;
  }

  .picker-item:hover {
    background: var(--accent);
    color: #111;
  }

  .picker-item-name {
    font-weight: 600;
  }

  .picker-item-size {
    font-size: 0.85rem;
    opacity: 0.7;
  }

  .picker-create {
    flex-shrink: 0;
    border-top: 1px solid var(--border);
    padding-top: 1.5rem;
    margin-top: 1.5rem;
  }

  .picker-create h3 {
    margin: 0 0 0.75rem;
    font-size: 1rem;
    color: var(--text-muted);
  }

  .picker-create-row {
    display: flex;
    gap: 0.5rem;
  }

  .picker-create-row input {
    flex: 1;
    padding: 0.5rem 0.75rem;
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    border-radius: 6px;
    color: var(--text);
    font-size: 0.95rem;
  }

  .picker-create-row button {
    padding: 0.5rem 1rem;
    background: var(--accent);
    color: #111;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    font-size: 0.95rem;
  }

  .picker-create-row button:hover {
    background: var(--accent-hover);
  }

  .picker-shutdown {
    border-top: 1px solid var(--border);
    padding-top: 1.5rem;
    margin-top: 1.5rem;
    text-align: center;
  }

  .shutdown-btn {
    width: 100%;
    padding: 0.5rem 1.5rem;
    background: transparent;
    color: var(--text-muted);
    border: 1px solid var(--border);
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
  }

  .shutdown-btn:hover {
    background: #ff444422;
    color: #ff6666;
    border-color: #ff444444;
  }

  .confirm-text {
    margin: 0 0 0.75rem;
    color: var(--text-muted);
    font-size: 0.9rem;
    text-align: center;
  }

  .confirm-row {
    display: flex;
    gap: 0.5rem;
  }

  .confirm-btn {
    flex: 1;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    border: 1px solid var(--border);
  }

  .confirm-yes {
    background: #ff444422;
    color: #ff6666;
    border-color: #ff444444;
  }

  .confirm-yes:hover {
    background: #ff444444;
  }

  .confirm-no {
    background: transparent;
    color: var(--text-muted);
  }

  .confirm-no:hover {
    background: var(--bg-input);
  }

  .confirm-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
