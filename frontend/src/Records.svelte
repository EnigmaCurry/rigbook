<script>
  import { onMount, createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  export let editId = null;

  let records = [];
  let loading = true;
  let searchQuery = "";
  let searchTimeout = null;
  let showForm = false;
  let formTitle = "";
  let formContent = "";
  let formTags = "";
  let formId = null;
  let saving = false;
  let error = "";

  $: if (editId !== null && editId !== formId) {
    loadRecord(editId);
  }

  onMount(() => {
    fetchRecords();
  });

  async function fetchRecords() {
    loading = true;
    try {
      let url = "/api/records/";
      if (searchQuery) url += `?q=${encodeURIComponent(searchQuery)}`;
      const res = await fetch(url);
      if (res.ok) {
        records = await res.json();
      }
    } catch {}
    loading = false;
  }

  function onSearchInput() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(fetchRecords, 300);
  }

  function startNew() {
    formId = null;
    formTitle = "";
    formContent = "";
    formTags = "";
    error = "";
    showForm = true;
    dispatch("dirty", true);
  }

  async function loadRecord(id) {
    try {
      const res = await fetch(`/api/records/${id}`);
      if (res.ok) {
        const r = await res.json();
        formId = r.id;
        formTitle = r.title || "";
        formContent = r.content || "";
        formTags = r.tags || "";
        showForm = true;
        dispatch("dirty", true);
      }
    } catch {}
  }

  function editRecord(r) {
    formId = r.id;
    formTitle = r.title || "";
    formContent = r.content || "";
    formTags = r.tags || "";
    error = "";
    showForm = true;
    dispatch("dirty", true);
  }

  async function saveRecord() {
    if (!formTitle.trim()) {
      error = "Title is required";
      return;
    }
    saving = true;
    error = "";
    const body = {
      title: formTitle.trim(),
      content: formContent.trim() || null,
      tags: formTags.trim() || null,
    };
    try {
      let res;
      if (formId) {
        res = await fetch(`/api/records/${formId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      } else {
        res = await fetch("/api/records/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      }
      if (res.ok) {
        cancelForm();
        await fetchRecords();
      } else {
        const data = await res.json().catch(() => null);
        error = data?.detail || "Failed to save";
      }
    } catch (e) {
      error = e.message || "Failed to save";
    }
    saving = false;
  }

  async function deleteRecord(id) {
    if (!confirm("Delete this record?")) return;
    try {
      await fetch(`/api/records/${id}`, { method: "DELETE" });
      if (formId === id) cancelForm();
      await fetchRecords();
    } catch {}
  }

  function cancelForm() {
    showForm = false;
    formId = null;
    formTitle = "";
    formContent = "";
    formTags = "";
    error = "";
    dispatch("dirty", false);
    dispatch("editClear");
  }

  function formatDate(ts) {
    if (!ts) return "";
    const d = new Date(ts.endsWith("Z") ? ts : ts + "Z");
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
      + " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  }
</script>

<div class="records-page">
  <div class="records-header">
    <div class="search-bar">
      <input
        type="text"
        placeholder="Search records..."
        bind:value={searchQuery}
        on:input={onSearchInput}
      />
    </div>
    <button class="add-btn" on:click={startNew}>+ New Record</button>
  </div>

  {#if showForm}
    <div class="record-form">
      <h3>{formId ? "Edit Record" : "New Record"}</h3>
      <div class="form-field">
        <label for="rec-title">Title</label>
        <input id="rec-title" type="text" bind:value={formTitle} placeholder="Record title" />
      </div>
      <div class="form-field">
        <label for="rec-content">Content</label>
        <textarea id="rec-content" bind:value={formContent} placeholder="Content (optional)" rows="4"></textarea>
      </div>
      <div class="form-field">
        <label for="rec-tags">Tags</label>
        <input id="rec-tags" type="text" bind:value={formTags} placeholder="Tags (optional, comma-separated)" />
      </div>
      {#if error}
        <p class="error">{error}</p>
      {/if}
      <div class="form-actions">
        <button class="cancel-btn" on:click={cancelForm}>Cancel</button>
        <button class="save-btn" on:click={saveRecord} disabled={saving}>
          {saving ? "Saving..." : (formId ? "Update" : "Create")}
        </button>
      </div>
    </div>
  {/if}

  {#if loading}
    <p class="status">Loading...</p>
  {:else if records.length === 0}
    <p class="status">{searchQuery ? "No records match your search." : "No records yet. Click '+ New Record' to create one."}</p>
  {:else}
    <div class="records-list">
      {#each records as r (r.id)}
        <div class="record-row" class:editing={formId === r.id} on:click={() => editRecord(r)}>
          <div class="record-main">
            <span class="record-title">{r.title}</span>
            {#if r.tags}
              <span class="record-tags">
                {#each r.tags.split(",").map(t => t.trim()).filter(Boolean) as tag}
                  <span class="tag">{tag}</span>
                {/each}
              </span>
            {/if}
          </div>
          <div class="record-meta">
            <span class="record-date">{formatDate(r.timestamp)}</span>
            <button class="delete-btn" on:click|stopPropagation={() => deleteRecord(r.id)} title="Delete">x</button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .records-page {
    padding: 1rem;
    max-width: 800px;
    margin: 0 auto;
  }

  .records-header {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    margin-bottom: 1rem;
  }

  .search-bar {
    flex: 1;
  }

  .search-bar input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border, #3a3b3f);
    border-radius: 6px;
    background: var(--bg-input, transparent);
    color: var(--text, #eaeaea);
    font-size: 0.9rem;
  }

  .add-btn {
    background: var(--accent, #00ff88);
    color: var(--accent-text, #000);
    border: none;
    border-radius: 6px;
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }

  .add-btn:hover {
    opacity: 0.9;
  }

  .record-form {
    background: var(--bg-card, #24252b);
    border: 1px solid var(--border, #3a3b3f);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
  }

  .record-form h3 {
    margin: 0 0 0.75rem;
    font-size: 1rem;
    color: var(--text, #eaeaea);
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    margin-bottom: 0.75rem;
  }

  .form-field label {
    font-size: 0.75rem;
    color: var(--text-dim, #888);
  }

  .form-field input,
  .form-field textarea {
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--border, #3a3b3f);
    border-radius: 4px;
    background: var(--bg-input, transparent);
    color: var(--text, #eaeaea);
    font-size: 0.9rem;
    font-family: inherit;
    resize: vertical;
  }

  .error {
    color: #ff4444;
    font-size: 0.8rem;
    margin: 0 0 0.5rem;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .cancel-btn {
    background: none;
    border: 1px solid var(--border, #3a3b3f);
    color: var(--text-dim, #888);
    border-radius: 4px;
    padding: 0.35rem 0.75rem;
    cursor: pointer;
    font-size: 0.85rem;
  }

  .save-btn {
    background: var(--accent, #00ff88);
    color: var(--accent-text, #000);
    border: none;
    border-radius: 4px;
    padding: 0.35rem 0.75rem;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.85rem;
  }

  .save-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .status {
    color: var(--text-dim, #888);
    font-size: 0.9rem;
    text-align: center;
    margin: 2rem 0;
  }

  .records-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .record-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0.75rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.1s;
  }

  .record-row:hover {
    background: var(--bg-hover, rgba(255, 255, 255, 0.05));
  }

  .record-row.editing {
    background: var(--bg-selected, rgba(255, 255, 255, 0.08));
  }

  .record-main {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
    flex: 1;
  }

  .record-title {
    font-size: 0.9rem;
    color: var(--text, #eaeaea);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .record-tags {
    display: flex;
    gap: 0.25rem;
    flex-shrink: 0;
  }

  .tag {
    font-size: 0.7rem;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    background: var(--bg-card, #24252b);
    color: var(--text-dim, #888);
    border: 1px solid var(--border, #3a3b3f);
  }

  .record-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .record-date {
    font-size: 0.75rem;
    color: var(--text-dim, #888);
    white-space: nowrap;
  }

  .delete-btn {
    background: none;
    border: none;
    color: var(--text-dim, #888);
    cursor: pointer;
    font-size: 0.8rem;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    opacity: 0;
    transition: opacity 0.1s;
  }

  .record-row:hover .delete-btn {
    opacity: 1;
  }

  .delete-btn:hover {
    color: #ff4444;
    background: rgba(255, 68, 68, 0.1);
  }
</style>
