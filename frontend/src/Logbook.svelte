<script>
  import { onMount, tick, createEventDispatcher } from "svelte";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";
  import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
  import markerIcon from "leaflet/dist/images/marker-icon.png";
  import markerShadow from "leaflet/dist/images/marker-shadow.png";

  delete L.Icon.Default.prototype._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2x,
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
  });
  import Autocomplete from "./Autocomplete.svelte";
  import GridMap from "./GridMap.svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";
  import { parkAward, parkAwardTitle } from "./parkAward.js";
  import { countryFlag, prefixFromRef } from "./countryFlag.js";

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
  let grid = "";
  let skcc = "";
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
  let comments = "";
  let notes = "";

  let countries = [];
  let subdivisions = [];
  let availableModes = [];
  $: countryItems = countries.map(c => ({ name: c.name, aliases: c.aliases || [] }));
  $: subdivisionNames = subdivisions.map(s => s.name);

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
  let showGridPicker = false;
  $: if (typeof document !== "undefined") {
    document.body.style.overflow = showGridPicker ? "hidden" : "";
  }
  export let showForm = true;

  let sortCol = "timestamp";
  let sortAsc = false;

  const columns = [
    { key: "timestamp", label: "UTC" },
    { key: "call", label: "Call" },
    { key: "name", label: "Name" },
    { key: "freq", label: "Freq" },
    { key: "mode", label: "Mode" },
    { key: "pota_park", label: "POTA" },
    { key: "qth", label: "QTH" },
    { key: "rst_sent", label: "RST S" },
    { key: "rst_recv", label: "RST R" },
    { key: "comments", label: "Comments" },
  ];

  function toggleSort(key) {
    if (sortCol === key) {
      sortAsc = !sortAsc;
    } else {
      sortCol = key;
      sortAsc = key === "timestamp" ? false : true;
    }
  }

  $: prevContactCount = call.trim() ? contacts.filter(c => c.call?.toUpperCase() === call.trim().toUpperCase()).length : 0;

  let logFilter = "all";
  $: if (prevContactCount === 0) logFilter = "all";

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
    grid = "";
    skcc = "";
    comments = "";
    notes = "";
    datePart = "";
    timePart = "";
    subdivisions = [];

    prefillSource = "hunting";
    if (prefill.call) call = prefill.call;
    if (prefill.freq) freq = prefill.freq;
    if (prefill.mode) mode = prefill.mode;
    if (prefill.pota_park) { pota_park = prefill.pota_park; resolvePotaParkName(); }
    if (prefill.grid) grid = prefill.grid;
    if (prefill.country) country = prefill.country;
    if (prefill.state) state = prefill.state;
    if (prefill.skcc) skcc = prefill.skcc;
    dispatch("prefillconsumed");
    // Lookup name from QRZ
    if (prefill.call) lookupCallsign(prefill.call.toUpperCase());
  }

  // Auto-fill freq/mode from VFO when not editing and no prefill
  $: if (!editingId && !prefill && vfoFreq) {
    freq = String(parseFloat(vfoFreq) / 1000);
  }
  $: if (!editingId && !prefill && vfoMode) {
    mode = vfoMode;
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
        skcc = data.skcc || "";
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
      } else {
        if (!name && data.name) name = data.name;
        if (!qth && data.qth) qth = data.qth;
        if (!country && data.country) {
          country = data.country;
          normalizeCountry();
          const match = countries.find(c => c.name === country);
          if (match) await fetchSubdivisions(match.code);
        }
        if (!state && data.state) { state = data.state; normalizeState(); }
        if (!grid && data.grid) grid = data.grid;
      }
    } catch {}
  }

  function onCallInput() {
    call = call.replace(/\s/g, "");
  }

  function onCallBlur() {
    if (call.length >= 3) {
      lookupCallsign(call.toUpperCase());
    }
  }

  $: stripCall = () => { call = call.replace(/\s/g, ""); };
  $: stripGrid = () => {
    grid = grid.replace(/[^A-Za-z0-9]/g, "");
    if (grid.length >= 2) grid = grid.substring(0, 2).toUpperCase() + grid.substring(2);
    if (grid.length >= 5) grid = grid.substring(0, 4) + grid.substring(4).toLowerCase();
  };
  $: stripSkcc = () => { skcc = skcc.replace(/[^A-Za-z0-9]/g, ""); };

  // POTA park autocomplete
  let potaResults = [];
  let potaOpen = false;
  let potaHighlight = -1;
  let potaTimer = null;
  let potaParkName = "";
  let parkOverlay = null;
  let parkOverlayLoading = false;
  let overlayMapEl;
  let overlayMap = null;

  let overlayFullscreen = false;

  function addExpandControl(map, wrapEl) {
    const ExpandControl = L.Control.extend({
      options: { position: "topright" },
      onAdd() {
        const btn = L.DomUtil.create("div", "leaflet-bar leaflet-control map-expand-btn");
        btn.innerHTML = "⛶";
        btn.title = "Toggle fullscreen";
        btn.onclick = (e) => {
          e.stopPropagation();
          overlayFullscreen = !overlayFullscreen;
          if (overlayFullscreen) {
            wrapEl.classList.add("map-fullscreen");
          } else {
            wrapEl.classList.remove("map-fullscreen");
          }
          setTimeout(() => map.invalidateSize(), 100);
        };
        return btn;
      }
    });
    map.addControl(new ExpandControl());
  }

  function destroyOverlayMap() {
    if (overlayMap) { overlayMap.remove(); overlayMap = null; }
  }

  async function renderOverlayMap() {
    await tick();
    destroyOverlayMap();
    if (!overlayMapEl || !parkOverlay || parkOverlay.latitude == null) return;
    overlayMap = L.map(overlayMapEl, { scrollWheelZoom: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
      maxZoom: 18,
    }).addTo(overlayMap);
    const ll = [parkOverlay.latitude, parkOverlay.longitude];
    L.marker(ll).addTo(overlayMap)
      .bindPopup(`<b>${parkOverlay.reference}</b><br>${parkOverlay.name || ""}`)
      .openPopup();
    overlayMap.setView(ll, 12);
    addExpandControl(overlayMap, overlayMapEl);
  }

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
          potaParkName = match.name;
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
    if (park.location_name && !state) state = park.location_name;
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
    if (overlayFullscreen && overlayMapEl) overlayMapEl.classList.remove("map-fullscreen");
    overlayFullscreen = false;
    destroyOverlayMap();
    parkOverlay = null;
    parkOverlayLoading = false;
  }

  function onParkOverlayKeydown(e) {
    if (e.key === "Escape") {
      if (overlayFullscreen && overlayMapEl) {
        overlayMapEl.classList.remove("map-fullscreen");
        overlayFullscreen = false;
        setTimeout(() => overlayMap?.invalidateSize(), 100);
        return;
      }
      closeParkOverlay();
    }
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
    if (parkOverlay) renderOverlayMap();
  }

  function editContact(c) {
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
    grid = c.grid || "";
    skcc = c.skcc || "";
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
    errorMsg = "";
    const match = countries.find(co => co.name === country);
    fetchSubdivisions(match ? match.code : "");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() {
    editingId = null;
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
        grid: grid.trim().toUpperCase() || null,
        skcc: skcc.trim().toUpperCase() || null,
        comments: comments || null,
        notes: notes || null,
        timestamp: `${datePart}T${timePart || "00:00:00"}Z`,
      };
      const res = await fetch(`/api/contacts/${editingId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        editingId = null;
        dispatch("editchange", null);
        clearForm();
        await fetchContacts();
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
    grid = "";
    skcc = "";
    comments = "";
    notes = "";
    datePart = "";
    timePart = "";
    subdivisions = [];
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
        grid: grid.trim().toUpperCase() || null,
        skcc: skcc.trim().toUpperCase() || null,
        comments: comments || null,
        notes: notes || null,
        timestamp: `${datePart}T${timePart || "00:00:00"}Z`,
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
        comments = "";
        notes = "";
        datePart = "";
        timePart = "";
        await fetchContacts();
        dispatch("navigate", wasHunting ? "hunting" : "log");
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
    if (c) editContact(c);
    else loadEditFromId(editId);
  } else if (!editId) {
    handledEditId = null;
  }

  onMount(() => {
    fetchContacts();
    fetchDefaultRst();
    fetchCountries();
    fetchModes();
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
<form on:submit|preventDefault={editingId ? saveEdit : submitContact} on:keydown={e => e.key === "Enter" && e.target.tagName !== "TEXTAREA" && e.preventDefault()}>
  <h3 class="form-heading">{editingId ? "Edit QSO" : "New QSO"}{#if call.trim()} <a class="form-callsign-text" href="https://www.qrz.com/db/{call.trim().toUpperCase()}" target="_blank" rel="noopener" title="View {call.trim().toUpperCase()} on QRZ.com">{call.trim().toUpperCase()}</a>{/if}{#if callCountryCode} <span class="form-callsign-flag">{countryFlag(callCountryCode)}</span>{/if}{#if editingId} <span class="prev-contact">({relativeTime(`${datePart}T${timePart || "00:00:00"}Z`)})</span>{:else if prevContactCount > 0} <span class="prev-contact">(contacted {prevContactCount} time{prevContactCount === 1 ? "" : "s"} before)</span>{/if}</h3>
  <div class="form-row">
    <div class="field">
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
    <div class="field">
      <label for="freq">Freq (KHz) *</label>
      <input id="freq" type="text" bind:value={freq} required />
    </div>
    <div class="field">
      <label>Mode *</label>
      <Autocomplete bind:value={mode} items={availableModes} />
    </div>
    <div class="field">
      <label for="rst_sent">RST Sent</label>
      <input id="rst_sent" type="text" bind:value={rst_sent} />
    </div>
    <div class="field">
      <label for="rst_recv">RST Recv</label>
      <input id="rst_recv" type="text" bind:value={rst_recv} />
    </div>
    <div class="field field-name">
      <label for="name">Name</label>
      <input id="name" type="text" bind:value={name} />
    </div>
  </div>

  <div class="form-row">
    <div class="field">
      <label for="qth">QTH</label>
      <input id="qth" type="text" bind:value={qth} />
    </div>
    <div class="field">
      <label>Country</label>
      <Autocomplete bind:value={country} items={countryItems} on:pick={onCountryChange} on:input={onCountryChange} on:blur={normalizeCountry} />
    </div>
    <div class="field">
      <label>State</label>
      <Autocomplete bind:value={state} items={subdivisionNames} on:blur={normalizeState} />
    </div>
    <div class="field">
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
    <div class="field field-pota">
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
    <div class="field">
      <label for="skcc">SKCC</label>
      <input id="skcc" type="text" bind:value={skcc} on:input={stripSkcc} style="text-transform: uppercase" />
    </div>
    <div class="field wide">
      <label for="comments">Comments (public)</label>
      <input id="comments" type="text" bind:value={comments} />
    </div>
  </div>

  <div class="form-row">
    <div class="field">
      <label for="date">Date (UTC)</label>
      <input id="date" type="date" bind:value={datePart} />
    </div>
    <div class="field">
      <label for="time">Time (UTC)</label>
      <input id="time" type="text" bind:value={timePart} on:blur={normalizeTime} placeholder="HH:MM:SS" maxlength="8" />
    </div>
    <div class="field wide">
      <label for="notes">Notes (private)</label>
      <textarea id="notes" bind:value={notes} rows="2"></textarea>
    </div>
  </div>

  <div class="form-row">
    <button type="submit" disabled={submitting || !call.trim() || !freq.trim() || !mode.trim()}>
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
    {#if errorMsg}
      <span class="error">{errorMsg}</span>
    {/if}
  </div>
</form>
{/if}

<section class="log">
  <div class="log-title-row">
    <h2>Log ({displayedContacts.length})</h2>
    {#if prevContactCount > 0 && showForm}
      <div class="log-tabs">
        <button class="log-tab" class:active={logFilter === "all"} on:click={() => logFilter = "all"}>All</button>
        <button class="log-tab" class:active={logFilter === "call"} on:click={() => logFilter = "call"}>{call.trim().toUpperCase()}</button>
      </div>
    {/if}
  </div>
  {#if contacts.length === 0}
    <p class="empty">No contacts logged yet.</p>
  {:else}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            {#each columns as col}
              <th class="sortable" on:click={() => toggleSort(col.key)}>
                {col.label}{#if sortCol === col.key}{sortAsc ? " ▲" : " ▼"}{/if}
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each displayedContacts as c}
            <tr class="clickable" class:editing={editingId === c.id} title={relativeTime(c.timestamp)} on:click={() => editContact(c)}>
              <td>{formatTimestamp(c.timestamp)}</td>
              <td class="call">{c.call}</td>
              <td class="truncate truncate-wide">{c.name || ""}</td>
              <td>{formatFreq(c.freq)} {#if freqToBand(c.freq)}<span class="band-tag" style="background: {bandColor(freqToBand(c.freq))}; color: {bandTextColor(freqToBand(c.freq))}">{freqToBand(c.freq)}</span>{/if}</td>
              <td>{c.mode || ""}</td>
              <td class="truncate">{c.pota_park || ""}</td>
              <td class="truncate">{c.qth || ""}</td>
              <td>{c.rst_sent || ""}</td>
              <td>{c.rst_recv || ""}</td>
              <td class="truncate">{c.comments || ""}</td>
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
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <div class="park-overlay-backdrop" tabindex="0" on:click={closeParkOverlay} on:keydown={onParkOverlayKeydown} use:focusOverlay>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="park-overlay" on:click|stopPropagation>
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <span class="park-overlay-close" on:click={closeParkOverlay}>&times;</span>
      {#if parkOverlayLoading}
        <p class="park-overlay-loading">Loading park...</p>
      {:else if parkOverlay}
        <h3 class="park-overlay-ref">{parkOverlay.reference}</h3>
        <p class="park-overlay-name">{parkOverlay.name}</p>
        <div class="park-overlay-details">
          <div class="park-overlay-row"><span class="park-overlay-label">Location</span> <span>{parkOverlay.location_name || ""} ({parkOverlay.location_desc})</span></div>
          <div class="park-overlay-row"><span class="park-overlay-label">Country</span> <span>{countryFlag(prefixFromRef(parkOverlay.reference))} {parkOverlay.program_name || ""}</span></div>
          {#if parkOverlay.grid}
            <div class="park-overlay-row"><span class="park-overlay-label">Grid</span> <span>{parkOverlay.grid}</span></div>
          {/if}
          {#if parkOverlay.latitude != null && parkOverlay.longitude != null}
            <div class="park-overlay-row"><span class="park-overlay-label">Coordinates</span> <span>{parkOverlay.latitude}, {parkOverlay.longitude}</span></div>
          {/if}
          {#if parkOverlay.activations != null}
            <div class="park-overlay-row"><span class="park-overlay-label">Activations</span> <span>{parkOverlay.activations}</span></div>
          {/if}
          {#if parkOverlay.attempts != null}
            <div class="park-overlay-row"><span class="park-overlay-label">Attempts</span> <span>{parkOverlay.attempts}</span></div>
          {/if}
          {#if parkOverlay.qsos != null}
            <div class="park-overlay-row"><span class="park-overlay-label">QSOs</span> <span>{parkOverlay.qsos}</span></div>
          {/if}
          <div class="park-overlay-row">
            <span class="park-overlay-label">My QSOs</span>
            <span>{parkOverlay.my_qsos || 0} <span title="{parkAwardTitle(parkOverlay.my_qsos || 0)}">{parkAward(parkOverlay.my_qsos || 0)}</span></span>
          </div>
        </div>
        {#if parkOverlay.latitude != null && parkOverlay.longitude != null}
          <div class="park-map" bind:this={overlayMapEl}></div>
        {/if}
        <div class="park-overlay-links">
          <a href="https://pota.app/#/park/{parkOverlay.reference}" target="_blank" rel="noopener">View on POTA</a>
          <a href="#/parks/park/{encodeURIComponent(parkOverlay.reference)}">View details</a>
        </div>
        {#if parkOverlay.contacts && parkOverlay.contacts.length > 0}
          <h4 class="park-overlay-qsos-heading">My QSOs ({parkOverlay.contacts.length})</h4>
          <div class="park-overlay-qsos">
            {#each parkOverlay.contacts as c}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <div class="park-overlay-qso-row" on:click={() => { closeParkOverlay(); window.location.hash = `/log/${c.id}`; }}>
                <span class="poq-date">{c.timestamp ? c.timestamp.slice(0, 10) : ""}</span>
                <span class="poq-call">{c.call}</span>
                <span class="poq-name">{c.name || ""}</span>
                <span class="poq-mode">{c.mode || ""}</span>
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  </div>
{/if}

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
    overflow: hidden;
  }

  .field.wide {
    flex: 2;
    min-width: 240px;
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
    border-collapse: collapse;
    font-size: 0.85rem;
  }

  th {
    text-align: left;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    padding: 0.3rem 0.5rem;
    white-space: nowrap;
  }

  th.sortable {
    cursor: pointer;
    user-select: none;
  }

  th.sortable:hover {
    color: var(--accent);
  }

  td {
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid var(--bg-card);
    white-space: nowrap;
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
    z-index: 200;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .park-overlay {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1.5rem;
    max-width: 500px;
    width: 90%;
    position: relative;
  }

  .park-overlay-close {
    position: absolute;
    top: 0.5rem;
    right: 0.75rem;
    font-size: 1.4rem;
    color: var(--text-dim);
    cursor: pointer;
    line-height: 1;
  }

  .park-overlay-close:hover {
    color: var(--text);
  }

  .park-overlay-loading {
    color: var(--text-muted);
    font-style: italic;
  }

  .park-overlay-ref {
    color: var(--accent-vfo);
    font-size: 1.3rem;
    margin: 0 0 0.25rem 0;
  }

  .park-overlay-name {
    font-size: 1.1rem;
    color: var(--text);
    margin: 0 0 1rem 0;
  }

  .park-overlay-details {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin-bottom: 1rem;
  }

  .park-overlay-row {
    display: flex;
    gap: 0.75rem;
    font-size: 0.9rem;
  }

  .park-overlay-label {
    color: var(--text-dim);
    min-width: 10ch;
    flex-shrink: 0;
  }

  .park-map {
    width: 100%;
    height: 200px;
    border: 1px solid var(--border);
    border-radius: 3px;
    margin-bottom: 0.75rem;
  }

  .park-overlay-links {
    display: flex;
    gap: 1rem;
  }

  .park-overlay-links a {
    color: var(--accent);
    text-decoration: none;
    font-size: 0.85rem;
  }

  .park-overlay-links a:hover {
    text-decoration: underline;
  }

  .park-overlay-qsos-heading {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin: 0.75rem 0 0.4rem 0;
  }

  .park-overlay-qsos {
    max-height: 150px;
    overflow-y: auto;
  }

  .park-overlay-qso-row {
    display: flex;
    gap: 0.5rem;
    padding: 0.2rem 0.3rem;
    font-size: 0.8rem;
    cursor: pointer;
    border-radius: 3px;
    line-height: 1.5;
  }

  .park-overlay-qso-row:hover {
    background: var(--row-hover);
  }

  .poq-date {
    color: var(--text-dim);
    flex-shrink: 0;
  }

  .poq-call {
    color: var(--accent-callsign);
    font-weight: bold;
    flex-shrink: 0;
  }

  .poq-name {
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .poq-mode {
    color: var(--text-dim);
    flex-shrink: 0;
    margin-left: auto;
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

  :global(.map-expand-btn) {
    width: 30px;
    height: 30px;
    line-height: 30px;
    text-align: center;
    font-size: 1.2rem;
    cursor: pointer;
    background: white;
  }

  :global(.map-expand-btn:hover) {
    background: #f4f4f4;
  }

  :global(.map-fullscreen) {
    position: fixed !important;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 10000;
    width: 100% !important;
    height: 100% !important;
    max-width: none !important;
    border-radius: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
  }

  :global(.leaflet-attribution-flag) {
    display: none !important;
  }
</style>
