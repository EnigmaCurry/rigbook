<script>
  import { onMount, onDestroy } from "svelte";

  let my_callsign = "";
  let my_grid = "";
  let default_rst = "599";
  let qrz_password = "";
  let hasQrzPassword = false;
  let flrig_host = "localhost";
  let flrig_port = "12345";
  let wide_breakpoint = "1200";
  let wide_mode_enabled = true;
  let theme = localStorage.getItem("rigbook-theme") || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  let saving = false;
  let message = "";
  let qrzStatus = null; // { ok, error?, username? }
  let qrzChecking = false;

  // RBN settings
  let rbn_enabled = false;
  let rbn_host = "telnet.reversebeacon.net";
  let rbn_port = "7001";

  // HamAlert settings
  let hamalert_enabled = false;
  let hamalert_host = "hamalert.org";
  let hamalert_port = "7300";
  let hamalert_username = "";
  let hamalert_password = "";
  let hasHamalertPassword = false;

  // Feed connection status
  let spotStatus = { rbn: { connected: false, enabled: false }, hamalert: { connected: false, enabled: false } };
  let spotStatusInterval;

  function toggleTheme() {
    theme = theme === "dark" ? "light" : "dark";
    localStorage.setItem("rigbook-theme", theme);
    document.documentElement.classList.toggle("light", theme === "light");
  }

  async function clearCache() {
    try {
      await Promise.all([
        fetch("/api/qrz/cache", { method: "DELETE" }),
        fetch("/api/skcc/cache", { method: "DELETE" }),
      ]);
      message = "Cache cleared.";
    } catch {
      message = "Failed to clear cache.";
    }
  }

  $: stripCallsign = () => { my_callsign = my_callsign.replace(/\s/g, ""); };
  $: stripGrid = () => { my_grid = my_grid.replace(/[^A-Za-z0-9]/g, ""); };

  async function fetchSpotStatus() {
    try {
      const res = await fetch("/api/spots/status");
      if (res.ok) spotStatus = await res.json();
    } catch {}
  }

  async function fetchSettings() {
    try {
      const res = await fetch("/api/settings/");
      if (res.ok) {
        const data = await res.json();
        for (const s of data) {
          if (s.key === "my_callsign") my_callsign = s.value || "";
          if (s.key === "my_grid") my_grid = s.value || "";
          if (s.key === "default_rst") default_rst = s.value || "599";
          if (s.key === "qrz_password") hasQrzPassword = !!s.value && s.value !== "";
          if (s.key === "flrig_host") flrig_host = s.value || "localhost";
          if (s.key === "flrig_port") flrig_port = s.value || "12345";
          if (s.key === "rbn_enabled") rbn_enabled = s.value === "true";
          if (s.key === "rbn_host") rbn_host = s.value || "telnet.reversebeacon.net";
          if (s.key === "rbn_port") rbn_port = s.value || "7000";
          if (s.key === "hamalert_enabled") hamalert_enabled = s.value === "true";
          if (s.key === "hamalert_host") hamalert_host = s.value || "hamalert.org";
          if (s.key === "hamalert_port") hamalert_port = s.value || "7300";
          if (s.key === "hamalert_username") hamalert_username = s.value || "";
          if (s.key === "hamalert_password") hasHamalertPassword = !!s.value && s.value !== "";
          if (s.key === "wide_breakpoint") {
            if (s.value === "0") {
              wide_mode_enabled = false;
              wide_breakpoint = "1200";
            } else {
              wide_mode_enabled = true;
              wide_breakpoint = s.value || "1500";
            }
          }
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
      await fetch("/api/settings/default_rst", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: default_rst.trim() }),
      });
      if (qrz_password.trim()) {
        await fetch("/api/settings/qrz_password", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: qrz_password.trim() }),
        });
        hasQrzPassword = true;
        qrz_password = "";
      }
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
      await fetch("/api/settings/wide_breakpoint", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: wide_mode_enabled ? String(wide_breakpoint) : "0" }),
      });
      // RBN settings
      await fetch("/api/settings/rbn_enabled", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: rbn_enabled ? "true" : "false" }),
      });
      await fetch("/api/settings/rbn_host", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: rbn_host.trim() }),
      });
      await fetch("/api/settings/rbn_port", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: rbn_port.trim() }),
      });
      // HamAlert settings
      await fetch("/api/settings/hamalert_enabled", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: hamalert_enabled ? "true" : "false" }),
      });
      await fetch("/api/settings/hamalert_host", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: hamalert_host.trim() }),
      });
      await fetch("/api/settings/hamalert_port", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: hamalert_port.trim() }),
      });
      await fetch("/api/settings/hamalert_username", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: hamalert_username.trim() }),
      });
      if (hamalert_password.trim()) {
        await fetch("/api/settings/hamalert_password", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: hamalert_password.trim() }),
        });
        hasHamalertPassword = true;
        hamalert_password = "";
      }
      // Restart feeds to apply changes
      await fetch("/api/spots/restart", { method: "POST" });
      setTimeout(fetchSpotStatus, 2000);
      message = "Settings saved.";
    } catch (e) {
      message = `Error: ${e.message}`;
    }
    saving = false;
  }

  async function checkQrz() {
    qrzChecking = true;
    qrzStatus = null;
    try {
      const res = await fetch("/api/qrz/status");
      if (res.ok) qrzStatus = await res.json();
    } catch {
      qrzStatus = { ok: false, error: "Request failed" };
    }
    qrzChecking = false;
  }

  onMount(() => {
    fetchSettings();
    fetchSpotStatus();
    spotStatusInterval = setInterval(fetchSpotStatus, 5000);
  });

  onDestroy(() => {
    clearInterval(spotStatusInterval);
  });
</script>

<div class="settings">
  <h2>Settings</h2>

  <section class="settings-section">
    <h3>Station</h3>
    <div class="setting-row">
      <label for="my_callsign">My Callsign</label>
      <input id="my_callsign" type="text" bind:value={my_callsign} on:input={stripCallsign} maxlength="10" autocomplete="off" style="text-transform: uppercase" />
    </div>
    <div class="setting-row">
      <label for="my_grid">My Grid Square</label>
      <input id="my_grid" type="text" bind:value={my_grid} on:input={stripGrid} autocomplete="off" style="text-transform: uppercase" />
    </div>
    <div class="setting-row">
      <label for="default_rst">Default RST</label>
      <input id="default_rst" type="text" bind:value={default_rst} autocomplete="off" />
    </div>
  </section>

  <section class="settings-section">
    <h3>QRZ</h3>
    <div class="setting-row">
      <label for="qrz_password">{hasQrzPassword ? "Change QRZ Password" : "QRZ Password"}</label>
      <input id="qrz_password" type="password" bind:value={qrz_password} autocomplete="off" disabled={!my_callsign.trim()} placeholder={hasQrzPassword ? "Leave blank to keep current" : ""} />
      <span class="hint">{#if !my_callsign.trim()}Set My Callsign first{:else if hasQrzPassword}Leave blank to remain unchanged{:else}Your QRZ account password (uses My Callsign as username){/if}</span>
    </div>
    {#if hasQrzPassword}
      <div class="setting-row qrz-status-row">
        <button class="theme-toggle" on:click={checkQrz} disabled={qrzChecking}>
          {qrzChecking ? "Checking..." : "Test QRZ Connection"}
        </button>
        {#if qrzStatus}
          {#if qrzStatus.ok}
            <span class="qrz-ok">Connected as {qrzStatus.username}</span>
          {:else}
            <span class="qrz-error">{qrzStatus.error}</span>
          {/if}
        {/if}
      </div>
    {/if}
  </section>

  <section class="settings-section">
    <h3>Appearance</h3>
    <div class="setting-row toggle-row">
      <label>Theme</label>
      <button class="theme-toggle" on:click={toggleTheme}>
        {theme === "dark" ? "Dark" : "Light"}
      </button>
    </div>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={wide_mode_enabled} />
        Wide Mode
      </label>
    </div>
    <div class="setting-row">
      <label for="wide_breakpoint">Breakpoint: {wide_breakpoint}px</label>
      <input id="wide_breakpoint" type="range" min="1200" max="2500" step="50" bind:value={wide_breakpoint} disabled={!wide_mode_enabled} />
    </div>
  </section>

  <section class="settings-section">
    <h3>flrig Connection</h3>
    <div class="setting-row">
      <label for="flrig_host">flrig Host</label>
      <input id="flrig_host" type="text" bind:value={flrig_host} autocomplete="off" />
    </div>
    <div class="setting-row">
      <label for="flrig_port">flrig Port</label>
      <input id="flrig_port" type="text" bind:value={flrig_port} autocomplete="off" inputmode="numeric" />
    </div>
  </section>

  <section class="settings-section">
    <h3>Reverse Beacon Network (RBN)</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={rbn_enabled} />
        Enable RBN Feed
      </label>
      <span class="conn-status">
        <span class="dot" class:green={spotStatus.rbn.connected} class:red={spotStatus.rbn.enabled && !spotStatus.rbn.connected} class:off={!spotStatus.rbn.enabled}></span>
        {#if !spotStatus.rbn.enabled}Disabled{:else if spotStatus.rbn.connected}Connected{:else}Connecting...{/if}
      </span>
    </div>
    <div class="setting-row">
      <label for="rbn_host">RBN Host</label>
      <input id="rbn_host" type="text" bind:value={rbn_host} autocomplete="off" />
    </div>
    <div class="setting-row">
      <label for="rbn_port">RBN Port</label>
      <input id="rbn_port" type="text" bind:value={rbn_port} autocomplete="off" inputmode="numeric" />
    </div>
    <p class="hint">RBN uses your My Callsign to authenticate.</p>
  </section>

  <section class="settings-section">
    <h3>HamAlert</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={hamalert_enabled} />
        Enable HamAlert Feed
      </label>
      <span class="conn-status">
        <span class="dot" class:green={spotStatus.hamalert.connected} class:red={spotStatus.hamalert.enabled && !spotStatus.hamalert.connected} class:off={!spotStatus.hamalert.enabled}></span>
        {#if !spotStatus.hamalert.enabled}Disabled{:else if spotStatus.hamalert.connected}Connected{:else}Connecting...{/if}
      </span>
    </div>
    <div class="setting-row">
      <label for="hamalert_host">Host</label>
      <input id="hamalert_host" type="text" bind:value={hamalert_host} autocomplete="off" />
    </div>
    <div class="setting-row">
      <label for="hamalert_port">Port</label>
      <input id="hamalert_port" type="text" bind:value={hamalert_port} autocomplete="off" inputmode="numeric" />
    </div>
    <div class="setting-row">
      <label for="hamalert_username">Username</label>
      <input id="hamalert_username" type="text" bind:value={hamalert_username} autocomplete="off" />
    </div>
    <div class="setting-row">
      <label for="hamalert_password">{hasHamalertPassword ? "Change Password" : "Password"}</label>
      <input id="hamalert_password" type="password" bind:value={hamalert_password} autocomplete="off" placeholder={hasHamalertPassword ? "Leave blank to keep current" : ""} />
    </div>
  </section>

  <section class="settings-section">
    <h3>Cache</h3>
    <div class="setting-row toggle-row">
      <button class="theme-toggle" on:click={clearCache}>Clear Cache</button>
    </div>
  </section>

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
    color: var(--accent);
    font-size: 1.2rem;
    margin: 0 0 1rem 0;
  }

  .settings-section {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
  }

  h3 {
    color: var(--accent);
    font-size: 0.9rem;
    margin: 0 0 0.75rem 0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
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
    color: var(--text-muted);
  }

  input:not([type="range"]):not([type="checkbox"]) {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 0.4rem 0.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    border-radius: 3px;
    width: 100%;
  }

  input:not([type="range"]):not([type="checkbox"]):focus {
    outline: none;
    border-color: var(--accent);
  }

  input[type="range"] {
    width: 100%;
    accent-color: var(--accent);
  }

  input[type="range"]:disabled {
    opacity: 0.4;
  }

  input[type="checkbox"] {
    accent-color: var(--accent);
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
  }

  button:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .hint {
    font-size: 0.7rem;
    color: var(--text-dim);
  }

  .message {
    color: var(--accent);
    font-size: 0.85rem;
    margin-left: 0.5rem;
  }

  .toggle-row {
    flex-direction: row;
    align-items: center;
    gap: 0.75rem;
  }

  .theme-toggle {
    background: var(--btn-secondary);
    color: var(--text);
    padding: 0.3rem 1rem;
    font-size: 0.85rem;
  }

  .theme-toggle:hover {
    background: var(--btn-secondary-hover);
  }

  .qrz-status-row {
    flex-direction: row;
    align-items: center;
    gap: 0.75rem;
  }

  .qrz-ok {
    color: var(--accent);
    font-size: 0.85rem;
  }

  .qrz-error {
    color: var(--accent-error);
    font-size: 0.85rem;
  }

  .conn-status {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-left: auto;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    background: var(--text-dim);
  }
  .dot.green { background: #4caf50; }
  .dot.red { background: #f44336; }
  .dot.off { background: var(--text-dim); opacity: 0.4; }

  p.hint {
    font-size: 0.7rem;
    color: var(--text-dim);
    margin: 0;
  }
</style>
