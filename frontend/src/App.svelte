<script>
  import { onMount, onDestroy } from "svelte";
  import Logbook from "./Logbook.svelte";
  import ExportImport from "./ExportImport.svelte";
  import Hunting from "./Hunting.svelte";
  import Search from "./Search.svelte";
  import Settings from "./Settings.svelte";
  import About from "./About.svelte";

  function parseHash() {
    const hash = window.location.hash.slice(1) || "/";
    if (hash === "/about") return { page: "about", editId: null };
    if (hash === "/settings") return { page: "settings", editId: null };
    if (hash === "/logbook") return { page: "log", editId: null };
    if (hash === "/export") return { page: "export", editId: null };
    if (hash === "/add") return { page: "add", editId: null };
    const match = hash.match(/^\/log\/(\d+)$/);
    if (match) return { page: "add", editId: parseInt(match[1], 10) };
    return { page: "hunting", editId: null };
  }

  let { page, editId } = parseHash();
  let prefill = null;
  let menuOpen = false;
  let myCallsign = "";
  let vfoFreq = "";
  let vfoMode = "";
  let vfoConnected = false;
  let vfoEditing = false;
  let vfoFreqInput;
  let vfoEditFreq = "";
  let vfoEditMode = "";
  let flrigInterval;

  async function pollFlrig() {
    try {
      const res = await fetch("/api/flrig/status");
      if (res.ok) {
        const data = await res.json();
        vfoFreq = data.freq || "";
        vfoMode = data.mode || "";
        vfoConnected = data.connected;
      }
    } catch {
      vfoFreq = "";
      vfoMode = "";
      vfoConnected = false;
    }
  }

  function formatFreq(f) {
    if (!f) return "";
    const n = parseFloat(f) / 1000;
    if (isNaN(n)) return f;
    return parseFloat(n.toFixed(1)).toString() + " KHz";
  }

  function startVfoEdit() {
    vfoEditFreq = vfoFreq ? String(parseFloat(vfoFreq) / 1000) : "";
    vfoEditMode = vfoMode;
    vfoEditing = true;
    // Focus after Svelte renders the input
    setTimeout(() => vfoFreqInput?.focus(), 0);
  }

  async function saveVfo() {
    const freqHz = vfoEditFreq ? String(parseFloat(vfoEditFreq) * 1000) : null;
    try {
      await fetch("/api/flrig/vfo", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ freq: freqHz }),
      });
    } catch {}
    vfoEditing = false;
    pollFlrig();
  }

  function cancelVfoEdit() {
    vfoEditing = false;
  }

  async function fetchCallsign() {
    try {
      const res = await fetch("/api/settings/my_callsign");
      if (res.ok) {
        const data = await res.json();
        myCallsign = data.value || "";
      }
    } catch {}
  }

  function navigate(p) {
    page = p;
    editId = null;
    menuOpen = false;
    const paths = { hunting: "/", log: "/logbook", add: "/add", export: "/export", settings: "/settings", about: "/about" };
    window.location.hash = paths[p] || "/";
    fetchCallsign();
  }

  async function tuneAndPrefill(spot) {
    try {
      await fetch("/api/flrig/vfo", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ freq: String(parseFloat(spot.frequency) * 1000), mode: spot.mode }),
      });
      pollFlrig();
    } catch {}
    prefill = {
      call: spot.activator || "",
      freq: spot.frequency || "",
      mode: spot.mode || "",
      pota_park: spot.reference || "",
      grid: spot.grid4 || "",
      country: "",
      state: "",
    };
    const loc = spot.locationDesc || "";
    if (loc.startsWith("US-")) {
      prefill.country = "United States";
    }
    navigate("add");
  }

  function handleSearchAction(e) {
    const { type, data } = e.detail;
    if (type === "logbook") {
      editId = data.id;
      navigate("add");
      window.location.hash = `/log/${data.id}`;
    } else if (type === "pota") {
      tuneAndPrefill(data);
    } else if (type === "skcc") {
      prefill = {
        call: data.call || "",
        freq: "",
        mode: "",
        pota_park: "",
        grid: "",
        country: "",
        state: "",
        skcc: data.skcc || "",
      };
      navigate("add");
    } else if (type === "qrz") {
      prefill = {
        call: data.call || "",
        freq: "",
        mode: "",
        pota_park: "",
        grid: data.grid || "",
        country: data.country || "",
        state: data.state || "",
      };
      navigate("add");
    }
  }

  function onHashChange() {
    const parsed = parseHash();
    page = parsed.page;
    editId = parsed.editId;
    fetchCallsign();
  }

  // Apply theme from localStorage on load
  function applyTheme() {
    const stored = localStorage.getItem("rigbook-theme");
    const theme = stored || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    document.documentElement.classList.toggle("light", theme === "light");
  }

  let searchComponent;

  function onGlobalKeydown(e) {
    // Ignore if typing in an input/textarea/select
    const tag = e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

    if (e.key === "n" || e.key === "N") {
      e.preventDefault();
      navigate("add");
    } else if (e.key === "/") {
      e.preventDefault();
      searchComponent?.focus();
    } else if (e.key === "h" || e.key === "H") {
      e.preventDefault();
      navigate("hunting");
    } else if (e.key === "l" || e.key === "L") {
      e.preventDefault();
      navigate("log");
    } else if (e.key === "t" || e.key === "T") {
      e.preventDefault();
      startVfoEdit();
    } else if (e.key === "?") {
      e.preventDefault();
      navigate("about");
    }
  }

  onMount(() => {
    applyTheme();
    window.addEventListener("storage", applyTheme);
    window.addEventListener("keydown", onGlobalKeydown);
    fetchCallsign();
    pollFlrig();
    flrigInterval = setInterval(pollFlrig, 2000);
    window.addEventListener("hashchange", onHashChange);
  });

  onDestroy(() => {
    clearInterval(flrigInterval);
    window.removeEventListener("hashchange", onHashChange);
    window.removeEventListener("storage", applyTheme);
    window.removeEventListener("keydown", onGlobalKeydown);
  });
</script>

<main>
  <header>
    <div class="header-left">
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
      <h1 on:click={() => navigate("hunting")} style="cursor: pointer">Rigbook</h1>
      {#if myCallsign}
        <span class="callsign">{myCallsign}</span>
      {/if}
      {#if vfoEditing}
        <span class="vfo-edit">
          <input bind:this={vfoFreqInput} type="text" bind:value={vfoEditFreq} class="vfo-input freq" placeholder="Freq" on:keydown={e => e.key === "Enter" && saveVfo()} />
          <button class="vfo-btn save" on:click={saveVfo}>Set</button>
          <button class="vfo-btn cancel" on:click={cancelVfoEdit}>X</button>
        </span>
      {:else if vfoConnected}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <span class="vfo" on:click={startVfoEdit} title="Click to change VFO">📻 {formatFreq(vfoFreq)}</span>
      {:else}
        <span class="vfo disconnected" title="Radio not connected">📻 ❌</span>
      {/if}
    </div>
    <Search bind:this={searchComponent} on:action={handleSearchAction} />
    <div class="hamburger-wrap">
      <button class="hamburger" on:click={() => menuOpen = !menuOpen} aria-label="Menu">
        <span class="bar"></span>
        <span class="bar"></span>
        <span class="bar"></span>
      </button>
      {#if menuOpen}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div class="menu-backdrop" on:click={() => menuOpen = false}></div>
        <nav class="menu">
          <button class="menu-item" class:active={page === "log"} on:click={() => navigate("log")}>Logbook</button>
          <button class="menu-item" class:active={page === "add"} on:click={() => navigate("add")}>Add QSO</button>
          <button class="menu-item" class:active={page === "hunting"} on:click={() => navigate("hunting")}>Hunting</button>
          <button class="menu-item" class:active={page === "export"} on:click={() => navigate("export")}>Export / Import</button>
          <button class="menu-item" class:active={page === "settings"} on:click={() => navigate("settings")}>Settings</button>
          <button class="menu-item" class:active={page === "about"} on:click={() => navigate("about")}>About</button>
        </nav>
      {/if}
    </div>
  </header>

  {#if page === "log"}
    <div class="log-header">
      <button class="btn-add" on:click={() => navigate("add")}>Add QSO</button>
    </div>
    <Logbook showForm={false} {vfoFreq} {vfoMode} on:editchange={e => { editId = e.detail; navigate("add"); window.location.hash = `/log/${e.detail}`; }} on:navigate={e => navigate(e.detail)} />
  {:else if page === "add"}
    <Logbook showForm={true} {editId} {prefill} {vfoFreq} {vfoMode} on:editchange={e => { editId = e.detail; window.location.hash = e.detail ? `/log/${e.detail}` : "/add"; }} on:navigate={e => navigate(e.detail)} on:prefillconsumed={() => prefill = null} />
  {:else if page === "hunting"}
    <Hunting on:tune={e => tuneAndPrefill(e.detail)} />
  {:else if page === "export"}
    <ExportImport />
  {:else if page === "settings"}
    <Settings />
  {:else if page === "about"}
    <About />
  {/if}
</main>

<style>
  :global(:root) {
    --bg: #3b3d4a;
    --bg-card: #4a4c5a;
    --bg-input: #5a5c6a;
    --bg-deep: #11111b;
    --border: #5a5c6a;
    --border-input: #6e7080;
    --text: #eaeaea;
    --text-muted: #b0b2be;
    --text-dim: #8a8c98;
    --text-dimmer: #6e7080;
    --accent: #00ff88;
    --accent-hover: #00cc6a;
    --accent-callsign: #ffcc00;
    --accent-vfo: #00ccff;
    --accent-delete: #cc3333;
    --accent-delete-hover: #aa2222;
    --accent-error: #ff6b6b;
    --btn-secondary: #6e7080;
    --btn-secondary-hover: #5a5c6a;
    --row-hover: #44465a;
    --row-editing: #3a5a3a;
    --bar-color: #eaeaea;
    --menu-bg: #4a4c5a;
    --menu-hover: #5a5c6a;
  }

  :global(:root.light) {
    --bg: #e8e8ec;
    --bg-card: #f4f4f6;
    --bg-input: #ffffff;
    --bg-deep: #f0f0f2;
    --border: #c8c8d0;
    --border-input: #b0b0b8;
    --text: #1a1a2e;
    --text-muted: #555566;
    --text-dim: #777788;
    --text-dimmer: #999aaa;
    --accent: #00994d;
    --accent-hover: #007a3d;
    --accent-callsign: #b8860b;
    --accent-vfo: #0077aa;
    --accent-delete: #cc3333;
    --accent-delete-hover: #aa2222;
    --accent-error: #cc2222;
    --btn-secondary: #aaaabc;
    --btn-secondary-hover: #9999ab;
    --row-hover: #dddde4;
    --row-editing: #c8ecc8;
    --bar-color: #333344;
    --menu-bg: #f4f4f6;
    --menu-hover: #e0e0e8;
  }

  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family: "Courier New", Courier, monospace;
    font-size: 14px;
  }

  main {
    max-width: 1100px;
    margin: 0 auto;
    padding: 1rem;
  }

  header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
  }

  .header-left {
    display: flex;
    align-items: baseline;
    gap: 1rem;
  }

  h1 {
    margin: 0;
    color: var(--accent);
    font-size: 1.6rem;
  }

  .callsign {
    color: var(--accent-callsign);
    font-size: 1.2rem;
    font-weight: bold;
  }

  .vfo {
    color: var(--accent-vfo);
    font-size: 1rem;
    cursor: pointer;
  }

  .vfo:not(.disconnected):hover {
    text-decoration: underline;
  }

  .vfo.disconnected {
    cursor: default;
    opacity: 0.6;
  }

  .vfo-edit {
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }

  .vfo-input {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--accent-vfo);
    padding: 0.15rem 0.4rem;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
    outline: none;
  }

  .vfo-input.freq {
    width: 100px;
  }

  .vfo-input.mode {
    width: 60px;
  }

  .vfo-input:focus {
    border-color: var(--accent-vfo);
  }

  .vfo-btn {
    padding: 0.15rem 0.5rem;
    font-size: 0.75rem;
    border-radius: 3px;
    border: none;
    cursor: pointer;
    font-family: inherit;
    font-weight: bold;
  }

  .vfo-btn.save {
    background: var(--accent-vfo);
    color: var(--bg);
  }

  .vfo-btn.cancel {
    background: var(--btn-secondary);
    color: var(--text);
  }

  .log-header {
    margin-bottom: 1rem;
  }

  .btn-add {
    background: var(--accent);
    color: var(--bg);
    border: none;
    padding: 0.6rem 2rem;
    font-family: inherit;
    font-size: 1rem;
    font-weight: bold;
    border-radius: 4px;
    cursor: pointer;
  }

  .btn-add:hover {
    background: var(--accent-hover);
  }

  .hamburger-wrap {
    position: relative;
  }

  .hamburger {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.3rem;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .hamburger:hover {
    background: none;
  }

  .bar {
    display: block;
    width: 22px;
    height: 2px;
    background: var(--bar-color);
    border-radius: 1px;
  }

  .menu-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 99;
  }

  .menu {
    position: absolute;
    top: 100%;
    right: 0;
    background: var(--menu-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    min-width: 150px;
    z-index: 100;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .menu-item {
    background: none;
    border: none;
    color: var(--text);
    padding: 0.6rem 1rem;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: normal;
    text-align: left;
    cursor: pointer;
    border-radius: 0;
  }

  .menu-item:hover {
    background: var(--menu-hover);
  }

  .menu-item.active {
    color: var(--accent);
    font-weight: bold;
  }
</style>
