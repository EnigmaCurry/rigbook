<script>
  import { onMount } from "svelte";

  let my_callsign = "";
  let my_grid = "";
  let flrig_host = "localhost";
  let flrig_port = "12345";
  let saving = false;
  let message = "";

  $: stripCallsign = () => { my_callsign = my_callsign.replace(/\s/g, ""); };
  $: stripGrid = () => { my_grid = my_grid.replace(/[^A-Za-z0-9]/g, ""); };

  async function fetchSettings() {
    try {
      const res = await fetch("/api/settings/");
      if (res.ok) {
        const data = await res.json();
        for (const s of data) {
          if (s.key === "my_callsign") my_callsign = s.value || "";
          if (s.key === "my_grid") my_grid = s.value || "";
          if (s.key === "flrig_host") flrig_host = s.value || "localhost";
          if (s.key === "flrig_port") flrig_port = s.value || "12345";
        }
      }
    } catch {}
  }

  async function save() {
    saving = true;
    message = "";
    try {
      await fetch("/api/settings/my_callsign", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: my_callsign.trim().toUpperCase() }),
      });
      await fetch("/api/settings/my_grid", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: my_grid.trim().toUpperCase() }),
      });
      await fetch("/api/settings/flrig_host", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: flrig_host.trim() }),
      });
      await fetch("/api/settings/flrig_port", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: flrig_port.trim() }),
      });
      message = "Settings saved.";
    } catch (e) {
      message = `Error: ${e.message}`;
    }
    saving = false;
  }

  onMount(fetchSettings);
</script>

<div class="settings">
  <h2>Settings</h2>

  <div class="setting-row">
    <label for="my_callsign">My Callsign</label>
    <input id="my_callsign" type="text" bind:value={my_callsign} on:input={stripCallsign} maxlength="10" autocomplete="off" style="text-transform: uppercase" />
  </div>

  <div class="setting-row">
    <label for="my_grid">My Grid Square</label>
    <input id="my_grid" type="text" bind:value={my_grid} on:input={stripGrid} autocomplete="off" style="text-transform: uppercase" />
  </div>

  <h3>flrig Connection</h3>

  <div class="setting-row">
    <label for="flrig_host">flrig Host</label>
    <input id="flrig_host" type="text" bind:value={flrig_host} autocomplete="off" />
  </div>

  <div class="setting-row">
    <label for="flrig_port">flrig Port</label>
    <input id="flrig_port" type="text" bind:value={flrig_port} autocomplete="off" inputmode="numeric" />
  </div>

  <div class="setting-row">
    <button on:click={save} disabled={saving}>
      {saving ? "Saving..." : "Save"}
    </button>
    {#if message}
      <span class="message">{message}</span>
    {/if}
  </div>
</div>

<style>
  .settings {
    max-width: 400px;
  }

  h2 {
    color: #00ff88;
    font-size: 1.2rem;
    margin: 0 0 1rem 0;
  }

  h3 {
    color: #b0b2be;
    font-size: 0.95rem;
    margin: 1rem 0 0.5rem 0;
  }

  .setting-row {
    margin-bottom: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .setting-row:last-child {
    flex-direction: row;
    align-items: center;
  }

  label {
    font-size: 0.8rem;
    color: #b0b2be;
  }

  input {
    background: #5a5c6a;
    border: 1px solid #6e7080;
    color: #f0f0f0;
    padding: 0.4rem 0.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    border-radius: 3px;
    width: 100%;
  }

  input:focus {
    outline: none;
    border-color: #00ff88;
  }

  button {
    background: #00ff88;
    color: #1a1a2e;
    border: none;
    padding: 0.5rem 1.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: bold;
    border-radius: 3px;
    cursor: pointer;
  }

  button:hover:not(:disabled) {
    background: #00cc6a;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .message {
    color: #00ff88;
    font-size: 0.85rem;
    margin-left: 0.5rem;
  }
</style>
