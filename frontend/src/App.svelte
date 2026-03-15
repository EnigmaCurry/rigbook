<script>
  import { onMount } from "svelte";
  import Logbook from "./Logbook.svelte";
  import Settings from "./Settings.svelte";

  function parseHash() {
    const hash = window.location.hash.slice(1) || "/";
    if (hash === "/settings") return { page: "settings", editId: null };
    const match = hash.match(/^\/log\/(\d+)$/);
    if (match) return { page: "logbook", editId: parseInt(match[1], 10) };
    return { page: "logbook", editId: null };
  }

  let { page, editId } = parseHash();
  let menuOpen = false;
  let myCallsign = "";

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
    window.location.hash = p === "settings" ? "/settings" : "/";
    if (p === "logbook") fetchCallsign();
  }

  function onHashChange() {
    const parsed = parseHash();
    page = parsed.page;
    editId = parsed.editId;
    if (page === "logbook") fetchCallsign();
  }

  onMount(() => {
    fetchCallsign();
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  });
</script>

<main>
  <header>
    <div class="header-left">
      <h1>Rigbook</h1>
      {#if myCallsign}
        <span class="callsign">{myCallsign}</span>
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
          <button class="menu-item" class:active={page === "logbook"} on:click={() => navigate("logbook")}>Logbook</button>
          <button class="menu-item" class:active={page === "settings"} on:click={() => navigate("settings")}>Settings</button>
        </nav>
      {/if}
    </div>
  </header>

  {#if page === "logbook"}
    <Logbook {editId} on:editchange={e => { window.location.hash = e.detail ? `/log/${e.detail}` : "/"; }} />
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
