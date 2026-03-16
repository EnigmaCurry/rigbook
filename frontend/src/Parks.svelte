<script>
  import { onMount } from "svelte";

  let programs = [];
  let loading = false;
  let saving = false;
  let fetching = false;
  let fetchProgress = null; // { done, total, location }
  let fetchResult = null; // shown after fetch completes
  let filter = "";
  let dirty = false;

  $: filtered = filter
    ? programs.filter(p =>
        p.prefix.toLowerCase().includes(filter.toLowerCase()) ||
        p.name.toLowerCase().includes(filter.toLowerCase())
      )
    : programs;

  $: selectedCount = programs.filter(p => p.selected).length;
  $: cachedCountries = programs.filter(p => p.park_count > 0).length;
  $: totalLocations = programs.reduce((s, p) => s + (p.location_count || 0), 0);
  $: totalParks = programs.reduce((s, p) => s + (p.park_count || 0), 0);

  async function loadPrograms() {
    loading = true;
    try {
      const res = await fetch("/api/pota/programs");
      if (res.ok) programs = await res.json();
    } catch {}
    loading = false;
  }

  function toggle(prefix) {
    programs = programs.map(p =>
      p.prefix === prefix ? { ...p, selected: !p.selected } : p
    );
    dirty = true;
  }

  async function saveSelections() {
    saving = true;
    const prefixes = programs.filter(p => p.selected).map(p => p.prefix);
    try {
      await fetch("/api/pota/selected-programs", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prefixes }),
      });
      dirty = false;
    } catch {}
    saving = false;
  }

  async function fetchParks() {
    if (dirty) await saveSelections();
    fetching = true;
    fetchProgress = null;
    fetchResult = null;
    let totalParks = 0;
    let totalLocations = 0;
    let errors = 0;
    try {
      const res = await fetch("/api/pota/fetch-parks", { method: "POST" });
      const contentType = res.headers.get("content-type") || "";

      if (contentType.includes("text/event-stream")) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split("\n\n");
          buf = lines.pop();
          for (const line of lines) {
            const m = line.match(/^data: (.+)$/);
            if (!m) continue;
            const msg = JSON.parse(m[1]);
            if (msg.type === "progress") {
              fetchProgress = msg;
              totalParks += msg.parks || 0;
              totalLocations++;
            } else if (msg.type === "error") {
              fetchProgress = msg;
              errors++;
            } else if (msg.type === "start") {
              fetchProgress = { done: 0, total: msg.total, location: "" };
            }
          }
        }
        fetchResult = { locations: totalLocations, parks: totalParks, errors };
      } else {
        const data = await res.json();
        if (data.status === "up_to_date") {
          fetchResult = { upToDate: true, locations: data.locations };
        }
      }
    } catch {}
    fetching = false;
    fetchProgress = null;
    await loadPrograms();
  }

  onMount(loadPrograms);
</script>

<section class="parks">
  <div class="parks-header">
    <h2>POTA Parks Cache</h2>
  </div>

  <div class="stats">
    <span>{programs.length} countries</span>
    <span>{totalLocations} locations</span>
    <span class="stat-highlight">{totalParks} parks cached across {cachedCountries} {cachedCountries === 1 ? "country" : "countries"}</span>
  </div>

  <p class="description">Select countries to cache park data for. Then click Update to fetch all parks for selected countries.</p>

  <div class="controls">
    <input type="text" class="filter-input" placeholder="Filter countries..." bind:value={filter} />
    <span class="count">{selectedCount} selected</span>
    {#if dirty}
      <button class="btn save-btn" on:click={saveSelections} disabled={saving}>
        {saving ? "Saving..." : "Save"}
      </button>
    {/if}
    <button class="btn update-btn" on:click={fetchParks} disabled={fetching || selectedCount === 0}>
      {#if fetching}
        Fetching...
      {:else}
        Update Parks
      {/if}
    </button>
  </div>

  {#if fetchResult}
    <div class="fetch-result">
      {#if fetchResult.upToDate}
        All {fetchResult.locations} locations already up to date.
      {:else}
        Fetched {fetchResult.parks} parks across {fetchResult.locations} locations.{#if fetchResult.errors} ({fetchResult.errors} errors){/if}
      {/if}
    </div>
  {/if}

  {#if fetching && fetchProgress}
    <div class="progress">
      <div class="progress-bar">
        <div class="progress-fill" style="width: {(fetchProgress.done / fetchProgress.total * 100).toFixed(1)}%"></div>
      </div>
      <span class="progress-text">{fetchProgress.done} / {fetchProgress.total} locations — {fetchProgress.location || "..."}</span>
    </div>
  {/if}

  {#if loading}
    <p class="loading">Loading programs...</p>
  {:else}
    <div class="program-list">
      {#each filtered as prog}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div class="program-row" class:selected={prog.selected} on:click={() => toggle(prog.prefix)}>
          <input type="checkbox" checked={prog.selected} on:click|stopPropagation={() => toggle(prog.prefix)} />
          <span class="prefix">{prog.prefix}</span>
          <span class="name">{prog.name}</span>
          {#if prog.park_count > 0}
            <span class="badge">{prog.park_count} parks</span>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .parks {
    padding: 0;
  }

  .parks-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  h2 {
    margin: 0;
    color: var(--accent);
    font-size: 1.2rem;
  }

  .stats {
    display: flex;
    gap: 1rem;
    font-size: 0.85rem;
    color: var(--text-dim);
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
  }

  .stat-highlight {
    color: var(--accent);
  }

  .description {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin: 0 0 0.75rem 0;
  }

  .controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
  }

  .filter-input {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 0.3rem 0.5rem;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
    outline: none;
    width: 200px;
  }

  .filter-input:focus {
    border-color: var(--accent);
  }

  .count {
    color: var(--text-dim);
    font-size: 0.85rem;
  }

  .btn {
    padding: 0.3rem 0.8rem;
    font-size: 0.85rem;
    border-radius: 3px;
    border: none;
    cursor: pointer;
    font-family: inherit;
    font-weight: bold;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .save-btn {
    background: var(--btn-secondary);
    color: var(--text);
  }

  .update-btn {
    background: var(--accent);
    color: var(--bg);
  }

  .update-btn:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .progress {
    margin-bottom: 0.75rem;
  }

  .progress-bar {
    height: 6px;
    background: var(--bg-deep);
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 0.25rem;
  }

  .progress-fill {
    height: 100%;
    background: var(--accent);
    transition: width 0.2s;
  }

  .progress-text {
    font-size: 0.75rem;
    color: var(--text-dim);
  }

  .fetch-result {
    font-size: 0.85rem;
    color: var(--accent);
    margin-bottom: 0.75rem;
  }

  .loading {
    color: var(--text-muted);
    font-style: italic;
  }

  .program-list {
    display: flex;
    flex-direction: column;
    max-height: 60vh;
    overflow-y: auto;
  }

  .program-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.4rem;
    cursor: pointer;
    border-radius: 3px;
    white-space: nowrap;
    line-height: 1.4;
  }

  .program-row:hover {
    background: var(--row-hover);
  }

  .program-row.selected {
    background: var(--bg-deep);
  }

  .program-row input[type="checkbox"] {
    cursor: pointer;
    flex-shrink: 0;
  }

  .prefix {
    color: var(--accent-callsign);
    font-weight: bold;
    flex-shrink: 0;
    min-width: 4ch;
  }

  .name {
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .badge {
    font-size: 0.75rem;
    color: var(--text-dim);
    background: var(--bg-deep);
    padding: 0.05rem 0.4rem;
    border-radius: 8px;
    flex-shrink: 0;
    margin-left: auto;
  }
</style>
