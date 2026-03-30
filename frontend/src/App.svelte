<script>
  import { onMount, onDestroy, tick } from "svelte";
  import Logbook from "./Logbook.svelte";
  import ExportImport from "./ExportImport.svelte";
  import Hunting from "./Hunting.svelte";
  import BandPlan from "./BandPlan.svelte";
  import GridMap from "./GridMap.svelte";
  import Search from "./Search.svelte";
  import Settings from "./Settings.svelte";
  import About from "./About.svelte";
  import Conditions from "./Conditions.svelte";
  import Parks from "./Parks.svelte";
  import Links from "./Links.svelte";
  import Notifications from "./Notifications.svelte";
  import Spots from "./Spots.svelte";
  import LogbookPicker from "./LogbookPicker.svelte";
  import SearchResults from "./SearchResults.svelte";
  import Query from "./Query.svelte";
  import { bandColor, bandTextColor } from "./bandColors.js";
  import { setLogbook, storageGet, storageSet, migrateStorage } from "./storage.js";

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

  const DUAL_RIGHT_PAGES = new Set(["hunting", "spots", "parks", "notifications", "conditions"]);

  function parseHash() {
    const hash = window.location.hash.slice(1) || "/";
    if (hash === "/picker") return { page: "picker", editId: null, dualRight: null };
    if (hash === "/grid") return { page: "grid", editId: null, dualRight: null };
    if (hash === "/about") return { page: "about", editId: null, dualRight: null };
    if (hash === "/conditions") return { page: isWide() ? "dual" : "conditions", editId: null, dualRight: "conditions" };
    if (hash === "/links") return { page: "links", editId: null, dualRight: null };
    if (hash === "/settings" || hash.startsWith("/settings/")) {
      const settingsTab = hash.split("/")[2] || null;
      return { page: "settings", editId: null, dualRight: null, settingsTab };
    }
    if (hash === "/query" || hash.startsWith("/query?")) {
      const qm = hash.indexOf("?");
      const sp = qm >= 0 ? new URLSearchParams(hash.slice(qm + 1)) : null;
      return { page: "query", editId: null, dualRight: null, querySql: sp?.get("sql") || "" };
    }
    if (hash === "/export") return { page: "export", editId: null, dualRight: null };
    if (hash === "/search" || hash.startsWith("/search?")) {
      const qm = hash.indexOf("?");
      const sp = qm >= 0 ? new URLSearchParams(hash.slice(qm + 1)) : null;
      return { page: "search", editId: null, dualRight: null, searchQuery: sp?.get("q") || "" };
    }
    if (hash === "/logbook") return { page: isWide() ? "dual" : "log", editId: null, dualRight: null };
    if (hash === "/add") return { page: isWide() ? "dual" : "add", editId: null, dualRight: null };
    // Right-pane-eligible pages
    if (hash === "/hunting") return { page: isWide() ? "dual" : "hunting", editId: null, dualRight: "hunting" };
    if (hash === "/spots" || hash.startsWith("/spots?")) return { page: isWide() ? "dual" : "spots", editId: null, dualRight: "spots" };
    if (hash === "/parks" || hash.startsWith("/parks/")) return { page: isWide() ? "dual" : "parks", editId: null, dualRight: "parks" };
    if (hash === "/notifications") return { page: isWide() ? "dual" : "notifications", editId: null, dualRight: "notifications" };
    // Dual with subpage
    const dualMatch = hash.match(/^\/dual(?:\/(\w+))?$/);
    if (dualMatch) {
      const sub = dualMatch[1] || "hunting";
      return { page: "dual", editId: null, dualRight: DUAL_RIGHT_PAGES.has(sub) ? sub : "hunting" };
    }
    const logMatch = hash.match(/^\/log\/(\d+)$/);
    if (logMatch) return { page: isWide() ? "dual" : "add", editId: parseInt(logMatch[1], 10), dualRight: null };
    return { page: isWide() ? "dual" : "log", editId: null, dualRight: null };
  }

  let wideBreakpoint = 1200;
  let wide = typeof window !== "undefined" && window.innerWidth >= 1200;
  let _parsed = parseHash();
  let { page, editId } = _parsed;
  let dualRightPage = _parsed.dualRight || "hunting";
  let previousPage = "log";
  let defaultPage = "log";
  let settingsTab = _parsed.settingsTab || null;
  let searchQuery = _parsed.searchQuery || "";
  let querySql = _parsed.querySql || "";
  let prefill = null;
  let formDirty = false;
  let activePark = "";
  let dualShowForm = !!editId || (page === "dual" && (window.location.hash.slice(1) === "/add"));
  let logbookRight = false;
  let dualSplit = 50;
  let draggingSplit = false;

  function onDividerDown(e) {
    e.preventDefault();
    draggingSplit = true;
    const onMove = (ev) => {
      const clientX = ev.touches ? ev.touches[0].clientX : ev.clientX;
      const layout = e.target.closest(".dual-layout");
      if (!layout) return;
      const rect = layout.getBoundingClientRect();
      let pct = logbookRight
        ? 100 - ((clientX - rect.left) / rect.width) * 100
        : ((clientX - rect.left) / rect.width) * 100;
      if (pct < 10) pct = 10;
      if (pct > 90) pct = 90;
      dualSplit = pct;
    };
    const onUp = () => {
      draggingSplit = false;
      storageSet("dualSplit", String(dualSplit));
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchmove", onMove);
    window.addEventListener("touchend", onUp);
  }
  let dualHunting;
  let dualParks;
  let gridMapValue = "";
  let menuOpen = false;
  let myCallsign = "";
  let customHeader = "";
  let appVersion = "";
  let updateAvailable = false;
  let updateChecked = false;
  let updateDev = false;
  let updateExact = false;
  let updateUrl = "";
  let updateLatest = "";
  let updateSupported = false;
  let updateApplying = false;
  let vfoFreq = "";
  let vfoMode = "";
  let vfoConnected = false;
  let vfoEditing = false;
  let vfoFreqInput;
  let radioModes = [];
  let vfoEditFreq = "";
  let vfoEditMode = "";
  let potaEnabled = false;
  let spotsEnabled = false;
  let solarEnabled = false;
  let sqlQueryEnabled = false;
  let flrigEnabled = false;
  let flrigInterval;
  let utcNow = new Date().toISOString().slice(0, 19).replace("T", " ") + "z";
  let clockInterval;
  let clockCopied = false;
  let unreadCount = 0;
  let prevUnreadCount = -1;
  let eventSource = null;
  let popupNotifications = [];
  let popupNotifEnabled = false;
  let showPopup = false;
  let activeDesktopNotif = null;
  let pickerMode = false;
  let logbookOpen = false;
  let currentLogbook = "";
  let pendingLogbook = "";

  async function checkLogbookMode() {
    try {
      const res = await fetch("/api/logbooks/mode");
      if (res.ok) {
        const data = await res.json();
        pickerMode = data.picker;
      }
    } catch {}
    try {
      const cur = await fetch("/api/logbooks/current");
      if (cur.ok) {
        const data = await cur.json();
        logbookOpen = data.is_open;
        currentLogbook = data.name || "";
        pendingLogbook = data.pending || "";
      }
    } catch {}
    if (!pickerMode && !logbookOpen && !pendingLogbook) {
      logbookOpen = true;
    }
  }

  let needsSetup = false;

  async function checkNeedsSetup() {
    try {
      const [csRes, gridRes] = await Promise.all([
        fetch("/api/settings/my_callsign"),
        fetch("/api/settings/my_grid"),
      ]);
      const cs = csRes.ok ? (await csRes.json()).value || "" : "";
      const grid = gridRes.ok ? (await gridRes.json()).value || "" : "";
      needsSetup = !cs || !grid;
    } catch {
      needsSetup = false;
    }
    if (needsSetup) {
      page = "settings";
      window.location.hash = "/settings";
    }
  }

  async function startAppServices() {
    fetchVersion();
    fetchUpdateCheck();
    fetchCallsign();
    fetchCustomHeader();
    await fetchDefaultPage();
    fetchPopupNotifEnabled();
    await fetchLogbookRight();
    await fetchSolarEnabled();
    await fetchSpotsEnabled();
    await fetchPotaEnabled();
    await fetchSqlQueryEnabled();
    await fetchFlrigEnabled();
    if (flrigEnabled) {
      fetchRadioModes();
      pollFlrig();
      flrigInterval = setInterval(pollFlrig, 2000);
    }
    fetchUnreadCount();
    connectSSE();
  }

  function setShutdownState() {
    serverShutdown = true;
    stopAppServices();
    document.title = "Close this tab";
    const link = document.querySelector("link[rel~='icon']") || document.createElement("link");
    link.rel = "icon";
    link.href = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💤</text></svg>";
    document.head.appendChild(link);
  }

  function clearShutdownState() {
    serverShutdown = false;
    document.title = "Rigbook";
    const link = document.querySelector("link[rel~='icon']");
    if (link) link.href = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📻</text></svg>";
  }

  async function attemptReconnect() {
    try {
      const res = await fetch("/api/settings/my_callsign");
      if (res.ok) {
        clearShutdownState();
        startAppServices();
      } else {
        alert("Server is not available yet.");
      }
    } catch {
      alert("Server is not available yet.");
    }
  }

  function stopAppServices() {
    clearInterval(flrigInterval);
    if (eventSource) { eventSource.close(); eventSource = null; }
  }

  async function handleLogbookOpened(e) {
    currentLogbook = e.detail;
    setLogbook(currentLogbook);
    dualSplit = parseFloat(storageGet("dualSplit")) || 50;
    applyTheme();
    logbookOpen = true;
    page = isWide() ? "dual" : "log";
    window.location.hash = "/";
    startAppServices();
    await checkNeedsSetup();
  }

  let serverShutdown = false;

  async function confirmPendingLogbook() {
    try {
      const res = await fetch("/api/logbooks/confirm", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        currentLogbook = data.name;
        setLogbook(currentLogbook);
        dualSplit = parseFloat(storageGet("dualSplit")) || 50;
        applyTheme();
        pendingLogbook = "";
        logbookOpen = true;
        page = isWide() ? "dual" : "log";
        window.location.hash = "/";
        startAppServices();
        await checkNeedsSetup();
      }
    } catch {}
  }

  async function declinePendingLogbook() {
    try {
      await fetch("/api/logbooks/decline", { method: "POST" });
    } catch {}
    setShutdownState();
  }

  async function closeLogbook() {
    menuOpen = false;
    try {
      await fetch("/api/logbooks/close", { method: "POST" });
    } catch {}
    stopAppServices();
    logbookOpen = false;
    currentLogbook = "";
    page = "picker";
  }

  function connectSSE() {
    if (eventSource) eventSource.close();
    eventSource = new EventSource("/api/events/stream");
    eventSource.addEventListener("unread", (e) => {
      const data = JSON.parse(e.data);
      const newCount = data.count;
      if (newCount > unreadCount && prevUnreadCount >= 0) {
        if (typeof Notification !== "undefined"
            && Notification.permission === "granted"
            && storageGet("desktop_notifications_enabled") === "true") {
          if (activeDesktopNotif) activeDesktopNotif.close();
          activeDesktopNotif = new Notification("Rigbook", {
            body: `You have ${newCount} unread notification${newCount > 1 ? "s" : ""}`,
          });
        }
        if (popupNotifEnabled) {
          showPopupNotifications();
        }
      } else if (newCount < unreadCount && activeDesktopNotif) {
        activeDesktopNotif.close();
        activeDesktopNotif = null;
      }
      prevUnreadCount = unreadCount;
      unreadCount = newCount;
    });
    eventSource.addEventListener("notification", (e) => {
      // Individual notification pushed — could be used later
    });
    eventSource.addEventListener("shutdown", () => {
      setShutdownState();
    });
    eventSource.onerror = () => {
      if (serverShutdown) return;
      // EventSource auto-reconnects; nothing to do
    };
  }

  async function fetchUnreadCount() {
    try {
      const res = await fetch("/api/notifications/unread-count");
      if (res.ok) {
        const data = await res.json();
        unreadCount = data.count;
        prevUnreadCount = data.count;
      }
    } catch {}
  }

  async function showPopupNotifications() {
    try {
      const res = await fetch("/api/notifications/");
      if (res.ok) {
        const all = await res.json();
        popupNotifications = all.filter(n => !n.read);
        if (popupNotifications.length > 0) showPopup = true;
      }
    } catch {}
  }

  async function dismissPopup() {
    // Mark all shown as read
    for (const n of popupNotifications) {
      try { await fetch(`/api/notifications/${n.id}/read`, { method: "PUT" }); } catch {}
    }
    showPopup = false;
    popupNotifications = [];
    fetchUnreadCount();
  }

  function dismissPopupKeepUnread() {
    showPopup = false;
    popupNotifications = [];
  }

  function handleNotificationClick() {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission().then(perm => {
        if (perm === "granted") {
          storageSet("desktop_notifications_enabled", "true");
        }
      });
    }
    navigate("notifications");
  }

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

  async function fetchVersion() {
    try {
      const res = await fetch("/api/version");
      if (res.ok) {
        const data = await res.json();
        appVersion = data.version || "";
      }
    } catch {}
  }

  async function fetchUpdateCheck() {
    try {
      const res = await fetch("/api/update-check");
      if (res.ok) {
        const data = await res.json();
        updateChecked = !!data.latest;
        updateDev = data.is_dev || false;
        updateExact = data.is_exact || false;
        updateLatest = data.latest || "";
        updateUrl = data.url || "";
      }
    } catch {}
    try {
      const res = await fetch("/api/update/platform");
      if (res.ok) {
        const data = await res.json();
        updateSupported = data.supported || false;
      }
    } catch {}
    // Only show "Update Available" banner for GitHub release binaries
    updateAvailable = updateSupported && !!updateLatest && !updateExact && !updateDev;
  }

  async function applyUpdateFromHeader() {
    if (updateApplying) return;
    updateApplying = true;
    try {
      const res = await fetch("/api/update/apply", { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        console.error("Update failed:", data.detail || data);
        updateApplying = false;
        return;
      }
      if (data.status === "up_to_date") {
        updateApplying = false;
        return;
      }
      await new Promise(r => setTimeout(r, 2000));
      for (let i = 0; i < 30; i++) {
        try {
          const check = await fetch("/api/version");
          if (check.ok) { window.location.reload(); return; }
        } catch {}
        await new Promise(r => setTimeout(r, 1000));
      }
      updateApplying = false;
    } catch (e) {
      console.error("Update error:", e);
      updateApplying = false;
    }
  }

  async function fetchPopupNotifEnabled() {
    try {
      const res = await fetch("/api/settings/popup_notifications_enabled");
      if (res.ok) {
        const data = await res.json();
        popupNotifEnabled = data.value === "true";
      }
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

  async function fetchDefaultPage() {
    try {
      const res = await fetch("/api/settings/default_page");
      if (res.ok) {
        const data = await res.json();
        defaultPage = data.value || "log";
      }
    } catch {}
  }

  async function fetchCustomHeader() {
    try {
      const res = await fetch("/api/settings/custom_header");
      if (res.ok) {
        const data = await res.json();
        customHeader = data.value || "";
      }
    } catch {}
  }

  async function fetchSolarEnabled() {
    try {
      const res = await fetch("/api/settings/solar_enabled");
      if (res.ok) {
        const data = await res.json();
        solarEnabled = data.value === "true";
      }
    } catch {}
  }

  async function fetchLogbookRight() {
    try {
      const res = await fetch("/api/settings/logbook_right");
      if (res.ok) {
        const data = await res.json();
        logbookRight = data.value === "true";
      }
    } catch {}
  }

  async function fetchSpotsEnabled() {
    try {
      const [rbnRes, haRes] = await Promise.all([
        fetch("/api/settings/rbn_enabled"),
        fetch("/api/settings/hamalert_enabled"),
      ]);
      let rbn = false, ha = false;
      if (rbnRes.ok) { const d = await rbnRes.json(); rbn = d.value === "true"; }
      if (haRes.ok) { const d = await haRes.json(); ha = d.value === "true"; }
      spotsEnabled = rbn || ha;
    } catch {}
  }

  async function fetchPotaEnabled() {
    try {
      const res = await fetch("/api/settings/pota_enabled");
      if (res.ok) {
        const data = await res.json();
        potaEnabled = data.value !== "false";
      }
    } catch {}
  }

  async function fetchSqlQueryEnabled() {
    try {
      const res = await fetch("/api/settings/sql_query_enabled");
      if (res.ok) {
        const data = await res.json();
        sqlQueryEnabled = data.value === "true";
      }
    } catch {}
  }

  async function fetchFlrigEnabled() {
    try {
      const res = await fetch("/api/settings/flrig_enabled");
      if (res.ok) {
        const data = await res.json();
        flrigEnabled = data.value === "true";
      }
    } catch {}
  }

  function isWide() {
    return typeof window !== "undefined" && window.innerWidth >= wideBreakpoint;
  }

  function goHome() {
    navigate(defaultPage);
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

  let previousHash = "";
  let navigating = false;

  function navigate(p) {
    if (p === "back") {
      if (previousHash) {
        window.location.hash = previousHash;
        previousHash = "";
        const parsed = parseHash();
        page = parsed.page;
        if (parsed.dualRight) dualRightPage = parsed.dualRight;
        editId = null;
        menuOpen = false;
        fetchCallsign();
        return;
      }
      p = previousPage;
    }
    // Block navigation away from dirty form (but allow switching dual right pane)
    if (formDirty && (page === "add" || page === "dual")) {
      const stayingOnDual = isWide() && (p === "add" || p === "log" || DUAL_RIGHT_PAGES.has(p));
      if (!stayingOnDual) {
        alert("Save or cancel your current QSO before navigating away.");
        return;
      }
    }
    // Redirect disabled pages to home
    if (p === "spots" && !spotsEnabled) p = "log";
    if (p === "parks" && !potaEnabled) p = "log";
    if (p === "conditions" && !solarEnabled) p = "log";
    if (p === "query" && !sqlQueryEnabled) p = "log";

    if (isWide() && (p === "add" || p === "log" || DUAL_RIGHT_PAGES.has(p))) {
      if (DUAL_RIGHT_PAGES.has(p)) dualRightPage = p;
      p = "dual";
    }
    if (page !== p) {
      previousPage = page;
      previousHash = window.location.hash.slice(1) || "/";
    }
    const wasPage = page;
    page = p;
    // Don't clear editId when staying on dual (switching right pane only)
    if (!(wasPage === "dual" && p === "dual")) editId = null;
    menuOpen = false;
    navigating = true;
    if (p === "dual") {
      window.location.hash = `/dual/${dualRightPage}`;
    } else {
      const paths = { hunting: "/hunting", log: "/logbook", add: "/add", grid: "/grid", parks: "/parks", spots: "/spots", query: "/query", export: "/export", search: "/search", notifications: "/notifications", conditions: "/conditions", settings: settingsTab ? `/settings/${settingsTab}` : "/settings", links: "/links", about: "/about", picker: "/picker" };
      window.location.hash = paths[p] || "/";
    }
    setTimeout(() => { navigating = false; }, 0);
    fetchCallsign();
  }

  function spotFreqHz(spot) {
    // POTA spots: frequency in MHz (e.g. 14.074)
    // SKCC/RBN spots: frequency in KHz (e.g. 14074)
    const f = parseFloat(spot.frequency);
    return String(f >= 1000 ? f * 1000 : f * 1000000);
  }

  async function tuneOnly(spot) {
    if (formDirty) {
      alert("Cannot tune radio while editing a QSO. Save or cancel first.");
      return;
    }
    if (!flrigEnabled) return;
    try {
      await fetch("/api/flrig/vfo", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ freq: spotFreqHz(spot), mode: spot.mode }),
      });
      pollFlrig();
    } catch {}
  }

  async function tuneAndPrefill(spot) {
    if (formDirty) {
      alert("Save or cancel your current QSO before selecting a new spot.");
      return;
    }

    await tuneOnly(spot);

    // If in edit mode but clean, clear edit to accept new spot
    if (editId) {
      editId = null;
      await tick();
    }

    // SKCC/RBN spot (has callsign field, no activator)
    if (spot.callsign && !spot.activator) {
      prefill = {
        call: String(spot.callsign || ""),
        freq: String(spot.frequency || ""),
        mode: String(spot.mode || ""),
        skcc: String(spot.skcc || ""),
        country: String(spot.country || ""),
        state: String(spot.qrz_state || ""),
      };
      dualShowForm = true;
      if (page !== "dual") navigate("add");
      return;
    }

    // POTA spot
    const loc = spot.locationDesc || "";
    let spotCountry = "";
    let spotState = "";
    if (loc.startsWith("US-")) {
      spotCountry = "United States";
    }
    if (spot.reference) {
      try {
        const res = await fetch(`/api/pota/park/${encodeURIComponent(spot.reference)}`);
        if (res.ok) {
          const park = await res.json();
          if (park.program_name) spotCountry = park.program_name;
          if (park.locations && park.locations.length === 1) {
            spotState = park.locations[0].name || "";
          } else if (park.locations && loc) {
            const match = park.locations.find(l => l.descriptor === loc);
            if (match) spotState = match.name || "";
          }
        }
      } catch {}
    }
    prefill = {
      call: spot.activator || "",
      freq: spot.frequency || "",
      mode: spot.mode || "",
      pota_park: spot.reference || "",
      grid: spot.grid4 || "",
      country: spotCountry,
      state: spotState,
    };
    dualShowForm = true;
    if (page !== "dual") navigate("add");
  }

  function handleSearchAction(e) {
    const { type, data } = e.detail;
    if (type === "logbook") {
      if (formDirty) { alert("Save or cancel your current QSO before selecting a new spot."); return; }
      const target = isWide() ? "dual" : "add";
      if ((target === "add" || target === "hunting" || target === "log") && isWide()) { /* already dual */ }
      if (page !== target) previousPage = page;
      page = target;
      menuOpen = false;
      dualShowForm = true;
      editId = data.id;
      window.location.hash = `/log/${data.id}`;
      fetchCallsign();
    } else if (type === "park") {
      navigate("parks");
      window.location.hash = `/parks/park/${encodeURIComponent(data.reference)}`;
    } else if (type === "pota") {
      tuneAndPrefill(data);
    } else if (type === "skcc") {
      if (formDirty) { alert("Save or cancel your current QSO before selecting a new spot."); return; }
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
    } else if (type === "search") {
      searchQuery = data.query || "";
      page = "search";
      menuOpen = false;
      window.location.hash = `/search?q=${encodeURIComponent(searchQuery)}`;
      return;
    } else if (type === "qrz") {
      if (formDirty) { alert("Save or cancel your current QSO before selecting a new spot."); return; }
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

  async function onHashChange() {
    if (navigating) return;
    const parsed = parseHash();
    let p = parsed.page;
    // Redirect disabled pages
    if (p === "spots" && !spotsEnabled) p = isWide() ? "dual" : "log";
    if (p === "parks" && !potaEnabled) p = isWide() ? "dual" : "log";
    if (p === "conditions" && !solarEnabled) p = isWide() ? "dual" : "log";
    if (p === "query" && !sqlQueryEnabled) p = isWide() ? "dual" : "log";
    // Don't clear editId when staying on dual (e.g. switching right pane)
    if (!(page === "dual" && p === "dual" && editId && !parsed.editId)) {
      editId = parsed.editId;
    }
    settingsTab = parsed.settingsTab || null;
    searchQuery = parsed.searchQuery || "";
    querySql = parsed.querySql || "";
    page = p;
    if (parsed.dualRight) {
      if ((parsed.dualRight === "spots" && !spotsEnabled) || (parsed.dualRight === "parks" && !potaEnabled) || (parsed.dualRight === "conditions" && !solarEnabled)) {
        // Don't set disabled right page
      } else {
        dualRightPage = parsed.dualRight;
      }
    }
    fetchCallsign();
    const wasEnabled = flrigEnabled;
    await fetchFlrigEnabled();
    if (flrigEnabled && !wasEnabled) {
      fetchRadioModes();
      pollFlrig();
      flrigInterval = setInterval(pollFlrig, 2000);
    } else if (!flrigEnabled && wasEnabled) {
      clearInterval(flrigInterval);
      vfoFreq = "";
      vfoMode = "";
      vfoConnected = false;
    }
    fetchWideBreakpoint();
  }

  function applyThemeFromCache() {
    const cached = storageGet("rigbook-theme");
    const theme = cached || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    document.documentElement.classList.toggle("light", theme === "light");
  }

  async function applyTheme() {
    applyThemeFromCache();
    try {
      const res = await fetch("/api/settings/theme");
      if (res.ok) {
        const data = await res.json();
        if (data.value) {
          storageSet("rigbook-theme", data.value);
          document.documentElement.classList.toggle("light", data.value === "light");
          return;
        }
      }
    } catch {}
    // No theme in DB — use system preference
    const sysPref = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    storageSet("rigbook-theme", sysPref);
    document.documentElement.classList.toggle("light", sysPref === "light");
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
    } else if (e.key === "s" || e.key === "S") {
      e.preventDefault();
      navigate("spots");
    } else if (e.key === "p" || e.key === "P") {
      e.preventDefault();
      navigate("parks");
    } else if ((e.key === "m" || e.key === "M") && flrigEnabled) {
      e.preventDefault();
      cycleMode();
    } else if ((e.key === "t" || e.key === "T") && flrigEnabled) {
      e.preventDefault();
      startVfoEdit();
    } else if (e.key === "?") {
      e.preventDefault();
      navigate("about");
    }
  }

  onMount(async () => {
    migrateStorage();
    fetchVersion();
    applyTheme();
    window.addEventListener("keydown", onGlobalKeydown);
    fetchWideBreakpoint();
    clockInterval = setInterval(() => { utcNow = new Date().toISOString().slice(0, 19).replace("T", " ") + "z"; }, 1000);
    window.addEventListener("hashchange", onHashChange);
    window.addEventListener("resize", onResize);
    await checkLogbookMode();
    setLogbook(currentLogbook);
    dualSplit = parseFloat(storageGet("dualSplit")) || 50;
    applyTheme();
    if (logbookOpen) {
      await startAppServices();
      await checkNeedsSetup();
      // Navigate to default page on initial load (no specific hash)
      const initHash = window.location.hash.slice(1) || "/";
      if (initHash === "/" && defaultPage !== "log") {
        navigate(defaultPage);
      }
    } else if (pickerMode) {
      page = "picker";
    }
  });

  function onResize() {
    wide = isWide();
    if (page === "dual" && !wide) {
      if (formDirty || dualShowForm || editId) {
        // Keep dual page alive so Logbook component isn't destroyed;
        // the right pane is hidden via CSS when not wide
      } else {
        navigate(dualRightPage);
      }
    } else if (wide && (page === "log" || DUAL_RIGHT_PAGES.has(page))) {
      if (DUAL_RIGHT_PAGES.has(page)) dualRightPage = page;
      navigate("dual");
    }
  }

  onDestroy(() => {
    clearInterval(flrigInterval);
    clearInterval(clockInterval);
    if (eventSource) eventSource.close();
    window.removeEventListener("hashchange", onHashChange);
    window.removeEventListener("resize", onResize);
    window.removeEventListener("keydown", onGlobalKeydown);
  });
</script>

<main class:dual-mode={page === "dual"} class:parks-mode={page === "parks"} class:spots-mode={page === "spots"} class:grid-mode={page === "grid"} class:export-mode={page === "export"} class:search-mode={page === "search"} class:query-mode={page === "query"}>
  {#if serverShutdown}
    <header>
      <div class="header-left">
        <h1 class="app-title"><span class="title-full">Rigbook</span><span class="title-short">RB</span>{#if appVersion}<span class="app-version" title={updateChecked && updateExact ? "Up to date" : updateChecked && updateDev ? "Development version" : !updateChecked ? "Enable update checker in the settings" : ""} on:click={() => navigate("about")} style="cursor: pointer">v{appVersion}{#if updateSupported && updateChecked && updateExact}<span class="up-to-date-check">✔</span>{/if}{#if updateChecked && updateDev}<span class="dev-version">🚧</span>{/if}{#if updateAvailable} <button class="update-link-btn" title={"v" + updateLatest + " available — click to update"} on:click|stopPropagation={applyUpdateFromHeader} disabled={updateApplying}>{updateApplying ? "Updating…" : "Update Available"}</button>{/if}</span>{/if}</h1>
      </div>
    </header>
    <div class="welcome-container">
      <div class="welcome-card">
        <p>Server has shut down.</p>
        <button class="welcome-btn" on:click={attemptReconnect}>Reconnect</button>
      </div>
    </div>
  {:else if pendingLogbook}
    <header>
      <div class="header-left">
        <h1 class="app-title"><span class="title-full">Rigbook</span><span class="title-short">RB</span>{#if appVersion}<span class="app-version" title={updateChecked && updateExact ? "Up to date" : updateChecked && updateDev ? "Development version" : !updateChecked ? "Enable update checker in the settings" : ""} on:click={() => navigate("about")} style="cursor: pointer">v{appVersion}{#if updateSupported && updateChecked && updateExact}<span class="up-to-date-check">✔</span>{/if}{#if updateChecked && updateDev}<span class="dev-version">🚧</span>{/if}{#if updateAvailable} <button class="update-link-btn" title={"v" + updateLatest + " available — click to update"} on:click|stopPropagation={applyUpdateFromHeader} disabled={updateApplying}>{updateApplying ? "Updating…" : "Update Available"}</button>{/if}</span>{/if}</h1>
      </div>
      <span class="utc-clock">{utcNow}</span>
    </header>
    <div class="welcome-container">
      <div class="welcome-card">
        <h2>Create New Logbook?</h2>
        <p>The logbook <strong>{pendingLogbook}</strong> does not exist yet. Would you like to create it?</p>
        <div class="welcome-buttons">
          <button class="welcome-btn confirm" on:click={confirmPendingLogbook}>Yes, create it</button>
          <button class="welcome-btn decline" on:click={declinePendingLogbook}>No, shut down</button>
        </div>
      </div>
    </div>
  {:else if pickerMode && !logbookOpen}
    <header>
      <div class="header-left">
        <h1 class="app-title"><span class="title-full">Rigbook</span><span class="title-short">RB</span>{#if appVersion}<span class="app-version" title={updateChecked && updateExact ? "Up to date" : updateChecked && updateDev ? "Development version" : !updateChecked ? "Enable update checker in the settings" : ""} on:click={() => navigate("about")} style="cursor: pointer">v{appVersion}{#if updateSupported && updateChecked && updateExact}<span class="up-to-date-check">✔</span>{/if}{#if updateChecked && updateDev}<span class="dev-version">🚧</span>{/if}{#if updateAvailable} <button class="update-link-btn" title={"v" + updateLatest + " available — click to update"} on:click|stopPropagation={applyUpdateFromHeader} disabled={updateApplying}>{updateApplying ? "Updating…" : "Update Available"}</button>{/if}</span>{/if}</h1>
      </div>
      <span class="utc-clock">{utcNow}</span>
    </header>
    <LogbookPicker on:logbookopened={handleLogbookOpened} />
  {:else}
  <header>
    <div class="header-left">
      <div class="title-group">
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
        <h1 class="app-title" on:click={goHome} style="cursor: pointer"><span class="title-full">Rigbook</span><span class="title-short">RB</span></h1>
        {#if appVersion}<span class="app-version" title={updateChecked && updateExact ? "Up to date" : updateChecked && updateDev ? "Development version" : !updateChecked ? "Enable update checker in the settings" : ""} on:click={() => navigate("about")} style="cursor: pointer">v{appVersion}{#if updateSupported && updateChecked && updateExact}<span class="up-to-date-check">✔</span>{/if}{#if updateChecked && updateDev}<span class="dev-version">🚧</span>{/if}{#if updateAvailable} <button class="update-link-btn" title={"v" + updateLatest + " available — click to update"} on:click|stopPropagation={applyUpdateFromHeader} disabled={updateApplying}>{updateApplying ? "Updating…" : "Update Available"}</button>{/if}</span>{/if}
      </div>
      {#if customHeader || myCallsign}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <span class={customHeader ? "custom-header" : "callsign"} on:click={() => { settingsTab = customHeader ? "appearance" : "station"; navigate("settings"); }} style="cursor: pointer">{customHeader || myCallsign}{#if currentLogbook && currentLogbook !== "rigbook"}<span class="logbook-name" title={"Current database: " + currentLogbook}>{currentLogbook}</span>{/if}</span>
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
      {:else if flrigEnabled}
        <span class="vfo disconnected" title="Radio not connected">❌ No Radio</span>
      {/if}
    </div>
    {#if page !== "search"}<Search bind:this={searchComponent} on:action={handleSearchAction} />{/if}
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <span class="utc-clock" on:click={copyUtcTimestamp} title="Click to copy">{clockCopied ? "Copied!" : utcNow}</span>
    <div class="hamburger-wrap">
      {#if wide}
        <button class="add-btn dual-btn" class:active-nav={dualRightPage === "hunting"} on:click={() => navigate("hunting")} title="Logbook & Hunting">{#if dualRightPage === "hunting" && !logbookRight}📖{/if}🧭{#if dualRightPage === "hunting" && logbookRight}📖{/if}</button>
        {#if spotsEnabled}<button class="add-btn dual-btn" class:active-nav={dualRightPage === "spots"} on:click={() => navigate("spots")} title="Logbook & Spots">{#if dualRightPage === "spots" && !logbookRight}📖{/if}🗺️{#if dualRightPage === "spots" && logbookRight}📖{/if}</button>{/if}
        {#if potaEnabled}<button class="add-btn dual-btn parks-btn" class:active-nav={dualRightPage === "parks"} on:click={() => navigate("parks")} title="Logbook & Parks">{#if dualRightPage === "parks" && !logbookRight}📖{/if}🌲{#if dualRightPage === "parks" && logbookRight}📖{/if}</button>{/if}
        <button class="add-btn dual-btn notification-btn" class:active-nav={dualRightPage === "notifications"} on:click={handleNotificationClick} title="Logbook & Notifications">{#if dualRightPage === "notifications" && !logbookRight}📖{/if}{#if unreadCount > 0}<span class="notif-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>{:else}✉️{/if}{#if dualRightPage === "notifications" && logbookRight}📖{/if}</button>
        {#if solarEnabled}<button class="add-btn dual-btn" class:active-nav={dualRightPage === "conditions"} on:click={() => navigate("conditions")} title="Logbook & Conditions">{#if dualRightPage === "conditions" && !logbookRight}📖{/if}🌤️{#if dualRightPage === "conditions" && logbookRight}📖{/if}</button>{/if}
      {:else}
        <button class="add-btn" on:click={() => navigate("log")} title="Logbook">📖</button>
        <button class="add-btn" on:click={() => navigate("hunting")} title="Hunting">🧭</button>
        {#if spotsEnabled}<button class="add-btn" on:click={() => navigate("spots")} title="Spots">🗺️</button>{/if}
        {#if potaEnabled}<button class="add-btn parks-btn" on:click={() => navigate("parks")} title="My Parks">🌲</button>{/if}
        <button class="add-btn notification-btn" class:has-unread={unreadCount > 0} on:click={handleNotificationClick} title="Notifications">
          {#if unreadCount > 0}
            <span class="notif-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>
          {:else}
            ✉️
          {/if}
        </button>
        {#if solarEnabled}<button class="add-btn" on:click={() => navigate("conditions")} title="Conditions">🌤️</button>{/if}
      {/if}
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
          <button class="menu-item" class:active={page === "log" || page === "dual"} on:click={() => navigate("log")}>Logbook</button>
          <button class="menu-item" class:active={page === "add"} on:click={() => navigate("add")}>Add QSO</button>
          <button class="menu-item" class:active={page === "hunting" || (page === "dual" && dualRightPage === "hunting")} on:click={() => navigate("hunting")}>Hunting</button>
          <button class="menu-item" class:active={page === "grid"} on:click={() => navigate("grid")}>Grid Map</button>
          {#if spotsEnabled}<button class="menu-item" class:active={page === "spots" || (page === "dual" && dualRightPage === "spots")} on:click={() => navigate("spots")}>Spots</button>{/if}
          {#if potaEnabled}<button class="menu-item" class:active={page === "parks" || (page === "dual" && dualRightPage === "parks")} on:click={() => navigate("parks")}>Parks</button>{/if}
          <button class="menu-item" class:active={page === "notifications" || (page === "dual" && dualRightPage === "notifications")} on:click={() => navigate("notifications")}>Notifications{#if unreadCount > 0} ({unreadCount}){/if}</button>
          {#if solarEnabled}<button class="menu-item" class:active={page === "conditions" || (page === "dual" && dualRightPage === "conditions")} on:click={() => navigate("conditions")}>Conditions</button>{/if}
          <button class="menu-item" class:active={page === "search"} on:click={() => { searchQuery = ""; navigate("search"); }}>Search</button>
          <button class="menu-item" class:active={page === "export"} on:click={() => navigate("export")}>Import / Export</button>
          {#if sqlQueryEnabled}<button class="menu-item" class:active={page === "query"} on:click={() => navigate("query")}>SQL Query</button>{/if}
          <button class="menu-item" class:active={page === "settings"} on:click={() => navigate("settings")}>Settings</button>
          <button class="menu-item" class:active={page === "links"} on:click={() => navigate("links")}>Links</button>
          <button class="menu-item" class:active={page === "about"} on:click={() => navigate("about")}>About</button>
          {#if pickerMode}
            <div class="menu-separator"></div>
            <button class="menu-item close-logbook" on:click={closeLogbook}>Close Logbook</button>
          {/if}
        </nav>
      {/if}
    </div>
  </header>

  {#if page === "dual"}
    <div class="dual-layout" class:dual-narrow={!wide} class:dragging={draggingSplit} class:dual-reversed={logbookRight}>
      <div class="dual-pane" style="flex: 0 0 {dualSplit}%">
        <Logbook showForm={dualShowForm || !!prefill || !!editId} {prefill} {editId} {vfoFreq} {vfoMode} bind:formDirty bind:activePark on:editchange={e => { editId = e.detail; dualShowForm = !!e.detail; }} on:navigate={e => { if (e.detail === "hunting" || e.detail === "log" || e.detail === "back") { prefill = null; editId = null; dualShowForm = false; dualHunting?.refreshAwards(); if (!wide) navigate(dualRightPage); } else navigate(e.detail); }} on:prefillconsumed={() => prefill = null} on:parkschanged={() => dualParks?.refreshParks()} />
      </div>
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <div class="dual-divider" on:mousedown={onDividerDown} on:touchstart={onDividerDown}></div>
      <div class="dual-pane" style="flex: 1">
        {#if dualRightPage === "hunting"}
          <Hunting bind:this={dualHunting} {potaEnabled} {spotsEnabled} on:tune={e => tuneOnly(e.detail)} on:addqso={e => tuneAndPrefill(e.detail)} />
        {:else if dualRightPage === "spots"}
          <Spots {potaEnabled} on:tune={e => tuneOnly(e.detail)} on:addqso={e => tuneAndPrefill(e.detail)} />
        {:else if dualRightPage === "parks"}
          <Parks bind:this={dualParks} {activePark} on:addqso={e => { if (formDirty) { alert("Save or cancel your current QSO before selecting a new spot."); return; } prefill = e.detail; dualShowForm = true; }} />
        {:else if dualRightPage === "notifications"}
          <Notifications on:countchange={() => fetchUnreadCount()} on:tune={e => tuneOnly(e.detail)} on:addqso={e => tuneAndPrefill(e.detail)} />
        {:else if dualRightPage === "conditions"}
          <Conditions />
        {/if}
      </div>
    </div>
  {:else if page === "parks"}
    <Parks on:addqso={e => { if (formDirty) { alert("Save or cancel your current QSO before selecting a new spot."); return; } prefill = e.detail; dualShowForm = true; navigate(isWide() ? "dual" : "add"); }} />
  {:else if page === "spots"}
    <Spots {potaEnabled} on:tune={e => tuneOnly(e.detail)} on:addqso={e => tuneAndPrefill(e.detail)} />
  {:else if page === "grid"}
    <GridMap bind:value={gridMapValue} on:select={e => { gridMapValue = e.detail; }} />
  {:else}
    <div class="page-content">
    {#if page === "log"}
      <Logbook showForm={false} {vfoFreq} {vfoMode} on:editchange={e => { editId = e.detail; navigate("add"); window.location.hash = `/log/${e.detail}`; }} on:navigate={e => navigate(e.detail)} />
    {:else if page === "add"}
      <Logbook showForm={true} {editId} {prefill} {vfoFreq} {vfoMode} bind:formDirty bind:activePark on:editchange={e => { editId = e.detail; window.location.hash = e.detail ? `/log/${e.detail}` : "/add"; }} on:navigate={e => navigate(e.detail)} on:prefillconsumed={() => prefill = null} on:parkschanged={() => dualParks?.refreshParks()} />
    {:else if page === "hunting"}
      <Hunting {potaEnabled} {spotsEnabled} on:tune={e => tuneOnly(e.detail)} on:addqso={e => tuneAndPrefill(e.detail)} />
    {:else if page === "search"}
      <SearchResults initialQuery={searchQuery} on:editcontact={e => { editId = e.detail; navigate("add"); window.location.hash = `/log/${e.detail}`; }} />
    {:else if page === "query"}
      <Query initialSql={querySql} />
    {:else if page === "export"}
      <ExportImport />
    {:else if page === "notifications"}
      <Notifications on:countchange={() => fetchUnreadCount()} on:tune={e => tuneOnly(e.detail)} on:addqso={e => tuneAndPrefill(e.detail)} />
    {:else if page === "settings"}
      <Settings logbookName={currentLogbook} pickerMode={pickerMode} {needsSetup} initialTab={settingsTab} on:deleted={e => { if (e.detail.shutdown) { setShutdownState(); } else { logbookOpen = false; currentLogbook = ""; page = "picker"; } }} on:setupcomplete={async () => { needsSetup = false; fetchCallsign(); await fetchLogbookRight(); await fetchSolarEnabled(); await fetchSpotsEnabled(); await fetchPotaEnabled(); await fetchSqlQueryEnabled(); await fetchFlrigEnabled(); if (flrigEnabled && !flrigInterval) { fetchRadioModes(); pollFlrig(); flrigInterval = setInterval(pollFlrig, 2000); } navigate(isWide() ? "dual" : "log"); }} on:saved={async () => { fetchCallsign(); fetchCustomHeader(); fetchDefaultPage(); applyTheme(); fetchPopupNotifEnabled(); await fetchLogbookRight(); await fetchSolarEnabled(); await fetchSpotsEnabled(); await fetchPotaEnabled(); await fetchSqlQueryEnabled(); await fetchFlrigEnabled(); fetchUpdateCheck(); if (flrigEnabled && !flrigInterval) { fetchRadioModes(); pollFlrig(); flrigInterval = setInterval(pollFlrig, 2000); } else if (!flrigEnabled && flrigInterval) { clearInterval(flrigInterval); flrigInterval = null; } }} on:shutdown={() => { setShutdownState(); }} />
    {:else if page === "links"}
      <Links />
    {:else if page === "conditions"}
      <Conditions />
    {:else if page === "about"}
      <About />
    {/if}
    </div>
  {/if}
  {/if}
</main>

{#if showPopup}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="popup-backdrop" on:click={dismissPopup}>
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="popup-modal" on:click|stopPropagation>
      <div class="popup-header">
        <span class="popup-title">New Notifications</span>
        <button class="popup-close" on:click={dismissPopup}>✕</button>
      </div>
      <div class="popup-body">
        {#each popupNotifications as notif (notif.id)}
          <div class="popup-notif">
            <div class="popup-notif-title">{notif.title}</div>
            <div class="popup-notif-text">
              {#if notif.meta?.callsign}
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <span class="popup-clickable popup-callsign" on:click={() => { dismissPopup(); tuneAndPrefill(notif.meta); }} title="Log QSO">{notif.meta.callsign}</span>
                {" on "}
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <span class="popup-clickable popup-freq" on:click={() => { dismissPopup(); tuneOnly(notif.meta); }} title="Tune radio">{(parseFloat(notif.meta.frequency) / 1000).toFixed(3)} MHz</span>
                {" "}{notif.meta.mode}{#if notif.text.includes(" — ")} — {notif.text.split(" — ").slice(1).join(" — ")}{/if}
              {:else}
                {notif.text}
              {/if}
            </div>
            <div class="popup-notif-time">{notif.timestamp.replace("T", " ").replace("Z", "z")}</div>
          </div>
        {/each}
      </div>
      <div class="popup-footer">
        <button class="popup-btn" on:click={dismissPopupKeepUnread}>Keep Unread</button>
        <button class="popup-btn" on:click={dismissPopup}>OK</button>
        <button class="popup-btn popup-btn-go" on:click={() => { dismissPopup(); navigate("notifications"); }}>View All</button>
      </div>
    </div>
  </div>
{/if}

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
    overflow-x: clip;
  }

  main {
    max-width: 100%;
    margin: 0 auto;
    padding: 1rem;
  }

  .page-content {
    max-width: 1100px;
    margin: 0 auto;
  }

  :global(main.export-mode),
  :global(main.query-mode) {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
    box-sizing: border-box;
  }

  :global(main.export-mode) .page-content,
  :global(main.search-mode) .page-content,
  :global(main.query-mode) .page-content {
    max-width: 100%;
    margin: 0;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
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
    flex-wrap: wrap;
    min-width: 0;
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

  .custom-header {
    color: var(--text-muted);
    font-size: 1rem;
    font-weight: normal;
    font-family: system-ui, sans-serif;
  }

  .app-version,
  .logbook-name {
    display: block;
    color: var(--text-muted);
    font-size: 0.6rem;
    font-weight: normal;
    line-height: 1;
    margin-top: 0.05rem;
  }

  .up-to-date-check {
    margin-left: 0.2rem;
    opacity: 0.7;
    font-size: 0.5rem;
  }

  .dev-version {
    margin-left: 0.2rem;
    font-size: 0.5rem;
  }

  .update-link-btn {
    color: #2ecc40;
    background: none;
    border: none;
    font-weight: bold;
    margin-left: 0.3rem;
    cursor: pointer;
    font-size: inherit;
    font-family: inherit;
    padding: 0;
  }
  .update-link-btn:hover {
    text-decoration: underline;
  }
  .update-link-btn:disabled {
    opacity: 0.7;
    cursor: default;
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
    background: #394942;
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
  .add-btn.dual-btn.active-nav {
    border-bottom: 2px solid var(--border);
  }

  .add-btn:hover {
    background: #4a5f55;
  }

  .notification-btn {
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .notification-btn.has-unread {
    background: #cc8800;
    border: 2px solid #ffcc00;
  }

  .notification-btn.has-unread:hover {
    background: #b07700;
  }

  .notif-badge {
    font-size: 0.75rem;
    font-weight: bold;
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
    border: 1px solid gold;
    border-radius: 3px;
  }

  .menu-separator {
    border-top: 1px solid var(--border);
    margin: 0.25rem 0;
  }

  .menu-item.close-logbook {
    color: var(--text-muted);
  }

  .welcome-container {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: calc(100vh - 60px);
    padding: 1rem;
  }

  .welcome-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 2rem;
    width: 100%;
    max-width: 480px;
    text-align: center;
  }

  .welcome-card h2 {
    margin: 0 0 1rem;
    color: var(--accent);
    font-size: 1.4rem;
  }

  .welcome-card p {
    color: var(--text);
    margin: 0 0 1.5rem;
    line-height: 1.5;
  }

  .welcome-buttons {
    display: flex;
    gap: 1rem;
    justify-content: center;
  }

  .welcome-btn {
    padding: 0.6rem 1.5rem;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
  }

  .welcome-btn.confirm {
    background: var(--accent);
    color: #111;
  }

  .welcome-btn.confirm:hover {
    background: var(--accent-hover);
  }

  .welcome-btn.decline {
    background: var(--bg-input);
    color: var(--text);
    border: 1px solid var(--border);
  }

  .welcome-btn.decline:hover {
    background: var(--border);
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


  main.parks-mode,
  main.spots-mode,
  main.grid-mode {
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .dual-layout {
    display: flex;
    gap: 0;
    flex: 1;
    min-height: 0;
  }

  .dual-pane {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
    padding: 0 0.75rem;
    display: flex;
    flex-direction: column;
  }
  .dual-reversed {
    flex-direction: row-reverse;
  }
  .dual-divider {
    width: 5px;
    cursor: col-resize;
    background: var(--border);
    flex-shrink: 0;
    transition: background 0.15s;
  }
  .dual-divider:hover, .dual-layout.dragging .dual-divider {
    background: var(--accent);
  }
  .dual-layout.dragging {
    user-select: none;
    cursor: col-resize;
  }
  .dual-narrow .dual-divider {
    display: none;
  }
  .dual-narrow .dual-pane:last-child {
    display: none;
  }

  @media (max-width: 600px) {
    .title-full {
      display: none;
    }
    .title-short {
      display: inline;
    }
    main {
      padding: 0.5rem;
    }
    header {
      gap: 0.25rem;
    }
    .header-left {
      gap: 0.5rem;
    }
    .vfo-bezel {
      padding: 0.1rem 0.3rem;
    }
    .vfo-digit {
      font-size: 0.9rem;
    }
  }

  .popup-backdrop {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6);
    z-index: 20000;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .popup-modal {
    background: var(--bg-card);
    border: 1px solid var(--accent);
    border-radius: 6px;
    width: 90%;
    max-width: 480px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
  }

  .popup-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid var(--border);
  }

  .popup-title {
    font-weight: bold;
    font-size: 0.95rem;
    color: var(--accent);
  }

  .popup-close {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 1rem;
    cursor: pointer;
    padding: 0.2rem;
  }

  .popup-close:hover { color: var(--text); }

  .popup-body {
    padding: 0.6rem 0.8rem;
    overflow-y: auto;
    flex: 1;
  }

  .popup-notif {
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--border);
  }

  .popup-notif:last-child { border-bottom: none; }

  .popup-notif-title {
    font-weight: bold;
    font-size: 0.85rem;
    color: var(--text);
  }

  .popup-notif-text {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: 0.15rem;
  }

  .popup-notif-time {
    font-size: 0.7rem;
    color: var(--text-dim);
    margin-top: 0.1rem;
  }

  .popup-clickable {
    cursor: pointer;
    text-decoration: underline;
    text-decoration-style: dotted;
  }

  .popup-clickable:hover { text-decoration-style: solid; }

  .popup-callsign {
    color: var(--accent-callsign, #ffcc00);
    font-weight: bold;
  }

  .popup-freq {
    color: var(--accent);
  }

  .popup-footer {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
    padding: 0.6rem 0.8rem;
    border-top: 1px solid var(--border);
  }

  .popup-btn {
    background: var(--btn-secondary, #3e404a);
    color: var(--text);
    border: none;
    padding: 0.35rem 0.8rem;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 3px;
    cursor: pointer;
  }

  .popup-btn:hover { background: var(--btn-secondary-hover, #4e505a); }

  .popup-btn-go {
    background: var(--accent);
    color: var(--bg);
    font-weight: bold;
  }

  .popup-btn-go:hover { background: var(--accent-hover); }
</style>
