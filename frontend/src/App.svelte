<script>
  import { onMount, onDestroy } from "svelte";
  import Logbook from "./Logbook.svelte";
  import ExportImport from "./ExportImport.svelte";
  import Hunting from "./Hunting.svelte";
  import BandPlan from "./BandPlan.svelte";
  import GridMap from "./GridMap.svelte";
  import Search from "./Search.svelte";
  import Settings from "./Settings.svelte";
  import About from "./About.svelte";
  import Parks from "./Parks.svelte";
  import Links from "./Links.svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";

  const BANDS = [
    { name: "160m", lo: 1800, hi: 2000, segments: [
      { label: "CW", lo: 1800, hi: 2000 }, { label: "SSB", lo: 1800, hi: 2000 },
    ]},
    { name: "80m", lo: 3500, hi: 4000, segments: [
      { label: "CW", lo: 3500, hi: 4000 }, { label: "SSB", lo: 3600, hi: 4000 },
    ]},
    { name: "60m", lo: 5330, hi: 5410, segments: [
      { label: "CW", lo: 5330, hi: 5410 }, { label: "Digi", lo: 5330, hi: 5410 }, { label: "USB", lo: 5330, hi: 5410 },
    ]},
    { name: "40m", lo: 7000, hi: 7300, segments: [
      { label: "CW", lo: 7000, hi: 7300 }, { label: "SSB", lo: 7125, hi: 7300 },
    ]},
    { name: "30m", lo: 10100, hi: 10150, segments: [
      { label: "CW", lo: 10100, hi: 10150 }, { label: "SSB", lo: 10100, hi: 10150 },
    ]},
    { name: "20m", lo: 14000, hi: 14350, segments: [
      { label: "CW", lo: 14000, hi: 14350 }, { label: "SSB", lo: 14150, hi: 14350 },
    ]},
    { name: "17m", lo: 18068, hi: 18168, segments: [
      { label: "CW", lo: 18068, hi: 18168 }, { label: "SSB", lo: 18110, hi: 18168 },
    ]},
    { name: "15m", lo: 21000, hi: 21450, segments: [
      { label: "CW", lo: 21000, hi: 21450 }, { label: "SSB", lo: 21200, hi: 21450 },
    ]},
    { name: "12m", lo: 24890, hi: 24990, segments: [
      { label: "CW", lo: 24890, hi: 24990 }, { label: "SSB", lo: 24930, hi: 24990 },
    ]},
    { name: "10m", lo: 28000, hi: 29700, segments: [
      { label: "CW", lo: 28000, hi: 29700 }, { label: "SSB", lo: 28300, hi: 29700 },
    ]},
    { name: "6m", lo: 50000, hi: 54000, segments: [
      { label: "CW", lo: 50000, hi: 54000 }, { label: "SSB", lo: 50100, hi: 54000 },
    ]},
    { name: "2m", lo: 144000, hi: 148000, segments: [
      { label: "CW", lo: 144000, hi: 148000 }, { label: "SSB", lo: 144100, hi: 148000 },
    ]},
  ];

  const VFO_MODE_MAP = {
    "CW": "CW", "CW-R": "CW", "CWR": "CW",
    "LSB": "SSB", "USB": "SSB", "SSB": "SSB", "AM": "SSB",
    "FM": "FM",
    "FT8": "Digi", "FT4": "Digi", "RTTY": "Digi", "RTTY-R": "Digi",
    "PSK31": "Digi", "PSK": "Digi", "DIGI": "Digi", "DATA": "Digi",
    "JS8": "Digi", "OLIVIA": "Digi",
  };

  function freqToBand(f) {
    const n = parseFloat(f);
    if (isNaN(n)) return "";
    const b = BANDS.find(b => n >= b.lo && n <= b.hi);
    return b ? b.name : "";
  }

  const SSB_BW = 3; // KHz typical SSB bandwidth
  const EDGE_MARGIN = 1;

  function freqToBandForMode(f, mode) {
    const n = parseFloat(f);
    if (isNaN(n)) return "";
    const b = BANDS.find(b => n >= b.lo && n <= b.hi);
    if (!b) return "";
    const upper = mode?.toUpperCase() || "";
    const segLabel = VFO_MODE_MAP[upper] || "";
    if (!segLabel) return b.name;
    const seg = b.segments.find(s => s.label === segLabel);
    if (!seg) return b.name;
    const loMargin = upper === "LSB" ? SSB_BW : EDGE_MARGIN;
    const hiMargin = upper === "USB" ? SSB_BW : EDGE_MARGIN;
    return (n >= seg.lo + loMargin && n <= seg.hi - hiMargin) ? b.name : "";
  }

  function parseHash() {
    const hash = window.location.hash.slice(1) || "/";
    if (hash === "/grid") return { page: "grid", editId: null };
    if (hash === "/parks" || hash.startsWith("/parks/")) return { page: "parks", editId: null };
    if (hash === "/about") return { page: "about", editId: null };
    if (hash === "/links") return { page: "links", editId: null };
    if (hash === "/settings") return { page: "settings", editId: null };
    if (hash === "/logbook") return { page: isWide() ? "dual" : "log", editId: null };
    if (hash === "/export") return { page: "export", editId: null };
    if (hash === "/add") return { page: isWide() ? "dual" : "add", editId: null };
    if (hash === "/hunting") return { page: isWide() ? "dual" : "hunting", editId: null };
    if (hash === "/dual") return { page: "dual", editId: null };
    const match = hash.match(/^\/log\/(\d+)$/);
    if (match) return { page: isWide() ? "dual" : "add", editId: parseInt(match[1], 10) };
    return { page: isWide() ? "dual" : "log", editId: null };
  }

  let wideBreakpoint = 1500;
  let wide = typeof window !== "undefined" && window.innerWidth >= 1500;
  let { page, editId } = parseHash();
  let previousPage = "log";
  let prefill = null;
  let dualShowForm = !!editId || (page === "dual" && (window.location.hash.slice(1) === "/add"));
  let dualHunting;
  let gridMapValue = "";
  let menuOpen = false;
  let myCallsign = "";
  let vfoFreq = "";
  let vfoMode = "";
  let vfoConnected = false;
  let vfoEditing = false;
  let vfoFreqInput;
  let radioModes = [];
  let vfoEditFreq = "";
  let vfoEditMode = "";
  let flrigInterval;
  let utcNow = new Date().toISOString().slice(0, 19).replace("T", " ") + "z";
  let clockInterval;
  let clockCopied = false;

  async function copyUtcTimestamp() {
    try {
      await navigator.clipboard.writeText(utcNow);
      clockCopied = true;
      setTimeout(() => { clockCopied = false; }, 1500);
    } catch {}
  }

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
    const khz = parseFloat(f) / 1000;
    if (isNaN(khz)) return f;
    return parseFloat(khz.toFixed(1)).toString();
  }

  // Split frequency into individual digit objects for wheel tuning
  // Each digit gets a place value in Hz for increment/decrement
  function freqDigits(f) {
    if (!f) return [];
    const hz = parseFloat(f);
    if (isNaN(hz)) return [];
    const khz = hz / 1000;
    const str = khz.toFixed(3);

    // Find the decimal point position to calculate place values
    const dotIdx = str.indexOf(".");
    const digits = [];
    for (let i = 0; i < str.length; i++) {
      if (str[i] === ".") {
        digits.push({ char: ".", placeHz: 0 });
        continue;
      }
      // Position relative to decimal: chars before dot have positive powers
      const posFromDot = dotIdx >= 0 ? (i < dotIdx ? dotIdx - i : dotIdx - i + 1) : str.length - i;
      // Convert place value from display unit to Hz
      const unitMultiplier = 1e3; // KHz->Hz
      const placeHz = Math.round(Math.pow(10, posFromDot - 1) * unitMultiplier);
      digits.push({ char: str[i], placeHz });
    }
    return digits;
  }

  $: vfoDigits = freqDigits(vfoFreq);

  // Svelte action to capture wheel events non-passively (required for preventDefault)
  function nonPassiveWheel(node) {
    function handler(e) {
      e.preventDefault();
      if (vfoEditing) return;
      const target = e.target.closest(".vfo-digit");
      if (!target || !target.dataset.placehz) return;
      const placeHz = parseInt(target.dataset.placehz);
      if (!placeHz) return;
      const hz = parseFloat(vfoFreq) || 0;
      const delta = e.deltaY < 0 ? placeHz : -placeHz;
      const newHz = Math.max(0, hz + delta);
      vfoFreq = String(newHz);
      fetch("/api/flrig/vfo", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ freq: String(newHz) }),
      }).catch(() => {});
    }
    node.addEventListener("wheel", handler, { passive: false });
    return { destroy() { node.removeEventListener("wheel", handler); } };
  }

  function startVfoEdit() {
    vfoEditFreq = vfoFreq ? String(parseFloat(vfoFreq) / 1000) : "";
    vfoEditMode = vfoMode;
    vfoEditing = true;
    // Focus after Svelte renders the input
    setTimeout(() => { vfoFreqInput?.focus(); vfoFreqInput?.select(); }, 0);
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

  async function fetchRadioModes() {
    try {
      const res = await fetch("/api/flrig/modes");
      if (res.ok) radioModes = await res.json();
    } catch {}
  }

  async function cycleMode() {
    if (!radioModes.length) await fetchRadioModes();
    if (!radioModes.length || !vfoMode) return;
    const idx = radioModes.indexOf(vfoMode);
    const next = radioModes[(idx + 1) % radioModes.length];
    try {
      await fetch("/api/flrig/vfo", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: next }),
      });
      vfoMode = next;
    } catch {}
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

  function isWide() {
    return typeof window !== "undefined" && window.innerWidth >= wideBreakpoint;
  }

  function goHome() {
    navigate(isWide() ? "dual" : "log");
  }

  async function fetchWideBreakpoint() {
    try {
      const res = await fetch("/api/settings/wide_breakpoint");
      if (res.ok) {
        const data = await res.json();
        const v = parseInt(data.value, 10);
        if (v === 0) wideBreakpoint = Infinity;
        else if (v > 0) wideBreakpoint = v;
      }
    } catch {}
    wide = isWide();
  }

  function navigate(p) {
    if (p === "back") {
      p = previousPage;
    }
    if (p === "add" && isWide()) p = "dual";
    if (page !== p) previousPage = page;
    page = p;
    editId = null;
    menuOpen = false;
    const paths = { hunting: "/hunting", log: "/logbook", dual: "/dual", add: "/add", grid: "/grid", parks: "/parks", export: "/export", settings: "/settings", links: "/links", about: "/about" };
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
    if (page === "dual") dualShowForm = true;
    else navigate("add");
  }

  function handleSearchAction(e) {
    const { type, data } = e.detail;
    if (type === "logbook") {
      editId = data.id;
      dualShowForm = true;
      navigate(isWide() ? "dual" : "add");
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
      dualShowForm = true;
      navigate(isWide() ? "dual" : "add");
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
      dualShowForm = true;
      navigate(isWide() ? "dual" : "add");
    }
  }

  function onHashChange() {
    const parsed = parseHash();
    page = parsed.page;
    editId = parsed.editId;
    fetchCallsign();
    fetchWideBreakpoint();
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
      dualShowForm = true; prefill = null; editId = null;
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
    } else if (e.key === "p" || e.key === "P") {
      e.preventDefault();
      navigate("parks");
    } else if (e.key === "m" || e.key === "M") {
      e.preventDefault();
      cycleMode();
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
    fetchWideBreakpoint();
    fetchRadioModes();
    pollFlrig();
    flrigInterval = setInterval(pollFlrig, 2000);
    clockInterval = setInterval(() => { utcNow = new Date().toISOString().slice(0, 19).replace("T", " ") + "z"; }, 1000);
    window.addEventListener("hashchange", onHashChange);
    window.addEventListener("resize", onResize);
  });

  function onResize() {
    wide = isWide();
    if (page === "dual" && !wide) {
      navigate("log");
    } else if ((page === "log" || page === "hunting") && wide) {
      navigate("dual");
    }
  }

  onDestroy(() => {
    clearInterval(flrigInterval);
    clearInterval(clockInterval);
    window.removeEventListener("hashchange", onHashChange);
    window.removeEventListener("resize", onResize);
    window.removeEventListener("storage", applyTheme);
    window.removeEventListener("keydown", onGlobalKeydown);
  });
</script>

<main class:dual-mode={page === "dual"} class:wide-mode={page === "grid"}>
  <header>
    <div class="header-left">
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
      <h1 class="app-title" on:click={goHome} style="cursor: pointer"><span class="title-full">Rigbook</span><span class="title-short">RB</span></h1>
      {#if myCallsign}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <span class="callsign" on:click={goHome} style="cursor: pointer">{myCallsign}</span>
      {/if}
      {#if vfoEditing}
        <span class="vfo-edit">
          <div class="vfo-freq-wrap">
            <input bind:this={vfoFreqInput} type="text" bind:value={vfoEditFreq} class="vfo-input freq" placeholder="Freq"
              on:keydown={e => { if (e.key === "Enter") saveVfo(); if (e.key === "Escape") cancelVfoEdit(); }}
            />
            <BandPlan currentFreq={vfoEditFreq} currentMode={vfoMode} on:tune={async e => {
              vfoEditFreq = String(e.detail);
              await saveVfo();
            }} />
          </div>
          <button class="vfo-btn save" on:click={saveVfo}>Set</button>
          <button class="vfo-btn cancel" on:click={cancelVfoEdit}>X</button>
        </span>
      {:else if vfoConnected}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <span class="vfo-bezel" use:nonPassiveWheel>
          <span class="vfo-icon" on:click={startVfoEdit}>📻</span>
          {#each vfoDigits as d, i}
            {#if d.char === "."}
              <!-- dot is merged into the next digit -->
            {:else}
              {@const prevDot = i > 0 && vfoDigits[i-1]?.char === "."}
              <span class="vfo-digit" data-placehz={d.placeHz} on:click={startVfoEdit} title="Scroll to tune">{prevDot ? "." : ""}{d.char}</span>
            {/if}
          {/each}
          {#if freqToBandForMode(parseFloat(vfoFreq) / 1000, vfoMode)}
            <span class="band-tag" style="background: {bandColor(freqToBandForMode(parseFloat(vfoFreq) / 1000, vfoMode))}; color: {bandTextColor(freqToBandForMode(parseFloat(vfoFreq) / 1000, vfoMode))}" on:click={startVfoEdit}>{freqToBandForMode(parseFloat(vfoFreq) / 1000, vfoMode)}</span>
          {/if}
        </span>
        {#if vfoMode}
          <!-- svelte-ignore a11y-click-events-have-key-events -->
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <span class="vfo-mode" on:click={cycleMode} title="Click or press M to cycle mode">{vfoMode}</span>
        {/if}
      {:else}
        <span class="vfo disconnected" title="Radio not connected">❌ No Radio</span>
      {/if}
    </div>
    <Search bind:this={searchComponent} on:action={handleSearchAction} />
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <span class="utc-clock" on:click={copyUtcTimestamp} title="Click to copy">{clockCopied ? "Copied!" : utcNow}</span>
    <div class="hamburger-wrap">
      {#if wide}
        <button class="add-btn dual-btn" on:click={() => navigate("dual")} title="Logbook & Hunting">📖🧭</button>
      {:else}
        <button class="add-btn" on:click={() => navigate("log")} title="Logbook">📖</button>
        <button class="add-btn" on:click={() => navigate("hunting")} title="Hunting">🧭</button>
      {/if}
      <button class="add-btn parks-btn" on:click={() => navigate("parks")} title="My Parks">🌲</button>
      <button class="add-btn" on:click={() => { dualShowForm = true; prefill = null; editId = null; if (page === "dual") { /* already on dual */ } else navigate("add"); }} title="Add QSO">+</button>
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
          <button class="menu-item" class:active={page === "grid"} on:click={() => navigate("grid")}>Grid Map</button>
          <button class="menu-item" class:active={page === "parks"} on:click={() => navigate("parks")}>Parks</button>
          <button class="menu-item" class:active={page === "export"} on:click={() => navigate("export")}>Export / Import</button>
          <button class="menu-item" class:active={page === "settings"} on:click={() => navigate("settings")}>Settings</button>
          <button class="menu-item" class:active={page === "links"} on:click={() => navigate("links")}>Links</button>
          <button class="menu-item" class:active={page === "about"} on:click={() => navigate("about")}>About</button>
        </nav>
      {/if}
    </div>
  </header>

  {#if page === "log"}
    <Logbook showForm={false} {vfoFreq} {vfoMode} on:editchange={e => { editId = e.detail; navigate("add"); window.location.hash = `/log/${e.detail}`; }} on:navigate={e => navigate(e.detail)} />
  {:else if page === "add"}
    <Logbook showForm={true} {editId} {prefill} {vfoFreq} {vfoMode} on:editchange={e => { editId = e.detail; window.location.hash = e.detail ? `/log/${e.detail}` : "/add"; }} on:navigate={e => navigate(e.detail)} on:prefillconsumed={() => prefill = null} />
  {:else if page === "hunting"}
    <Hunting on:tune={e => tuneAndPrefill(e.detail)} />
  {:else if page === "dual"}
    <div class="dual-layout">
      <div class="dual-pane">
        <Logbook showForm={dualShowForm || !!prefill || !!editId} {prefill} {editId} {vfoFreq} {vfoMode} on:editchange={e => { editId = e.detail; dualShowForm = !!e.detail; }} on:navigate={e => { if (e.detail === "hunting" || e.detail === "log" || e.detail === "back") { prefill = null; editId = null; dualShowForm = false; dualHunting?.refreshAwards(); } else navigate(e.detail); }} on:prefillconsumed={() => prefill = null} />
      </div>
      <div class="dual-pane">
        <Hunting bind:this={dualHunting} on:tune={e => tuneAndPrefill(e.detail)} />
      </div>
    </div>
  {:else if page === "parks"}
    <Parks on:addqso={e => { prefill = e.detail; dualShowForm = true; navigate(isWide() ? "dual" : "add"); }} />
  {:else if page === "grid"}
    <GridMap bind:value={gridMapValue} on:select={e => { gridMapValue = e.detail; }} />
  {:else if page === "export"}
    <ExportImport />
  {:else if page === "settings"}
    <Settings />
  {:else if page === "links"}
    <Links />
  {:else if page === "about"}
    <About />
  {/if}
</main>

<style>
  :global(:root) {
    --bg: #24252b;
    --bg-card: #2a2d3e;
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
    --vfo-bg: #111218;
    --vfo-border: #555;
    --vfo-text: #00ccff;
    --accent-delete: #cc3333;
    --accent-delete-hover: #aa2222;
    --accent-error: #ff6b6b;
    --btn-secondary: #6e7080;
    --btn-secondary-hover: #5a5c6a;
    --row-hover: #44465a;
    --row-editing: #3a5a3a;
    --bar-color: #eaeaea;
    --menu-bg: #2e303a;
    --menu-hover: #3e404a;
  }

  :global(:root.light) {
    --bg: #e8e8ff;
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
    --accent-vfo: #332525;
    --vfo-bg: #0c1e88;
    --vfo-border: #0c1e88;
    --vfo-text: #fbfbfb;
    --accent-delete: #cc3333;
    --accent-delete-hover: #aa2222;
    --accent-error: #cc2222;
    --btn-secondary: #aaaabc;
    --btn-secondary-hover: #9999ab;
    --row-hover: #dddde4;
    --row-editing: #c8ecc8;
    --bar-color: #333344;
    --menu-bg: #d8d8e0;
    --menu-hover: #c8c8d4;
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
    align-items: center;
    justify-content: space-between;
    user-select: none;
    flex-wrap: wrap;
    gap: 0.5rem;
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

  .vfo-bezel {
    display: inline-flex;
    align-items: center;
    gap: 0;
    background: var(--vfo-bg);
    border: 2px solid var(--vfo-border);
    border-radius: 6px;
    padding: 0.15rem 0.5rem;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.05);
    position: relative;
    top: -2px;
  }

  .vfo-digit {
    color: var(--vfo-text);
    font-size: 1.1rem;
    font-family: monospace;
    font-weight: bold;
    cursor: ns-resize;
    padding: 0 1px;
    border-radius: 2px;
    transition: background 0.1s;
  }

  .vfo-digit:hover {
    background: rgba(255,255,255,0.12);
  }

  .vfo-bezel .vfo-icon {
    cursor: pointer;
    margin-right: 0.3rem;
  }

  .vfo {
    color: var(--accent-vfo);
    font-size: 1rem;
    cursor: pointer;
    position: relative;
    top: -2px;
  }

  .band-tag {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: bold;
    padding: 0.1rem 0.35rem;
    border-radius: 8px;
    margin-left: 0.3rem;
    cursor: pointer;
  }

  .vfo-mode {
    color: var(--accent);
    font-size: 0.9rem;
    font-weight: bold;
    cursor: pointer;
  }

  .vfo-mode:hover {
    text-decoration: underline;
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

  .vfo-freq-wrap {
    position: relative;
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



  .hamburger-wrap {
    position: relative;
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .utc-clock {
    font-size: 0.75rem;
    color: var(--text-dim);
    font-family: monospace;
    cursor: pointer;
    white-space: nowrap;
  }

  .add-btn {
    background: #638676;
    color: #fff;
    border: none;
    font-size: 1.2rem;
    font-weight: bold;
    width: 28px;
    height: 28px;
    line-height: 1;
    border-radius: 4px;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .add-btn.dual-btn {
    width: auto;
    padding: 0 0.4rem;
    font-size: 0.9rem;
  }

  .add-btn:hover {
    background: #4a6e5e;
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
    z-index: 10001;
  }

  .menu {
    position: absolute;
    top: 100%;
    right: 0;
    background: var(--menu-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    min-width: 150px;
    z-index: 10002;
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

  .title-short {
    display: none;
  }

  main.dual-mode {
    max-width: 100%;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding-bottom: 0;
  }

  main.wide-mode {
    max-width: 1600px;
  }

  .dual-layout {
    display: flex;
    gap: 1.5rem;
    flex: 1;
    min-height: 0;
  }

  .dual-pane {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
  }

  @media (max-width: 600px) {
    .title-full {
      display: none;
    }
    .title-short {
      display: inline;
    }
  }
</style>
