<script>
  import { onMount } from "svelte";
  import Logbook from "./Logbook.svelte";
  import Settings from "./Settings.svelte";

  function parseHash() {
    const hash = window.location.hash.slice(1) || "/";
    if (hash === "/settings") return { page: "settings", editId: null };
    if (hash === "/add") return { page: "add", editId: null };
    const match = hash.match(/^\/log\/(\d+)$/);
    if (match) return { page: "add", editId: parseInt(match[1], 10) };
    return { page: "log", editId: null };
  }

  let { page, editId } = parseHash();
  let menuOpen = false;
  let myCallsign = "";
  let vfoFreq = "";
  let vfoMode = "";
  let vfoEditing = false;
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
      }
    } catch {
      vfoFreq = "";
      vfoMode = "";
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
    const paths = { log: "/", add: "/add", settings: "/settings" };
    window.location.hash = paths[p] || "/";
    fetchCallsign();
  }

  function onHashChange() {
    const parsed = parseHash();
    page = parsed.page;
    editId = parsed.editId;
    fetchCallsign();
  }

  onMount(() => {
    fetchCallsign();
    pollFlrig();
    flrigInterval = setInterval(pollFlrig, 2000);
    window.addEventListener("hashchange", onHashChange);
    return () => {
      clearInterval(flrigInterval);
      window.removeEventListener("hashchange", onHashChange);
    };
  });
</script>

<main>
  <header>
    <div class="header-left">
      <h1>Rigbook</h1>
      {#if myCallsign}
        <span class="callsign">{myCallsign}</span>
      {/if}
      {#if vfoEditing}
        <span class="vfo-edit">
          <input type="text" bind:value={vfoEditFreq} class="vfo-input freq" placeholder="Freq" on:keydown={e => e.key === "Enter" && saveVfo()} />
          <button class="vfo-btn save" on:click={saveVfo}>Set</button>
          <button class="vfo-btn cancel" on:click={cancelVfoEdit}>X</button>
        </span>
      {:else if vfoFreq}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <span class="vfo" on:click={startVfoEdit} title="Click to change VFO">{formatFreq(vfoFreq)}</span>
      {/if}
    </div>
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
          <button class="menu-item" class:active={page === "settings"} on:click={() => navigate("settings")}>Settings</button>
        </nav>
      {/if}
    </div>
  </header>

  {#if page === "log"}
    <div class="log-header">
      <button class="btn-add" on:click={() => navigate("add")}>Add QSO</button>
    </div>
    <Logbook showForm={false} on:editchange={e => { editId = e.detail; navigate("add"); window.location.hash = `/log/${e.detail}`; }} on:navigate={e => navigate(e.detail)} />
  {:else if page === "add"}
    <Logbook showForm={true} {editId} on:editchange={e => { editId = e.detail; window.location.hash = e.detail ? `/log/${e.detail}` : "/add"; }} on:navigate={e => navigate(e.detail)} />
  {:else if page === "settings"}
    <Settings />
  {/if}
</main>

<style>
  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    background: #3b3d4a;
    color: #eaeaea;
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
    border-bottom: 1px solid #5a5c6a;
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
    color: #00ff88;
    font-size: 1.6rem;
  }

  .callsign {
    color: #ffcc00;
    font-size: 1.2rem;
    font-weight: bold;
  }

  .vfo {
    color: #00ccff;
    font-size: 1rem;
    cursor: pointer;
  }

  .vfo:hover {
    text-decoration: underline;
  }

  .vfo-edit {
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }

  .vfo-input {
    background: #5a5c6a;
    border: 1px solid #6e7080;
    color: #00ccff;
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
    border-color: #00ccff;
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
    background: #00ccff;
    color: #1a1a2e;
  }

  .vfo-btn.cancel {
    background: #6e7080;
    color: #eaeaea;
  }

  .log-header {
    margin-bottom: 1rem;
  }

  .btn-add {
    background: #00ff88;
    color: #1a1a2e;
    border: none;
    padding: 0.6rem 2rem;
    font-family: inherit;
    font-size: 1rem;
    font-weight: bold;
    border-radius: 4px;
    cursor: pointer;
  }

  .btn-add:hover {
    background: #00cc6a;
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
    background: #eaeaea;
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
    background: #4a4c5a;
    border: 1px solid #5a5c6a;
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
    color: #eaeaea;
    padding: 0.6rem 1rem;
    font-family: inherit;
    font-size: 0.9rem;
    font-weight: normal;
    text-align: left;
    cursor: pointer;
    border-radius: 0;
  }

  .menu-item:hover {
    background: #5a5c6a;
  }

  .menu-item.active {
    color: #00ff88;
    font-weight: bold;
  }
</style>
