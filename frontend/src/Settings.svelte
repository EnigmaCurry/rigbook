<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";

  export let logbookName = "";
  export let pickerMode = false;
  export let needsSetup = false;

  const dispatch = createEventDispatcher();

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
  let rbn_feed_cw = true;
  let rbn_feed_digital = false;
  let skcc_skimmer_enabled = false;
  let skcc_skimmer_distance = "500";

  // HamAlert settings
  let hamalert_enabled = false;
  let hamalert_host = "hamalert.org";
  let hamalert_port = "7300";
  let hamalert_username = "";
  let hamalert_password = "";
  let hasHamalertPassword = false;

  // Desktop notifications
  let desktopNotifPermission = typeof Notification !== "undefined" ? Notification.permission : "denied";
  let desktopNotifEnabled = localStorage.getItem("desktop_notifications_enabled") === "true";
  let popupNotifEnabled = localStorage.getItem("popup_notifications_enabled") === "true";
  let testPending = false;

  // Danger zone
  let deleteConfirmName = "";
  let deleteError = "";
  let deleting = false;

  async function deleteLogbook() {
    if (deleteConfirmName !== logbookName) {
      deleteError = "Name does not match";
      return;
    }
    if (!confirm(`Are you sure you want to permanently delete "${logbookName}"? This cannot be undone.`)) {
      return;
    }
    deleteError = "";
    deleting = true;
    try {
      const res = await fetch("/api/logbooks/delete", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: logbookName }),
      });
      if (res.ok) {
        const data = await res.json();
        dispatch("deleted", { shutdown: data.shutdown });
      } else {
        const data = await res.json();
        deleteError = data.detail || "Failed to delete logbook";
      }
    } catch {
      deleteError = "Failed to delete logbook";
    }
    deleting = false;
  }

  async function shutdownServer() {
    if (!confirm("Are you sure you want to shut down the Rigbook server?")) return;
    dispatch("shutdown");
    try {
      await fetch("/api/logbooks/shutdown", { method: "POST" });
    } catch {}
    dispatch("deleted", { shutdown: true });
  }

  async function enableDesktopNotifications() {
    if (typeof Notification === "undefined") return;
    const perm = await Notification.requestPermission();
    desktopNotifPermission = perm;
    if (perm === "granted") {
      desktopNotifEnabled = true;
      localStorage.setItem("desktop_notifications_enabled", "true");
    }
  }

  function disableDesktopNotifications() {
    desktopNotifEnabled = false;
    localStorage.setItem("desktop_notifications_enabled", "false");
  }

  async function sendTestNotification() {
    // Ensure permission is granted before testing
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      const perm = await Notification.requestPermission();
      desktopNotifPermission = perm;
      if (perm === "granted") {
        desktopNotifEnabled = true;
        localStorage.setItem("desktop_notifications_enabled", "true");
      }
    }
    testPending = true;
    try {
      await fetch("/api/notifications/test", { method: "POST" });
    } catch {}
    setTimeout(() => { testPending = false; }, 5000);
  }

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
          if (s.key === "rbn_feeds") {
            const feeds = (s.value || "cw").split(",").map(f => f.trim().toLowerCase());
            rbn_feed_cw = feeds.includes("cw");
            rbn_feed_digital = feeds.includes("digital");
          }
          if (s.key === "skcc_skimmer_enabled") skcc_skimmer_enabled = s.value === "true";
          if (s.key === "skcc_skimmer_distance") skcc_skimmer_distance = s.value || "500";
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
      const rbnFeeds = [rbn_feed_cw ? "cw" : "", rbn_feed_digital ? "digital" : ""].filter(Boolean).join(",");
      await fetch("/api/settings/rbn_feeds", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: rbnFeeds || "cw" }),
      });
      await fetch("/api/settings/skcc_skimmer_enabled", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: skcc_skimmer_enabled ? "true" : "false" }),
      });
      await fetch("/api/settings/skcc_skimmer_distance", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: skcc_skimmer_distance.trim() || "500" }),
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
      if (my_callsign.trim() && my_grid.trim()) {
        dispatch("setupcomplete");
      }
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

  {#if needsSetup}
    <p class="setup-hint">Enter your callsign and grid square to get started.</p>
  {/if}

  <section class="settings-section">
    <h3>Station</h3>
    <div class="setting-row">
      <label for="my_callsign">My Callsign{#if needsSetup && !my_callsign.trim()} <span class="required">*</span>{/if}</label>
      <input id="my_callsign" type="text" bind:value={my_callsign} on:input={stripCallsign} maxlength="10" autocomplete="off" style="text-transform: uppercase" class:input-required={needsSetup && !my_callsign.trim()} />
    </div>
    <div class="setting-row">
      <label for="my_grid">My Grid Square{#if needsSetup && !my_grid.trim()} <span class="required">*</span>{/if}</label>
      <input id="my_grid" type="text" bind:value={my_grid} on:input={stripGrid} autocomplete="off" style="text-transform: uppercase" class:input-required={needsSetup && !my_grid.trim()} />
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
    <h3>Notifications</h3>
    <div class="setting-row toggle-row">
      {#if desktopNotifPermission === "denied"}
        <span class="hint">Desktop notifications blocked by browser. Allow notifications for this site in your browser settings.</span>
      {:else if desktopNotifPermission === "granted" && desktopNotifEnabled}
        <span style="font-size:0.85rem; color:var(--accent);">Desktop notifications enabled</span>
        <button class="theme-toggle" on:click={disableDesktopNotifications}>Disable</button>
      {:else if desktopNotifPermission === "granted" && !desktopNotifEnabled}
        <span style="font-size:0.85rem; color:var(--text-muted);">Desktop notifications disabled</span>
        <button class="theme-toggle" on:click={() => { desktopNotifEnabled = true; localStorage.setItem("desktop_notifications_enabled", "true"); }}>Enable</button>
      {:else}
        <button class="theme-toggle" on:click={enableDesktopNotifications}>Enable Desktop Notifications</button>
      {/if}
    </div>
    <p class="hint">In-app notifications are always enabled. Desktop notifications show browser popups when new alerts arrive.</p>
    <div class="setting-row toggle-row" style="margin-top: 0.5rem;">
      <label>
        <input type="checkbox" bind:checked={popupNotifEnabled} on:change={() => localStorage.setItem("popup_notifications_enabled", popupNotifEnabled ? "true" : "false")} />
        Popup notifications
      </label>
    </div>
    <p class="hint">Show a modal dialog immediately when new notifications arrive. Harder to miss, but more intrusive.</p>
    <div class="setting-row toggle-row" style="margin-top: 0.5rem;">
      <button class="theme-toggle" on:click={sendTestNotification} disabled={testPending}>
        {testPending ? "Sending in 5s..." : "Send Test Notification"}
      </button>
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
    <div class="setting-row toggle-row">
      <label><input type="checkbox" bind:checked={rbn_feed_cw} disabled={!rbn_enabled} /> CW (port 7000)</label>
      <label><input type="checkbox" bind:checked={rbn_feed_digital} disabled={!rbn_enabled} /> Digital (port 7001)</label>
    </div>
    <div class="setting-row">
      <label for="rbn_host">RBN Host</label>
      <input id="rbn_host" type="text" bind:value={rbn_host} autocomplete="off" disabled={!rbn_enabled} />
    </div>
    <div class="setting-row toggle-row">
      <label><input type="checkbox" bind:checked={skcc_skimmer_enabled} disabled={!rbn_enabled} /> Show SKCC Skimmer on Hunting page</label>
    </div>
    <div class="setting-row">
      <label for="skcc_distance">SKCC Skimmer max distance (miles)</label>
      <input id="skcc_distance" type="text" bind:value={skcc_skimmer_distance} autocomplete="off" inputmode="numeric" disabled={!rbn_enabled || !skcc_skimmer_enabled} />
    </div>
    <p class="hint">Uses your My Callsign to authenticate.</p>
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
      <input id="hamalert_host" type="text" bind:value={hamalert_host} autocomplete="off" disabled={!hamalert_enabled} />
    </div>
    <div class="setting-row">
      <label for="hamalert_port">Port</label>
      <input id="hamalert_port" type="text" bind:value={hamalert_port} autocomplete="off" inputmode="numeric" disabled={!hamalert_enabled} />
    </div>
    <div class="setting-row">
      <label for="hamalert_username">Telnet Username</label>
      <input id="hamalert_username" type="text" bind:value={hamalert_username} autocomplete="off" disabled={!hamalert_enabled} />
    </div>
    <div class="setting-row">
      <label for="hamalert_password">{hasHamalertPassword ? "Change Telnet Password" : "Telnet Password"}</label>
      <input id="hamalert_password" type="password" bind:value={hamalert_password} autocomplete="off" disabled={!hamalert_enabled} placeholder={hasHamalertPassword ? "Leave blank to keep current" : ""} />
    </div>
  </section>

  <section class="settings-section">
    <h3>Cache</h3>
    <p class="hint">Cached data: QRZ callsign lookups, SKCC member list. Clearing forces fresh lookups on next use.</p>
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

  {#if logbookName}
    <section class="settings-section danger-zone">
      <h3>Danger Zone</h3>
      <p class="danger-text">Permanently delete the logbook <strong>{logbookName}</strong> and all its data. This cannot be undone.</p>
      <div class="setting-row">
        <label for="delete-confirm">Type <strong>{logbookName}</strong> to confirm</label>
        <input id="delete-confirm" type="text" bind:value={deleteConfirmName} placeholder={logbookName} autocomplete="off" />
      </div>
      {#if deleteError}
        <p class="danger-error">{deleteError}</p>
      {/if}
      <div class="setting-row">
        <button class="danger-btn" on:click={deleteLogbook} disabled={deleting || deleteConfirmName !== logbookName}>
          {deleting ? "Deleting..." : "Delete Logbook"}
        </button>
      </div>
      <div class="danger-separator"></div>
      <div class="setting-row">
        <button class="danger-btn" on:click={shutdownServer}>Shutdown Server</button>
      </div>
    </section>
  {/if}
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

  input:disabled, select:disabled {
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

  .setup-hint {
    color: var(--accent);
    font-size: 0.95rem;
    margin: 0 0 1rem;
    font-weight: 600;
  }

  .required {
    color: #ff4444;
    font-weight: bold;
  }

  :global(.input-required) {
    border-color: #ff4444 !important;
  }

  .danger-zone {
    border-color: #ff4444;
    margin-top: 2rem;
  }

  .danger-zone h3 {
    color: #ff4444;
  }

  .danger-text {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin: 0 0 0.75rem;
    line-height: 1.4;
  }

  .danger-error {
    color: #ff6666;
    font-size: 0.8rem;
    margin: 0 0 0.5rem;
  }

  .danger-separator {
    border-top: 1px solid #ff444444;
    margin: 0.75rem 0;
  }

  .danger-btn {
    background: #ff4444;
    color: #fff;
  }

  .danger-btn:hover:not(:disabled) {
    background: #cc3333;
  }

  .danger-btn:disabled {
    background: #ff4444;
    opacity: 0.4;
  }
</style>
