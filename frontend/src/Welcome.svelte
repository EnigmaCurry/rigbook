<script>
  import { onMount, createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  let callsign = "";
  let grid = "";
  let qrzKey = "";
  let logbookName = "rigbook";
  let existingLogbooks = [];
  let saving = false;
  let error = "";

  onMount(async () => {
    try {
      const res = await fetch("/api/logbooks/");
      if (res.ok) {
        const data = await res.json();
        existingLogbooks = data.map(d => d.name);
        if (existingLogbooks.length > 0) {
          logbookName = existingLogbooks[0]; // most recently opened
        }
      }
    } catch {}
  });

  async function saveGlobal(key, value) {
    if (!value) return;
    await fetch(`/api/global-settings/${key}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    });
  }

  async function finish() {
    saving = true;
    error = "";
    try {
      // Save any filled-in global defaults
      await saveGlobal("my_callsign", callsign.trim().toUpperCase());
      await saveGlobal("my_grid", normalizeGrid(grid.trim()));
      await saveGlobal("qrz_password", qrzKey.trim());

      // Save logbook name as default and mark welcome acknowledged
      const name = logbookName.trim() || "rigbook";
      await saveGlobal("default_logbook_name", name);
      await saveGlobal("welcome_acknowledged", "true");
      const res = await fetch("/api/logbooks/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) {
        // Logbook doesn't exist yet — create it
        const createRes = await fetch("/api/logbooks/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        });
        if (!createRes.ok) {
          const data = await createRes.json().catch(() => null);
          error = data?.detail || "Failed to create logbook";
          saving = false;
          return;
        }
      }

      dispatch("complete", { logbook: name });
    } catch (e) {
      error = e.message || "Something went wrong";
      saving = false;
    }
  }

  async function skip() {
    saving = true;
    error = "";
    try {
      await saveGlobal("welcome_acknowledged", "true");
      dispatch("complete", { logbook: null });
    } catch (e) {
      error = e.message || "Something went wrong";
      saving = false;
    }
  }

  function normalizeGrid(g) {
    let out = "";
    for (let i = 0; i < g.length && out.length < 6; i++) {
      const c = g[i];
      const pos = out.length;
      if (pos < 2) {
        if (/[A-Ra-r]/.test(c)) out += c.toUpperCase();
      } else if (pos < 4) {
        if (/[0-9]/.test(c)) out += c;
      } else {
        if (/[A-Xa-x]/.test(c)) out += c.toLowerCase();
      }
    }
    return out;
  }

  function onNameKeydown(e) {
    if (!/[a-zA-Z0-9_-]/.test(e.key) && e.key.length === 1) {
      e.preventDefault();
    }
  }

  function validateName(name) {
    if (name.startsWith("__")) return "Name must not start with '__'";
    if (name && !/^[a-zA-Z0-9_-]+$/.test(name)) return "Letters, numbers, hyphens, underscores only";
    return "";
  }

  $: nameError = validateName(logbookName.trim());
</script>

<div class="welcome-overlay">
  <div class="welcome-panel">
    <h1>Welcome to Rigbook</h1>
    <p class="subtitle">Set up your station defaults. You can change these later in Settings.</p>

    <div class="fields">
      <div class="field">
        <label for="w-callsign">My Callsign</label>
        <input id="w-callsign" type="text" bind:value={callsign} on:input={() => { callsign = callsign.toUpperCase(); }} autocomplete="nope" data-1p-ignore data-lpignore="true" style="max-width: 10rem" placeholder="e.g. W1AW" />
      </div>

      <div class="field">
        <label for="w-grid">My Grid Square</label>
        <input id="w-grid" type="text" bind:value={grid} on:input={() => { grid = normalizeGrid(grid.slice(0, 6)); }} autocomplete="nope" data-1p-ignore data-lpignore="true" maxlength="6" style="max-width: 10rem" placeholder="e.g. AB12xy" />
      </div>

      <div class="field">
        <label for="w-qrz">QRZ Password <span class="optional">(optional)</span></label>
        <input id="w-qrz" type="text" class="secret-field" bind:value={qrzKey} autocomplete="nope" data-1p-ignore data-lpignore="true" data-form-type="other" placeholder="For callsign lookups" />
      </div>

      <div class="field">
        <label for="w-logbook">Default Logbook Name</label>
        {#if existingLogbooks.length > 0}
          <select id="w-logbook" bind:value={logbookName} style="max-width: 14rem">
            {#each existingLogbooks as name}
              <option value={name}>{name}</option>
            {/each}
          </select>
        {:else}
          <input id="w-logbook" type="text" bind:value={logbookName} autocomplete="nope" on:keydown={onNameKeydown} placeholder="rigbook" style="max-width: 14rem" />
          {#if nameError}
            <span class="field-error">{nameError}</span>
          {:else}
            <span class="hint">Letters, numbers, hyphens, underscores only</span>
          {/if}
        {/if}
      </div>
    </div>

    {#if error}
      <p class="error">{error}</p>
    {/if}

    <div class="actions">
      <button class="skip-link" on:click={skip} disabled={saving}>Skip</button>
      <button class="continue-btn" on:click={finish} disabled={saving || !!nameError}>
        {saving ? "Setting up..." : "Continue"}
      </button>
    </div>
  </div>
</div>

<style>
  .welcome-overlay {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg, #1a1b1e);
    z-index: 1000;
  }

  .welcome-panel {
    background: var(--bg-card, #24252b);
    border: 1px solid var(--border, #3a3b3f);
    border-radius: 12px;
    padding: 2rem 2.5rem;
    max-width: 420px;
    width: 90vw;
  }

  h1 {
    margin: 0 0 0.25rem;
    font-size: 1.5rem;
    color: var(--text, #eaeaea);
  }

  .subtitle {
    margin: 0 0 1.5rem;
    font-size: 0.85rem;
    color: var(--text-dim, #888);
  }

  .fields {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .field label {
    font-size: 0.8rem;
    color: var(--text-dim, #888);
  }

  .field select,
  .field input {
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--border, #3a3b3f);
    border-radius: 4px;
    background: var(--bg-input, transparent);
    color: var(--text, #eaeaea);
    font-size: 0.9rem;
  }

  .optional {
    font-style: italic;
    opacity: 0.6;
  }

  .hint {
    font-size: 0.7rem;
    color: var(--text-dim, #888);
  }

  .error, .field-error {
    color: #ff4444;
    font-size: 0.7rem;
  }
  .error {
    margin: 0.75rem 0 0;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 1rem;
    margin-top: 1.5rem;
  }

  .skip-link {
    background: none;
    border: none;
    color: var(--text-dim, #888);
    font-size: 0.8rem;
    cursor: pointer;
    padding: 0.4rem 0.8rem;
    text-decoration: underline;
  }

  .skip-link:hover {
    color: var(--text, #eaeaea);
  }

  .continue-btn {
    background: var(--accent, #00ff88);
    color: #000;
    border: none;
    border-radius: 6px;
    padding: 0.5rem 1.5rem;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
  }

  .continue-btn:hover {
    opacity: 0.9;
  }

  .continue-btn:disabled, .skip-link:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .secret-field {
    -webkit-text-security: disc;
  }
  .secret-field:focus {
    -webkit-text-security: none;
  }
</style>
