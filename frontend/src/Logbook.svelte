<script>
  import { onMount, onDestroy, tick, createEventDispatcher } from "svelte";
  import Autocomplete from "./Autocomplete.svelte";
  import GridMap from "./GridMap.svelte";
  import ParkDetail from "./ParkDetail.svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";
  import { parkAward, parkAwardTitle } from "./parkAward.js";
  import { countryFlag, prefixFromRef } from "./countryFlag.js";
  import { storageGet, storageSet } from "./storage.js";

  export let editId = null;
  export let prefill = null;
  export let vfoFreq = "";
  export let vfoMode = "";
  const dispatch = createEventDispatcher();

  let contacts = [];

  // Form fields
  let call = "";
  let freq = "";
  let mode = "CW";
  let defaultRst = "599";
  let rst_sent = "599";
  let rst_recv = "599";
  let pota_park = "";
  let name = "";
  let qth = "";
  let state = "";
  let country = "";
  let dxcc = null;
  let dxccName = "";
  let grid = "";
  let skcc = "";
  let skcc_exch = false;
  let tableWrapEl;
  function utcNowDate() { return new Date().toISOString().slice(0, 10); }
  function utcNowTime() { return new Date().toISOString().slice(11, 19); }
  function normalizeTime() {
    const stripped = timePart.trim();
    // Already formatted with colons — just pad seconds if needed
    if (/^\d{2}:\d{2}$/.test(stripped)) {
      timePart = `${stripped}:00`;
      return;
    }
    // Digits only — insert colons
    const digits = stripped.replace(/\D/g, "");
    if (digits.length >= 4 && !stripped.includes(":")) {
      const h = digits.slice(0, 2);
      const m = digits.slice(2, 4);
      const s = digits.slice(4, 6) || "00";
      timePart = `${h}:${m}:${s}`;
    }
  }

  let datePart = "";
  let timePart = "";
  let datePartOff = "";
  let timePartOff = "";
  // Clock state machine: ROLLING_START -> ROLLING_END -> STATIC
  let clockState = "ROLLING_START";
  let clockInterval = null;

  function normalizeTimeOff() {
    const stripped = timePartOff.trim();
    if (/^\d{2}:\d{2}$/.test(stripped)) {
      timePartOff = `${stripped}:00`;
      return;
    }
    const digits = stripped.replace(/\D/g, "");
    if (digits.length >= 4 && !stripped.includes(":")) {
      const h = digits.slice(0, 2);
      const m = digits.slice(2, 4);
      const s = digits.slice(4, 6) || "00";
      timePartOff = `${h}:${m}:${s}`;
    }
  }

  function startRollingClock() {
    stopRollingClock();
    clockState = "ROLLING_START";
    datePartOff = "";
    timePartOff = "";
    clockInterval = setInterval(() => {
      if (clockState === "ROLLING_START") {
        datePart = utcNowDate();
        timePart = utcNowTime();
      } else if (clockState === "ROLLING_END") {
        datePartOff = utcNowDate();
        timePartOff = utcNowTime();
      }
    }, 1000);
    // Set initial values immediately
    datePart = utcNowDate();
    timePart = utcNowTime();
  }

  function stopRollingClock() {
    if (clockInterval) {
      clearInterval(clockInterval);
      clockInterval = null;
    }
  }

  function onStartClick() {
    if (clockState === "ROLLING_START") {
      // Freeze start time, begin rolling end
      clockState = "ROLLING_END";
      datePartOff = utcNowDate();
      timePartOff = utcNowTime();
    } else {
      // Override start time to now, restart end rolling
      datePart = utcNowDate();
      timePart = utcNowTime();
      clockState = "ROLLING_END";
      datePartOff = utcNowDate();
      timePartOff = utcNowTime();
      if (!clockInterval) {
        clockInterval = setInterval(() => {
          if (clockState === "ROLLING_END") {
            datePartOff = utcNowDate();
            timePartOff = utcNowTime();
          }
        }, 1000);
      }
    }
  }

  function onStopClick() {
    if (clockState === "ROLLING_END") {
      // Freeze end time
      clockState = "STATIC";
    } else if (clockState === "STATIC") {
      // Override end time to now
      datePartOff = utcNowDate();
      timePartOff = utcNowTime();
    }
  }

  function onStartFocus() {
    if (clockState === "ROLLING_START") {
      clockState = "ROLLING_END";
      datePartOff = utcNowDate();
      timePartOff = utcNowTime();
    }
  }

  function onEndFocus() {
    if (clockState === "ROLLING_END") {
      clockState = "STATIC";
    }
  }

  let comments = "";
  let notes = "";

  let countries = [];
  let subdivisions = [];
  let availableModes = [];
  $: countryItems = countries.map(c => ({ name: c.name, aliases: c.aliases || [], display: `${c.code} — ${c.name}` }));
  $: subdivisionNames = subdivisions.map(s => {
    const shortCode = s.code.includes("-") ? s.code.split("-")[1] : s.code;
    return { name: s.name, aliases: [shortCode, s.code], display: `${shortCode} — ${s.name}` };
  });

  function normalizeCountry() {
    if (!country || !countries.length) return;
    const upper = country.toUpperCase().trim();
    if (countries.some(c => c.name === country)) return;
    // Match by code (e.g. "US" -> "United States")
    const byCode = countries.find(c => c.code.toUpperCase() === upper);
    if (byCode) { country = byCode.name; onCountryChange(); return; }
    // Match by alias (e.g. "USA" -> "United States")
    const byAlias = countries.find(c => (c.aliases || []).some(a => a.toUpperCase() === upper));
    if (byAlias) { country = byAlias.name; onCountryChange(); return; }
  }

  function normalizeState() {
    if (!state || !subdivisions.length) return;
    const upper = state.toUpperCase().trim();
    // Already a full name match
    if (subdivisions.some(s => s.name === state)) return;
    // Match by code suffix (e.g. "UT" matches "US-UT")
    const byCode = subdivisions.find(s => s.code.split("-").pop() === upper);
    if (byCode) { state = byCode.name; return; }
    // Match by code (e.g. "US-UT")
    const byFull = subdivisions.find(s => s.code.toUpperCase() === upper);
    if (byFull) { state = byFull.name; return; }
  }
  let submitting = false;
  let errorMsg = "";
  let editingId = null;
  let editOriginal = null;
  let addOriginal = null;
  let userTouched = false;
  let showGridPicker = false;
  $: if (typeof document !== "undefined") {
    document.body.style.overflow = showGridPicker ? "hidden" : "";
  }
  export let showForm = true;
  export let formDirty = false;
  export let activePark = "";

  function formSnapshot() {
    return { call, freq, mode, rst_sent, rst_recv, pota_park, name, qth, state, country, grid, skcc, skcc_exch, comments, notes, datePart, timePart, datePartOff, timePartOff };
  }

  $: editHasChanges = !editingId || !editOriginal || (
    call !== editOriginal.call ||
    freq !== editOriginal.freq ||
    mode !== editOriginal.mode ||
    rst_sent !== editOriginal.rst_sent ||
    rst_recv !== editOriginal.rst_recv ||
    pota_park !== editOriginal.pota_park ||
    name !== editOriginal.name ||
    qth !== editOriginal.qth ||
    state !== editOriginal.state ||
    country !== editOriginal.country ||
    grid !== editOriginal.grid ||
    skcc !== editOriginal.skcc ||
    skcc_exch !== editOriginal.skcc_exch ||
    comments !== editOriginal.comments ||
    notes !== editOriginal.notes ||
    datePart !== editOriginal.datePart ||
    timePart !== editOriginal.timePart ||
    datePartOff !== editOriginal.datePartOff ||
    timePartOff !== editOriginal.timePartOff
  );
  $: missingFields = [
    !call.trim() && "Call",
    !freq.trim() && "Freq",
    !mode.trim() && "Mode",
  ].filter(Boolean);

  $: addHasChanges = !addOriginal ? false : (
    call !== addOriginal.call ||
    freq !== addOriginal.freq ||
    mode !== addOriginal.mode ||
    rst_sent !== addOriginal.rst_sent ||
    rst_recv !== addOriginal.rst_recv ||
    pota_park !== addOriginal.pota_park ||
    name !== addOriginal.name ||
    qth !== addOriginal.qth ||
    state !== addOriginal.state ||
    country !== addOriginal.country ||
    grid !== addOriginal.grid ||
    skcc !== addOriginal.skcc ||
    skcc_exch !== addOriginal.skcc_exch ||
    comments !== addOriginal.comments ||
    notes !== addOriginal.notes ||
    (clockState === "STATIC" && datePart !== addOriginal.datePart) ||
    (clockState === "STATIC" && timePart !== addOriginal.timePart) ||
    (clockState === "STATIC" && datePartOff !== addOriginal.datePartOff) ||
    (clockState === "STATIC" && timePartOff !== addOriginal.timePartOff)
  );

  $: formDirty = editingId ? editHasChanges : addHasChanges;
  $: orig = editingId ? editOriginal : addOriginal;
  $: activePark = showForm ? pota_park.trim().toUpperCase() : "";

  let sortCol = storageGet("logSortCol") || "timestamp";
  let sortAsc = storageGet("logSortAsc") === "true";

  const defaultColumnOrder = ["timestamp", "call", "name", "freq", "mode", "pota_park", "qth", "rst_sent", "rst_recv", "comments", "updated_at"];
  const flexColumns = new Set(["name", "qth", "comments"]);
  const columnDefs = {
    timestamp: { key: "timestamp", label: "UTC" },
    call: { key: "call", label: "Call" },
    name: { key: "name", label: "Name" },
    freq: { key: "freq", label: "Freq" },
    mode: { key: "mode", label: "Mode" },
    pota_park: { key: "pota_park", label: "POTA" },
    qth: { key: "qth", label: "QTH" },
    rst_sent: { key: "rst_sent", label: "RST S" },
    rst_recv: { key: "rst_recv", label: "RST R" },
    comments: { key: "comments", label: "Comments" },
    updated_at: { key: "updated_at", label: "Edited" },
  };

  function loadColumnOrder() {
    try {
      const saved = JSON.parse(storageGet("logColumnOrder"));
      if (Array.isArray(saved) && saved.every(k => columnDefs[k])) {
        const missing = defaultColumnOrder.filter(k => !saved.includes(k));
        const merged = [...saved.filter(k => columnDefs[k]), ...missing];
        if (merged.length === defaultColumnOrder.length) return merged;
      }
    } catch {}
    return [...defaultColumnOrder];
  }

  let columnOrder = loadColumnOrder();
  $: columns = columnOrder.map(k => columnDefs[k]);

  let dragCol = null;
  let dragOverCol = null;

  function onColDragStart(e, key) {
    dragCol = key;
    e.dataTransfer.effectAllowed = "move";
  }
  function onColDragOver(e, key) {
    e.preventDefault();
    dragOverCol = key;
  }
  function onColDrop(e, key) {
    e.preventDefault();
    if (dragCol && dragCol !== key) {
      const from = columnOrder.indexOf(dragCol);
      const to = columnOrder.indexOf(key);
      const newOrder = [...columnOrder];
      newOrder.splice(from, 1);
      newOrder.splice(to, 0, dragCol);
      columnOrder = newOrder;
      storageSet("logColumnOrder", JSON.stringify(columnOrder));
    }
    dragCol = null;
    dragOverCol = null;
  }
  function onColDragEnd() {
    dragCol = null;
    dragOverCol = null;
  }

  // Column resize
  let resizeCol = null;
  let resizeColKey = null;
  let resizeStartX = 0;
  let resizeStartW = 0;

  function loadColumnWidths() {
    try {
      return JSON.parse(storageGet("logColumnWidths")) || {};
    } catch { return {}; }
  }

  let columnWidths = loadColumnWidths();

  function startColResize(e, key) {
    e.preventDefault();
    e.stopPropagation();
    const th = e.target.parentElement;
    resizeCol = th;
    resizeColKey = key;
    resizeStartX = e.clientX;
    resizeStartW = th.offsetWidth;
    window.addEventListener("mousemove", onColResize);
    window.addEventListener("mouseup", stopColResize);
  }

  function onColResize(e) {
    if (!resizeCol) return;
    const diff = e.clientX - resizeStartX;
    const newW = Math.max(30, resizeStartW + diff);
    resizeCol.style.width = newW + "px";
  }

  function stopColResize() {
    if (resizeCol && resizeColKey) {
      columnWidths[resizeColKey] = resizeCol.style.width;
      storageSet("logColumnWidths", JSON.stringify(columnWidths));
    }
    resizeCol = null;
    resizeColKey = null;
    window.removeEventListener("mousemove", onColResize);
    window.removeEventListener("mouseup", stopColResize);
  }

  let columnsAutoSized = false;

  async function autoSizeColumns() {
    if (columnsAutoSized) return;
    // Check if any columns still need default widths
    const needsAuto = columns.some(col => !columnWidths[col.key]);
    if (!needsAuto) { columnsAutoSized = true; return; }
    if (!tableWrapEl) return;
    const table = tableWrapEl.querySelector("table");
    if (!table) return;

    // Temporarily switch to auto layout to measure natural widths
    table.style.tableLayout = "auto";
    // Force reflow
    await tick();
    // Small delay to ensure browser has reflowed
    await new Promise(r => requestAnimationFrame(r));

    const ths = table.querySelectorAll("thead th");
    const measured = {};
    ths.forEach((th, i) => {
      if (i < columns.length) {
        measured[columns[i].key] = th.offsetWidth;
      }
    });

    // Switch back to fixed
    table.style.tableLayout = "fixed";

    // Apply measured widths only for columns without saved widths
    ths.forEach((th, i) => {
      if (i < columns.length) {
        const key = columns[i].key;
        if (columnWidths[key]) {
          th.style.width = columnWidths[key];
        } else if (measured[key]) {
          th.style.width = measured[key] + "px";
        }
      }
    });

    columnsAutoSized = true;
  }

  function toggleSort(key) {
    if (sortCol === key) {
      sortAsc = !sortAsc;
    } else {
      sortCol = key;
      sortAsc = key === "timestamp" ? false : true;
    }
    storageSet("logSortCol", sortCol);
    storageSet("logSortAsc", String(sortAsc));
  }

  $: prevContactCount = call.trim() ? contacts.filter(c => c.call?.toUpperCase() === call.trim().toUpperCase()).length : 0;

  let logFilter = "all";
  let lastFilterCall = "";
  $: {
    const trimmed = call.trim().toUpperCase();
    if (prevContactCount === 0) {
      logFilter = "all";
      lastFilterCall = trimmed;
    } else if (trimmed !== lastFilterCall) {
      logFilter = "call";
      lastFilterCall = trimmed;
    }
  }

  $: sortedContacts = [...contacts].sort((a, b) => {
    let va = a[sortCol] ?? "";
    let vb = b[sortCol] ?? "";
    if (sortCol === "freq" || sortCol === "skcc") {
      va = parseFloat(va) || 0;
      vb = parseFloat(vb) || 0;
    } else if (typeof va === "string") {
      va = va.toLowerCase();
      vb = (vb || "").toLowerCase();
    }
    if (va < vb) return sortAsc ? -1 : 1;
    if (va > vb) return sortAsc ? 1 : -1;
    return 0;
  });

  $: displayedContacts = logFilter === "all" || !call.trim()
    ? sortedContacts
    : sortedContacts.filter(c => c.call?.toUpperCase() === call.trim().toUpperCase());

  async function fetchContacts() {
    try {
      const res = await fetch("/api/contacts/");
      if (res.ok) {
        contacts = await res.json();
        await tick();
        autoSizeColumns();
      }
    } catch {}
  }

  async function fetchDefaultRst() {
    try {
      const res = await fetch("/api/settings/default_rst");
      if (res.ok) {
        const data = await res.json();
        if (data.value) {
          defaultRst = data.value;
          rst_sent = defaultRst;
          rst_recv = defaultRst;
        }
      }
    } catch {}
  }

  async function fetchCountries() {
    try {
      const res = await fetch("/api/geo/countries");
      if (res.ok) countries = await res.json();
    } catch {}
  }

  async function fetchModes() {
    try {
      const res = await fetch("/api/flrig/modes");
      if (res.ok) availableModes = await res.json();
    } catch {}
  }

  async function fetchSubdivisions(code) {
    if (!code) { subdivisions = []; return; }
    try {
      const res = await fetch(`/api/geo/subdivisions/${code}`);
      if (res.ok) subdivisions = await res.json();
      else subdivisions = [];
    } catch { subdivisions = []; }
  }

  function onCountryChange() {
    state = "";
    const match = countries.find(c => c.name === country);
    if (match && match.dxcc != null) {
      dxcc = match.dxcc;
      dxccName = match.dxcc_name || "";
    } else {
      dxcc = null;
      dxccName = "";
    }
    fetchSubdivisions(match ? match.code : "");
  }

  // Auto-fill freq/mode from VFO when not editing
  // Apply prefill from hunting spot
  $: if (prefill && !editingId) {
    // Clear form first to avoid stale data from previous prefill
    lastQrzCall = "";
    callCountryCode = "";
    call = "";
    freq = "";
    mode = "CW";
    rst_sent = defaultRst;
    rst_recv = defaultRst;
    pota_park = "";
    potaParkName = "";
    name = "";
    qth = "";
    state = "";
    country = "";
    dxcc = null;
    dxccName = "";
    grid = "";
    skcc = "";
    skcc_exch = false;
    comments = "";
    notes = "";
    datePart = "";
    timePart = "";
    datePartOff = "";
    timePartOff = "";
    subdivisions = [];

    startRollingClock();
    prefillSource = "hunting";
    if (prefill.call) call = prefill.call;
    if (prefill.freq) freq = prefill.freq;
    if (prefill.mode) mode = prefill.mode;
    if (prefill.pota_park) { pota_park = prefill.pota_park; resolvePotaParkName(); }
    if (prefill.grid) grid = prefill.grid;
    if (prefill.country) {
      country = prefill.country;
      const cm = countries.find(c => c.name === country || (c.aliases || []).includes(country));
      if (cm) {
        country = cm.name;
        if (cm.dxcc != null) { dxcc = cm.dxcc; dxccName = cm.dxcc_name || ""; }
      }
    }
    if (prefill.state) state = prefill.state;
    if (prefill.skcc) skcc = prefill.skcc;
    userTouched = false;
    addOriginal = formSnapshot();
    dispatch("prefillconsumed");
    // Lookup name from QRZ
    if (prefill.call) lookupCallsign(prefill.call.toUpperCase());
  }

  // Auto-fill freq/mode from VFO when not editing, no prefill, and user hasn't typed
  $: if (!editingId && !prefill && !userTouched && vfoFreq) {
    freq = String(parseFloat(vfoFreq) / 1000);
    if (addOriginal) addOriginal = { ...addOriginal, freq };
  }
  $: if (!editingId && !prefill && !userTouched && vfoMode) {
    mode = vfoMode;
    if (addOriginal) addOriginal = { ...addOriginal, mode };
  }

  let lastQrzCall = "";
  let callCountryCode = "";
  let prefillSource = null; // tracks if prefill came from hunting

  async function lookupCallsign(callsign) {
    // Strip portable indicators (e.g. JK1JXP/1, JR2NTC/P)
    const baseCall = callsign.split("/")[0];
    if (!baseCall || baseCall.length < 3 || baseCall === lastQrzCall) return;
    lastQrzCall = baseCall;
    callsign = baseCall;

    // SKCC lookup
    try {
      const res = await fetch(`/api/skcc/lookup/${callsign}`);
      if (res.ok) {
        const data = await res.json();
        if (!skcc.trim()) skcc = data.skcc || "";
        if (!editingId && addOriginal) addOriginal = { ...addOriginal, skcc };
      }
    } catch {}

    // QRZ lookup
    try {
      const res = await fetch(`/api/qrz/lookup/${callsign}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.error) return;
      // If from hunting spot, only fill name. Otherwise fill all empty fields.
      // Derive ISO country code for flag display
      if (data.country) {
        const cm = countries.find(c => c.name === data.country || (c.aliases || []).includes(data.country));
        if (cm) callCountryCode = cm.code;
      }
      if (prefillSource === "hunting") {
        if (!name && data.name) name = data.name;
        // Fill QTH from QRZ if station is not portable
        const isPortable = !!pota_park || call.includes("/");
        if (!isPortable && !qth && data.qth) qth = data.qth;
      } else {
        if (!name && data.name) name = data.name;
        if (!qth && data.qth) qth = data.qth;
        if (!country && data.country) {
          country = data.country;
          if (data.dxcc != null) {
            dxcc = data.dxcc;
            dxccName = data.dxcc_name || "";
          }
          normalizeCountry();
          const match = countries.find(c => c.name === country);
          if (match) await fetchSubdivisions(match.code);
        }
        if (!state && data.state) { state = data.state; normalizeState(); }
        if (!grid && data.grid) grid = data.grid;
      }
      // Update addOriginal so auto-filled fields don't make form dirty
      if (!editingId && addOriginal) {
        addOriginal = { ...addOriginal, name, qth, state, country, grid, skcc, skcc_exch };
      }
    } catch {}
  }

  function onCallInput() {
    call = call.replace(/\s/g, "");
    callCountryCode = "";
    if (!editingId) {
      skcc = "";
      skcc_exch = false;
      name = "";
      qth = "";
      country = "";
      dxcc = null;
      dxccName = "";
      state = "";
      grid = "";
    }
  }

  function onCallBlur() {
    if (!editingId && call.length >= 3) {
      lookupCallsign(call.toUpperCase());
    }
  }

  $: stripCall = () => { call = call.replace(/\s/g, ""); };
  $: stripGrid = () => {
    grid = grid.replace(/[^A-Za-z0-9]/g, "");
    if (grid.length >= 2) grid = grid.substring(0, 2).toUpperCase() + grid.substring(2);
    if (grid.length >= 5) grid = grid.substring(0, 4) + grid.substring(4).toLowerCase();
  };
  $: stripSkcc = () => { skcc = skcc.replace(/[^A-Za-z0-9]/g, ""); if (!skcc.trim()) skcc_exch = false; };

  // POTA park autocomplete
  let potaResults = [];
  let potaOpen = false;
  let potaHighlight = -1;
  let potaTimer = null;
  let potaParkName = "";
  let parkOverlay = null;
  let parkOverlayLoading = false;

  async function resolvePotaParkName() {
    const ref = pota_park.trim().toUpperCase();
    if (!ref) { potaParkName = ""; return; }
    try {
      const res = await fetch(`/api/pota/parks/search?q=${encodeURIComponent(ref)}`);
      if (res.ok) {
        // Check pota_park hasn't changed/cleared while we were fetching
        if (pota_park.trim().toUpperCase() !== ref) return;
        const results = await res.json();
        const match = results.find(p => p.reference === ref);
        if (match) {
          pickPota(match);
        } else {
          const prefixMatch = ref.match(/^([A-Z]{1,2})-/);
          if (prefixMatch) potaParkName = `${prefixMatch[1]} not downloaded`;
        }
      }
    } catch {}
  }

  function onPotaInput() {
    pota_park = pota_park.replace(/[^A-Za-z0-9\- ]/g, "");
    potaParkName = "";
    potaHighlight = -1;
    clearTimeout(potaTimer);
    const q = pota_park.trim();
    if (q.length < 2) { potaResults = []; potaOpen = false; return; }
    potaTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/pota/parks/search?q=${encodeURIComponent(q)}`);
        if (res.ok) {
          potaResults = await res.json();
          potaOpen = potaResults.length > 0;
        }
      } catch {}
    }, 200);
  }

  function onPotaFocus() {
    if (potaResults.length > 0) potaOpen = true;
  }

  function onPotaBlur() {
    setTimeout(() => {
      potaOpen = false;
      if (pota_park.trim() && !potaParkName) resolvePotaParkName();
    }, 150);
  }

  function pickPota(park) {
    pota_park = park.reference;
    potaParkName = park.name;
    if (park.grid && !grid) grid = park.grid;
    if (park.program_name && !country) {
      country = park.program_name;
      onCountryChange();
    }
    if (park.location_name && !state && (park.location_count || 1) === 1) state = park.location_name;
    potaOpen = false;
    potaResults = [];
  }

  function onPotaKeydown(e) {
    if (!potaOpen || potaResults.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      potaHighlight = (potaHighlight + 1) % potaResults.length;
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      potaHighlight = potaHighlight <= 0 ? potaResults.length - 1 : potaHighlight - 1;
    } else if (e.key === "Enter") {
      e.preventDefault();
      pickPota(potaResults[potaHighlight >= 0 ? potaHighlight : 0]);
    } else if (e.key === "Tab" && potaHighlight >= 0) {
      pickPota(potaResults[potaHighlight]);
    } else if (e.key === "Escape") {
      potaOpen = false;
    }
  }

  function autoFocus(node) {
    setTimeout(() => node.focus(), 0);
  }

  function focusOverlay(node) {
    node.focus();
  }

  function closeParkOverlay() {
    parkOverlay = null;
    parkOverlayLoading = false;
  }

  async function openParkOverlay() {
    const ref = pota_park.trim().toUpperCase();
    if (!ref) return;
    parkOverlayLoading = true;
    parkOverlay = null;
    try {
      const res = await fetch(`/api/pota/park/${encodeURIComponent(ref)}`);
      if (res.ok) {
        const data = await res.json();
        if (!data.error) parkOverlay = data;
      }
    } catch {}
    parkOverlayLoading = false;
  }

  function editContact(c) {
    if (formDirty) {
      alert("Save or cancel your current QSO before selecting a new contact.");
      return;
    }
    editingId = c.id;
    showForm = true;
    dispatch("editchange", c.id);
    call = c.call || "";
    freq = c.freq || "";
    mode = c.mode || "";
    rst_sent = c.rst_sent || "";
    rst_recv = c.rst_recv || "";
    pota_park = c.pota_park || "";
    potaParkName = "";
    if (pota_park) resolvePotaParkName();
    name = c.name || "";
    qth = c.qth || "";
    state = c.state || "";
    country = c.country || "";
    dxcc = c.dxcc != null ? c.dxcc : null;
    grid = c.grid || "";
    skcc = c.skcc || "";
    skcc_exch = !!c.skcc_exch;
    comments = c.comments || "";
    notes = c.notes || "";
    if (c.timestamp) {
      const iso = new Date(c.timestamp).toISOString();
      datePart = iso.slice(0, 10);
      timePart = iso.slice(11, 19);
    } else {
      datePart = "";
      timePart = "";
    }
    if (c.timestamp_off) {
      const isoOff = new Date(c.timestamp_off).toISOString();
      datePartOff = isoOff.slice(0, 10);
      timePartOff = isoOff.slice(11, 19);
    } else {
      datePartOff = "";
      timePartOff = "";
    }
    stopRollingClock();
    clockState = "STATIC";
    errorMsg = "";
    editOriginal = {
      call, freq, mode, rst_sent, rst_recv, pota_park, name, qth,
      state, country, grid, skcc, skcc_exch, comments, notes, datePart, timePart,
      datePartOff, timePartOff,
    };
    const match = countries.find(co => co.name === country);
    fetchSubdivisions(match ? match.code : "");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() {
    editingId = null;
    editOriginal = null;
    dispatch("editchange", null);
    dispatch("navigate", "back");
    clearForm();
  }

  async function deleteContact() {
    if (!editingId) return;
    if (!confirm(`Delete contact ${call}?`)) return;
    try {
      const res = await fetch(`/api/contacts/${editingId}`, { method: "DELETE" });
      if (res.ok) {
        editingId = null;
        dispatch("editchange", null);
        dispatch("navigate", "back");
        clearForm();
        await fetchContacts();
        dispatch("parkschanged");
      } else {
        errorMsg = `Delete failed: ${res.status} ${res.statusText}`;
      }
    } catch (e) {
      errorMsg = `Network error: ${e.message}`;
    }
  }

  async function saveEdit() {
    if (!editingId) return;
    submitting = true;
    errorMsg = "";
    try {
      const body = {
        call: call.trim().toUpperCase(),
        freq: freq.trim(),
        mode: mode.trim().toUpperCase(),
        rst_sent: rst_sent.trim() || null,
        rst_recv: rst_recv.trim() || null,
        pota_park: pota_park.trim().toUpperCase() || null,
        name: name || null,
        qth: qth.trim() || null,
        state: state.trim() || null,
        country: country.trim() || null,
        dxcc: dxcc,
        grid: grid.trim().toUpperCase() || null,
        skcc: skcc.trim().toUpperCase() || null,
        skcc_exch: skcc_exch,
        comments: comments || null,
        notes: notes || null,
        timestamp: `${datePart}T${timePart || "00:00:00"}Z`,
        timestamp_off: (datePartOff.trim() && timePartOff.trim()) ? `${datePartOff}T${timePartOff}Z` : null,
      };
      const res = await fetch(`/api/contacts/${editingId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        editingId = null;
        editOriginal = null;
        dispatch("editchange", null);
        clearForm();
        await fetchContacts();
        dispatch("parkschanged");
        dispatch("navigate", "back");
      } else {
        const data = await res.json().catch(() => null);
        errorMsg = data?.detail || `Error: ${res.status} ${res.statusText}`;
      }
    } catch (e) {
      errorMsg = `Network error: ${e.message}`;
    }
    submitting = false;
  }

  function clearForm() {
    lastQrzCall = "";
    prefillSource = null;
    callCountryCode = "";
    call = "";
    freq = "";
    mode = "CW";
    rst_sent = defaultRst;
    rst_recv = defaultRst;
    pota_park = "";
    potaParkName = "";
    closeParkOverlay();
    name = "";
    qth = "";
    state = "";
    country = "";
    dxcc = null;
    dxccName = "";
    grid = "";
    skcc = "";
    skcc_exch = false;
    comments = "";
    notes = "";
    datePart = "";
    timePart = "";
    datePartOff = "";
    timePartOff = "";
    subdivisions = [];
    userTouched = false;
    startRollingClock();
    addOriginal = formSnapshot();
  }

  async function submitContact() {
    const required = { call, freq, mode };
    const missing = Object.entries(required).filter(([, v]) => !v || !String(v).trim());
    if (missing.length) {
      errorMsg = `Required: ${missing.map(([k]) => k).join(", ")}`;
      return;
    }
    if (!datePart.trim()) datePart = utcNowDate();
    if (!timePart.trim()) timePart = utcNowTime();
    if (!datePartOff.trim()) datePartOff = utcNowDate();
    if (!timePartOff.trim()) timePartOff = utcNowTime();
    submitting = true;
    errorMsg = "";
    try {
      const body = {
        call: call.trim().toUpperCase(),
        freq: freq.trim(),
        mode: mode.trim().toUpperCase(),
        rst_sent: rst_sent.trim() || null,
        rst_recv: rst_recv.trim() || null,
        pota_park: pota_park.trim().toUpperCase() || null,
        name: name || null,
        qth: qth.trim() || null,
        state: state.trim() || null,
        country: country.trim() || null,
        dxcc: dxcc,
        grid: grid.trim().toUpperCase() || null,
        skcc: skcc.trim().toUpperCase() || null,
        skcc_exch: skcc_exch,
        comments: comments || null,
        notes: notes || null,
        timestamp: `${datePart}T${timePart || "00:00:00"}Z`,
        timestamp_off: (datePartOff && timePartOff) ? `${datePartOff}T${timePartOff}Z` : null,
      };
      const res = await fetch("/api/contacts/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const wasHunting = prefillSource === "hunting";
        callCountryCode = "";
        call = "";
        pota_park = "";
        potaParkName = "";
        name = "";
        qth = "";
        grid = "";
        skcc = "";
        skcc_exch = false;
        comments = "";
        notes = "";
        datePart = "";
        timePart = "";
        datePartOff = "";
        timePartOff = "";
        startRollingClock();
        addOriginal = formSnapshot();
        await fetchContacts();
        dispatch("parkschanged");
        dispatch("navigate", "back");
      } else {
        const data = await res.json().catch(() => null);
        errorMsg = data?.detail || `Error: ${res.status} ${res.statusText}`;
      }
    } catch (e) {
      errorMsg = `Network error: ${e.message}`;
    }
    submitting = false;
  }

  async function loadEditFromId(id) {
    if (!id) return;
    try {
      const res = await fetch(`/api/contacts/${id}`);
      if (res.ok) {
        const c = await res.json();
        editContact(c);
      }
    } catch {}
  }

  let handledEditId = null;

  $: if (editId && editId !== handledEditId && contacts.length > 0) {
    handledEditId = editId;
    const c = contacts.find(x => x.id === editId);
    if (c) setTimeout(() => editContact(c), 0);
    else loadEditFromId(editId);
  } else if (!editId) {
    handledEditId = null;
    if (editingId) {
      editingId = null;
      editOriginal = null;
      clearForm();
    }
  }

  onMount(() => {
    fetchContacts();
    fetchDefaultRst();
    fetchCountries();
    fetchModes();
    if (!editingId) startRollingClock();
  });

  onDestroy(() => {
    stopRollingClock();
  });

  const BANDS = [
    { name: "160m", lo: 1800, hi: 2000 },
    { name: "80m", lo: 3500, hi: 4000 },
    { name: "60m", lo: 5330, hi: 5410 },
    { name: "40m", lo: 7000, hi: 7300 },
    { name: "30m", lo: 10100, hi: 10150 },
    { name: "20m", lo: 14000, hi: 14350 },
    { name: "17m", lo: 18068, hi: 18168 },
    { name: "15m", lo: 21000, hi: 21450 },
    { name: "12m", lo: 24890, hi: 24990 },
    { name: "10m", lo: 28000, hi: 29700 },
    { name: "6m", lo: 50000, hi: 54000 },
    { name: "2m", lo: 144000, hi: 148000 },
  ];

  function freqToBand(f) {
    const n = parseFloat(f);
    if (isNaN(n)) return "";
    const b = BANDS.find(b => n >= b.lo && n <= b.hi);
    return b ? b.name : "";
  }

  function formatFreq(f) {
    if (!f) return "--";
    const n = parseFloat(f);
    if (isNaN(n)) return f;
    return n.toFixed(1).padStart(9, "\u2007") + " KHz";
  }

  function formatTimestamp(ts) {
    if (!ts) return "";
    try {
      const d = new Date(ts);
      return d.toISOString().replace("T", " ").substring(0, 19) + "z";
    } catch {
      return ts;
    }
  }

  function relativeTime(ts) {
    if (!ts) return "";
    try {
      const s = String(ts);
      const d = new Date(s.endsWith("Z") || s.includes("+") ? s : s + "Z");
      if (isNaN(d)) return "";
      const now = new Date();
      const diffMs = now - d;
      const absDiffMs = Math.abs(diffMs);
      const suffix = diffMs < 0 ? "from now" : "ago";
      const mins = Math.floor(absDiffMs / 60000);
      if (mins < 1) return "just now";
      if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ${suffix}`;
      const hours = Math.floor(mins / 60);
      if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ${suffix}`;
      const days = Math.floor(hours / 24);
      if (days < 30) return `${days} day${days === 1 ? "" : "s"} ${suffix}`;
      const months = Math.floor(days / 30);
      if (months < 12) return `${months} month${months === 1 ? "" : "s"} ${suffix}`;
      const years = Math.floor(days / 365);
      return `${years} year${years === 1 ? "" : "s"} ${suffix}`;
    } catch {
      return "";
    }
  }
</script>

<div class="logbook-layout">
{#if showForm}
<form on:submit|preventDefault={editingId ? saveEdit : submitContact} on:input={() => { if (!editingId) userTouched = true; }} on:keydown={e => { if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") e.preventDefault(); if (e.key === "Escape") { e.target.blur(); if (editingId) cancelEdit(); else { dispatch("navigate", "back"); clearForm(); } } }}>
  <h3 class="form-heading">{editingId ? "Edit QSO" : "New QSO"}{#if call.trim()} <a class="form-callsign-text" href="https://www.qrz.com/db/{call.trim().toUpperCase()}" target="_blank" rel="noopener" title="View {call.trim().toUpperCase()} on QRZ.com">{call.trim().toUpperCase()}</a>{/if}{#if callCountryCode} <span class="form-callsign-flag">{countryFlag(callCountryCode)}</span>{/if}{#if editingId} <span class="prev-contact">({relativeTime(`${datePart}T${timePart || "00:00:00"}Z`)})</span>{:else if prevContactCount > 0} <span class="prev-contact">(contacted {prevContactCount} time{prevContactCount === 1 ? "" : "s"} before)</span>{/if}</h3>
  <div class="form-row">
    <div class="field" class:changed={orig && call !== orig.call} class:missing={!call.trim()}>
      <label for="call">Call *</label>
      <input
        id="call"
        type="text"
        bind:value={call}
        on:input={onCallInput}
        on:blur={onCallBlur}
        required
        maxlength="10"
        autocomplete="off"
        style="text-transform: uppercase"
        use:autoFocus
      />
    </div>
    <div class="field" class:changed={orig && freq !== orig.freq} class:missing={!freq.trim()}>
      <label for="freq">Freq (KHz) *</label>
      <input id="freq" type="text" bind:value={freq} required />
    </div>
    <div class="field" class:changed={orig && mode !== orig.mode} class:missing={!mode.trim()}>
      <label>Mode *</label>
      <Autocomplete bind:value={mode} items={availableModes} />
    </div>
    <div class="field" class:changed={orig && rst_sent !== orig.rst_sent}>
      <label for="rst_sent">RST Sent</label>
      <input id="rst_sent" type="text" bind:value={rst_sent} />
    </div>
    <div class="field" class:changed={orig && rst_recv !== orig.rst_recv}>
      <label for="rst_recv">RST Recv</label>
      <input id="rst_recv" type="text" bind:value={rst_recv} />
    </div>
    <div class="field field-name" class:changed={orig && name !== orig.name}>
      <label for="name">Name</label>
      <input id="name" type="text" bind:value={name} />
    </div>
  </div>

  <div class="form-row">
    <div class="field" class:changed={orig && qth !== orig.qth}>
      <label for="qth">QTH</label>
      <input id="qth" type="text" bind:value={qth} />
    </div>
    <div class="field" class:changed={orig && country !== orig.country}>
      <label>Country{#if dxcc != null} — <span class="dxcc-label">DXCC {dxcc}{#if dxccName}: {dxccName}{/if}</span>{/if}</label>
      <Autocomplete bind:value={country} items={countryItems} on:pick={onCountryChange} on:input={onCountryChange} on:blur={normalizeCountry} />
    </div>
    <div class="field" class:changed={orig && state !== orig.state}>
      <label>State</label>
      <Autocomplete bind:value={state} items={subdivisionNames} on:blur={normalizeState} />
    </div>
    <div class="field" class:changed={orig && grid !== orig.grid}>
      <label for="grid">Grid</label>
      <div class="grid-input-row">
        <input id="grid" type="text" bind:value={grid} on:input={stripGrid} />
        <button type="button" class="grid-picker-btn" on:click={() => showGridPicker = !showGridPicker} title="Pick from map">🌍</button>
      </div>
      {#if showGridPicker}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
        <div class="grid-picker-overlay" on:click|self={() => showGridPicker = false} on:keydown={e => e.key === "Escape" && (showGridPicker = false)} tabindex="0" use:focusOverlay>
          <div class="grid-picker-modal">
            <div class="grid-picker-header">
              <span>Grid Square</span>
              <button type="button" class="grid-picker-close" on:click={() => showGridPicker = false}>✕</button>
            </div>
            <GridMap bind:value={grid} on:select={() => showGridPicker = false} />
          </div>
        </div>
      {/if}
    </div>
  </div>

  <div class="form-row">
    <div class="field field-pota" class:changed={orig && pota_park !== orig.pota_park}>
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <label for="pota_park">POTA Park{#if potaParkName} — {#if potaParkName.endsWith("not downloaded")}<a class="pota-park-name" href="#/parks/download" on:click|stopPropagation>{potaParkName}</a>{:else}<span class="pota-park-name" on:click|preventDefault|stopPropagation={openParkOverlay}>{potaParkName}</span>{/if}{/if}</label>
      <div class="pota-ac">
        <input id="pota_park" type="text" bind:value={pota_park} on:input={onPotaInput} on:focus={onPotaFocus} on:blur={onPotaBlur} on:keydown={onPotaKeydown} style="text-transform: uppercase" autocomplete="off" />
        {#if potaOpen && potaResults.length > 0}
          <ul class="pota-dropdown">
            {#each potaResults as park, i}
              <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
              <li class:highlighted={i === potaHighlight} on:mousedown|preventDefault={() => pickPota(park)}>
                <span class="pota-ref">{park.reference}</span>
                <span class="pota-name">{park.name}</span>
                <span class="pota-loc">{park.location_desc}{park.grid ? " " + park.grid : ""}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
    <div class="field" class:changed={orig && (skcc !== orig.skcc || skcc_exch !== orig.skcc_exch)}>
      <label for="skcc">SKCC # / {skcc_exch ? "Validated!" : "Validated?"}</label>
      <div class="skcc-input-row">
        <input id="skcc" type="text" bind:value={skcc} on:input={stripSkcc} style="text-transform: uppercase" readonly={skcc_exch} />
        <button type="button" class="skcc-exch-btn" class:active={skcc_exch} disabled={!skcc.trim()} on:click={() => skcc_exch = !skcc_exch} title="Valid SKCC exchange (RST, QTH, Name, SKCC#)">✓</button>
      </div>
    </div>
    <div class="field wide" class:changed={orig && comments !== orig.comments}>
      <label for="comments">Comments (public)</label>
      <input id="comments" type="text" bind:value={comments} />
    </div>
  </div>

  <div class="form-row">
    <div class="time-btn-group">
      <div class="field" class:changed={orig && datePart !== orig.datePart}>
        <label for="date">Start Date (UTC)</label>
        <input id="date" type="date" bind:value={datePart} on:focus={onStartFocus} />
      </div>
      <div class="field time-with-btn" class:changed={orig && timePart !== orig.timePart}>
        <label for="time">Start Time{#if !editingId && clockState === "ROLLING_START"} <span class="clock-rolling">CLICK START</span>{/if}</label>
        <div class="time-input-row">
          <input id="time" type="text" bind:value={timePart} on:blur={normalizeTime} on:focus={onStartFocus} placeholder="HH:MM:SS" maxlength="8" />
          {#if !editingId}
            <button type="button" class="btn-clock" on:click={onStartClick} title={clockState === "ROLLING_START" ? "Freeze start time" : "Reset start to now"}>
              Start
            </button>
          {/if}
        </div>
      </div>
    </div>
    <div class="time-btn-group">
      <div class="field" class:changed={orig && datePartOff !== orig.datePartOff}>
        <label for="date_off">End Date (UTC)</label>
        <input id="date_off" type="date" bind:value={datePartOff} on:focus={onEndFocus} disabled={!editingId && clockState === "ROLLING_START"} />
      </div>
      <div class="field time-with-btn" class:changed={orig && timePartOff !== orig.timePartOff}>
        <label for="time_off">End Time{#if !editingId && clockState === "ROLLING_END"} <span class="clock-rolling">LIVE</span>{/if}</label>
        <div class="time-input-row">
          <input id="time_off" type="text" bind:value={timePartOff} on:blur={normalizeTimeOff} on:focus={onEndFocus} placeholder="HH:MM:SS" maxlength="8" disabled={!editingId && clockState === "ROLLING_START"} />
          {#if !editingId}
            <button type="button" class="btn-clock" on:click={onStopClick} disabled={clockState === "ROLLING_START"} title={clockState === "ROLLING_END" ? "Freeze end time" : "Reset end to now"}>
              Stop
            </button>
          {/if}
        </div>
      </div>
    </div>
  </div>

  <div class="form-row">
    <div class="field wide" class:changed={orig && notes !== orig.notes}>
      <label for="notes">Notes (private)</label>
      <textarea id="notes" bind:value={notes} rows="2"></textarea>
    </div>
  </div>

  <div class="form-row">
    <button type="submit" disabled={submitting || !call.trim() || !freq.trim() || !mode.trim() || !editHasChanges}>
      {#if editingId}
        {submitting ? "Saving..." : "Save Edit"}
      {:else}
        {submitting ? "Logging..." : "Log QSO"}
      {/if}
    </button>
    {#if editingId}
      <button type="button" class="btn-clear" on:click={cancelEdit}>Cancel</button>
      <button type="button" class="btn-delete" on:click={deleteContact}>Delete</button>
    {:else}
      <button type="button" class="btn-clear" on:click={() => { dispatch("navigate", "back"); clearForm(); }}>Cancel</button>
    {/if}
    {#if missingFields.length}
      <span class="error">Required: {missingFields.join(", ")}</span>
    {:else if errorMsg}
      <span class="error">{errorMsg}</span>
    {/if}
  </div>
</form>
{/if}

<section class="log">
  <div class="log-title-row">
    <h2>Log ({displayedContacts.length})</h2>
    {#if prevContactCount > 0 && (showForm || editingId)}
      <div class="log-tabs">
        <button class="log-tab" class:active={logFilter === "all"} on:click={() => logFilter = "all"}>All</button>
        <button class="log-tab" class:active={logFilter === "call"} on:click={() => logFilter = "call"}>{call.trim().toUpperCase()}</button>
      </div>
    {/if}
  </div>
  {#if contacts.length === 0}
    <p class="empty">No contacts logged yet.</p>
  {:else}
    <div class="table-wrap" bind:this={tableWrapEl}>
      <table>
        <thead>
          <tr>
            {#each columns as col (col.key)}
              <th class:drag-over={dragOverCol === col.key && dragCol !== col.key} on:dragover={e => onColDragOver(e, col.key)} on:drop={e => onColDrop(e, col.key)} style={columnWidths[col.key] ? `width: ${columnWidths[col.key]}` : ""}>
                <span class="col-label" draggable="true" on:dragstart={e => onColDragStart(e, col.key)} on:dragend={onColDragEnd} on:click={() => toggleSort(col.key)}>{col.label}{#if sortCol === col.key}{sortAsc ? " ▲" : " ▼"}{/if}</span><span class="resize-handle" on:mousedown={e => startColResize(e, col.key)}></span>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each displayedContacts as c}
            <tr class="clickable" class:editing={editingId === c.id} title={relativeTime(c.timestamp)} on:click={() => editContact(c)}>
              {#each columns as col (col.key)}
                {#if col.key === "timestamp"}<td>{formatTimestamp(c.timestamp)}</td>
                {:else if col.key === "call"}<td class="call">{c.call}{#if c.pota_park} 🌲{/if}</td>
                {:else if col.key === "name"}<td class="truncate truncate-wide">{c.name || ""}</td>
                {:else if col.key === "freq"}<td>{formatFreq(c.freq)} {#if freqToBand(c.freq)}<span class="band-tag" style="background: {bandColor(freqToBand(c.freq))}; color: {bandTextColor(freqToBand(c.freq))}">{freqToBand(c.freq)}</span>{/if}</td>
                {:else if col.key === "mode"}<td>{c.mode || ""}</td>
                {:else if col.key === "pota_park"}<td class="truncate">{c.pota_park || ""}</td>
                {:else if col.key === "qth"}<td class="truncate">{c.qth || ""}</td>
                {:else if col.key === "rst_sent"}<td>{c.rst_sent || ""}</td>
                {:else if col.key === "rst_recv"}<td>{c.rst_recv || ""}</td>
                {:else if col.key === "comments"}<td class="truncate">{c.comments || ""}</td>
                {:else if col.key === "updated_at"}<td>{c.updated_at ? formatTimestamp(c.updated_at) : ""}</td>
                {/if}
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</section>
</div>

{#if parkOverlay || parkOverlayLoading}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="park-overlay-backdrop" on:click={closeParkOverlay}>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="park-overlay" on:click|stopPropagation>
      <button class="park-overlay-close" on:click={closeParkOverlay}>X</button>
      {#if parkOverlayLoading}
        <p class="park-overlay-loading">Loading park...</p>
      {:else if parkOverlay}
        <ParkDetail park={parkOverlay} on:close={closeParkOverlay} />
      {:else}
        {@const parkRef = pota_park.trim().toUpperCase()}
        {@const prefix = parkRef.match(/^([A-Z]{1,2})-/)?.[1] || ""}
        <p class="park-overlay-loading">Park {parkRef} not found in cache.</p>
        <p class="cache-link">Go to <a href="#/parks/download">Cache</a> to download park data{prefix ? ` for country code ${prefix}` : ""}.</p>
      {/if}
    </div>
  </div>
{/if}

<svelte:window on:keydown={e => {
  if ((parkOverlay || parkOverlayLoading) && e.key === "Escape") closeParkOverlay();
  if (tableWrapEl && (e.key === "PageDown" || e.key === "PageUp" || e.key === "Home" || e.key === "End")) {
    const active = document.activeElement;
    const inForm = active && (active.tagName === "INPUT" || active.tagName === "TEXTAREA" || active.tagName === "SELECT");
    if (!inForm) {
      e.preventDefault();
      if (e.key === "Home") tableWrapEl.scrollTo({ top: 0, behavior: "smooth" });
      else if (e.key === "End") tableWrapEl.scrollTo({ top: tableWrapEl.scrollHeight, behavior: "smooth" });
      else tableWrapEl.scrollBy({ top: e.key === "PageDown" ? tableWrapEl.clientHeight : -tableWrapEl.clientHeight, behavior: "smooth" });
    }
  }
}} />

<style>
  .logbook-layout {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }

  .logbook-layout .log {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  form {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.75rem;
    margin-bottom: 1rem;
    flex-shrink: 0;
  }

  .form-row {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
    align-items: flex-end;
  }

  .field {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 120px;
  }
  .field.changed {
    border-left: 3px solid var(--accent, #f0c040);
    padding-left: 4px;
  }
  .field.changed label {
    color: var(--accent, #f0c040);
  }

  .field.missing {
    border-left: 3px solid #cc4444;
    padding-left: 4px;
  }
  .field.missing label {
    color: #cc4444;
  }

  .field.wide {
    flex: 2;
    min-width: 240px;
  }

  .time-btn-group {
    display: flex;
    gap: 0.25rem;
    align-items: flex-end;
    flex: 1;
    min-width: 250px;
    flex-wrap: nowrap;
  }

  .time-btn-group .field {
    flex: 1;
    min-width: 0;
  }

  .time-input-row {
    display: flex;
    gap: 0.25rem;
    align-items: stretch;
  }

  .time-input-row input {
    flex: 1;
    min-width: 0;
  }

  .btn-clock {
    padding: 0.35rem 0.6rem;
    font-size: 0.75rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 4px;
    cursor: pointer;
  }
  .btn-clock:hover:not(:disabled) {
    background: var(--accent, #f0c040);
    color: var(--bg);
  }
  .btn-clock:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .clock-rolling {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: bold;
    color: #4caf50;
    margin-left: 0.3em;
    animation: pulse-live 1.5s infinite;
  }

  @keyframes pulse-live {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .field-name {
    min-width: 50%;
  }

  .field label {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .field-pota label {
    white-space: normal;
    overflow: visible;
    text-overflow: unset;
  }

  input,
  textarea {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 0.35rem 0.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    border-radius: 3px;
  }

  input:focus,
  textarea:focus {
    outline: none;
    border-color: var(--accent);
  }

  textarea {
    resize: vertical;
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

  button:hover:not(:disabled):not(.btn-clear):not(.btn-delete) {
    background: var(--accent-hover);
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-clear {
    background: var(--btn-secondary);
    color: var(--text);
  }

  .btn-clear:hover {
    background: var(--btn-secondary-hover);
  }

  .btn-delete {
    background: var(--accent-delete);
    color: #fff;
  }

  .btn-delete:hover {
    background: var(--accent-delete-hover);
  }

  .form-heading {
    margin: 0 0 0.5rem 0;
    font-size: 0.95rem;
    color: var(--accent);
  }

  .form-callsign-text {
    font-size: 1.1rem;
    font-weight: bold;
    color: var(--accent-callsign);
    text-decoration: none;
    margin-left: 0.4rem;
  }

  .form-callsign-text:hover {
    text-decoration: underline;
  }

  .form-callsign-flag {
    font-size: 1rem;
    margin-left: 0.25rem;
  }

  .form-heading .prev-contact {
    margin-left: 0.3rem;
  }

  .log-title-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
  }

  .log-title-row h2 {
    margin: 0;
  }

  .log-tabs {
    display: flex;
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
  }

  .log-tab {
    background: transparent;
    color: var(--text-muted);
    border: none;
    border-right: 1px solid var(--border);
    padding: 0.2rem 0.6rem;
    font-family: inherit;
    font-size: 0.75rem;
    font-weight: bold;
    cursor: pointer;
    border-radius: 0;
  }

  .log-tab:last-child {
    border-right: none;
  }

  .log-tab.active {
    background: var(--accent);
    color: var(--bg);
  }

  .log-tab:not(.active):hover {
    background: var(--btn-secondary);
    color: var(--text);
  }

  .prev-contact {
    font-size: 0.8rem;
    font-weight: normal;
    color: var(--text-muted);
  }

  .error {
    color: var(--accent-error);
    font-size: 0.85rem;
    margin-left: 0.5rem;
  }

  .grid-input-row {
    display: flex;
    gap: 0.25rem;
  }

  .grid-input-row input {
    flex: 1;
    min-width: 0;
  }

  .skcc-input-row {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .skcc-input-row input[type="text"] {
    flex: 1;
    min-width: 0;
  }

  .skcc-exch-btn {
    background: var(--btn-secondary);
    border: none;
    padding: 0.2rem 0.4rem;
    font-size: 0.85rem;
    border-radius: 3px;
    cursor: pointer;
    line-height: 1;
    opacity: 0.4;
  }

  .skcc-exch-btn:hover {
    background: var(--btn-secondary-hover);
  }

  .skcc-exch-btn.active {
    opacity: 1;
    background: var(--accent);
    color: var(--bg);
  }

  .grid-picker-btn {
    background: var(--btn-secondary);
    border: none;
    padding: 0.2rem 0.4rem;
    font-size: 0.85rem;
    border-radius: 3px;
    cursor: pointer;
    line-height: 1;
  }

  .grid-picker-btn:hover {
    background: var(--btn-secondary-hover);
  }

  .grid-picker-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 300;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
  }

  .grid-picker-modal {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1rem;
    width: 95vw;
    max-width: 100vw;
    max-height: 90vh;
    overflow-y: auto;
  }

  .grid-picker-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
    color: var(--accent);
    font-weight: bold;
    font-size: 1rem;
  }

  .grid-picker-close {
    background: var(--btn-secondary);
    color: var(--text);
    border: none;
    padding: 0.2rem 0.5rem;
    font-size: 0.9rem;
    border-radius: 3px;
    cursor: pointer;
  }

  .grid-picker-close:hover {
    background: var(--btn-secondary-hover);
  }

  .log h2 {
    color: var(--accent);
    font-size: 1.1rem;
    margin: 0 0 0.5rem 0;
  }

  .empty {
    color: var(--text-dim);
    font-style: italic;
  }

  .table-wrap {
    flex: 1;
    overflow: auto;
    min-height: 0;
  }

  table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.85rem;
    table-layout: fixed;
  }

  th {
    text-align: left;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    padding: 0.3rem 0.5rem;
    white-space: nowrap;
    position: sticky;
    top: 0;
    background: var(--bg);
    z-index: 1;
    overflow: hidden;
  }

  .col-label {
    cursor: pointer;
    user-select: none;
  }

  .col-label:hover {
    color: var(--accent);
  }
  th.drag-over {
    border-left: 2px solid var(--accent);
  }

  .resize-handle {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 5px;
    cursor: col-resize;
    background: transparent;
  }

  .resize-handle:hover,
  .resize-handle:active {
    background: var(--accent);
    opacity: 0.4;
  }

  td {
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid var(--bg-card);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  td.call {
    color: var(--accent-callsign);
    font-weight: bold;
  }

  td.truncate {
    max-width: 14ch;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  td.truncate-wide {
    max-width: 30ch;
  }

  tr.clickable {
    cursor: pointer;
  }

  tbody tr:hover {
    background: var(--row-hover);
  }

  tr.editing {
    background: var(--row-editing);
  }

  .band-tag {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: bold;
    padding: 0.1rem 0.35rem;
    border-radius: 8px;
    margin-left: 0.3rem;
    vertical-align: middle;
  }

  .dxcc-label {
    color: var(--accent-vfo);
    font-weight: normal;
  }

  .pota-park-name {
    color: var(--accent-vfo);
    font-weight: normal;
    cursor: pointer;
  }

  .pota-park-name:hover {
    text-decoration: underline;
  }

  .park-overlay-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .park-overlay {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    max-width: 900px;
    width: 95%;
    max-height: 80vh;
    overflow-y: auto;
    position: relative;
  }

  .park-overlay-close {
    position: absolute;
    top: 0.5rem;
    right: 0.75rem;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 1rem;
    font-family: inherit;
    font-weight: bold;
    cursor: pointer;
  }

  .park-overlay-close:hover {
    color: var(--text);
  }

  .park-overlay-loading {
    color: var(--text-muted);
    font-style: italic;
  }

  .cache-link {
    font-size: 0.9rem;
  }

  .cache-link a {
    color: var(--accent);
    text-decoration: none;
  }

  .cache-link a:hover {
    text-decoration: underline;
  }

  .pota-ac {
    position: relative;
    min-width: 0;
  }

  .pota-ac input {
    width: 100%;
    box-sizing: border-box;
  }

  .pota-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    min-width: 500px;
    max-height: 200px;
    overflow-y: auto;
    background: var(--bg-card);
    border: 1px solid var(--border-input);
    border-top: none;
    border-radius: 0 0 3px 3px;
    margin: 0;
    padding: 0;
    list-style: none;
    z-index: 100;
  }

  .pota-dropdown li {
    padding: 0.3rem 0.5rem;
    cursor: pointer;
    font-size: 0.8rem;
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
    line-height: 1.4;
  }

  .pota-dropdown li:hover,
  .pota-dropdown li.highlighted {
    background: var(--accent);
    color: var(--bg);
  }

  .pota-ref {
    color: var(--accent-vfo);
    font-weight: bold;
    flex-shrink: 0;
  }

  .pota-dropdown li:hover .pota-ref,
  .pota-dropdown li.highlighted .pota-ref {
    color: var(--bg);
  }

  .pota-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .pota-loc {
    color: var(--text-dim);
    font-size: 0.75rem;
    flex-shrink: 0;
    margin-left: auto;
  }

  .pota-dropdown li:hover .pota-loc,
  .pota-dropdown li.highlighted .pota-loc {
    color: var(--bg);
  }


</style>
