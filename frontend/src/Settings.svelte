<script>
  import { onMount, onDestroy, createEventDispatcher, tick } from "svelte";
  import { storageGet, storageSet } from "./storage.js";
  import { THEMES, THEME_NAMES, applyThemeVars, applyCustomThemeVars, generateCustomTheme } from "./themes.js";
  import "vanilla-colorful/hex-color-picker.js";

  export let logbookName = "";
  export let pickerMode = false;
  export let needsSetup = false;
  export let initialTab = null;
  export let highlightSection = null;
  export let clientCount = 0;

  const dispatch = createEventDispatcher();

  let update_check_enabled = true;
  let updateCheckResult = null;
  let updateChecking = false;
  let updateSupported = false;
  let updateNotWritable = false;
  let updateApplying = false;
  let updateApplyError = "";
  let updateCustomRepo = false;
  let updateGithubRepo = "";
  let updateBuildRepo = "";
  let updateBuildSha = "";
  let updateOfficialBuild = false;
  let logbook_right = false;
  let wide_breakpoint = "1200";
  let wide_mode_enabled = true;
  let theme = "dark";
  let themeContrast = 50;
  let themeBrightness = 50;
  let themeHue = 0;
  let themeSaturation = 50;
  let themeGradient = 50;
  let themeGrain = 0;
  let themeGlow = 0;
  let themeScanlines = 0;
  let themeMode = "preset"; // "preset" or "custom"
  let customBg = "#24252b";
  let customText = "#eaeaea";
  let customAccent = "#00ff88";
  let customSecondary = "#00ccff";
  let custom_header = "";

  let sql_query_enabled = false;
  let default_page = "log";

  // Global settings state
  let global_default_pick_mode = true;
  let global_default_host = "127.0.0.1";
  let global_default_port = "8073";
  let global_default_logbook_name = "guidebook";
  let global_open_browser_on_startup = true;
  let global_auto_shutdown_delay = "300";
  let global_browser_url_override = "";
  let availableLogbooks = [];
  let globalSettingsLoaded = false;

  // Track which per-logbook settings are from global defaults
  let settingSources = {};
  // Store global default values for use as placeholders
  let globalPlaceholders = {};

  const validTabs = ["features", "appearance", "updates", "data", "global"];
  let activeTab = (initialTab && validTabs.includes(initialTab)) ? initialTab : "features";
  let settingsLoaded = false;

  $: if (initialTab && validTabs.includes(initialTab)) activeTab = initialTab;
  $: if (highlightSection && settingsLoaded) {
    tick().then(() => {
      const el = document.querySelector(`[data-section="${highlightSection}"]`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
        el.classList.add("highlight-flash");
        el.addEventListener("animationend", () => el.classList.remove("highlight-flash"), { once: true });
      }
      highlightSection = null;
    });
  }

  let updateCheckLoaded = false;
  $: if (settingsLoaded && !updateCheckLoaded) {
    updateCheckLoaded = true;
    if (update_check_enabled) loadUpdateCheck();
  }

  // Desktop notifications
  let desktopNotifPermission = typeof Notification !== "undefined" ? Notification.permission : "denied";
  let desktopNotifEnabled = storageGet("desktop_notifications_enabled") === "true";
  let popupNotifEnabled = false;
  let testPending = false;

  // Shutdown
  let noShutdown = false;
  let disableShutdown = false;
  let autoShutdownOnDisconnect = false;
  let shutdownInMenu = false;

  // Backup
  let backupMessage = "";
  let backupMessageType = "";
  let backingUp = false;
  let dbInfo = null;
  let backupStatus = null;
  let autoBackupEnabled = true;
  let autoBackupHours = 24;
  let autoBackupMax = 10;
  let backupSaveTimer = null;
  let backupSettingsReady = false;

  async function loadDbInfo() {
    try {
      const res = await fetch("/api/settings/backup/db-info");
      if (res.ok) dbInfo = await res.json();
    } catch { /* ignore */ }
  }

  async function loadBackupStatus() {
    try {
      const res = await fetch("/api/settings/backup/status");
      if (res.ok) {
        backupStatus = await res.json();
        autoBackupEnabled = backupStatus.auto_enabled;
        autoBackupHours = backupStatus.interval_hours;
        autoBackupMax = backupStatus.max_backups;
        await tick();
        backupSettingsReady = true;
      }
    } catch { /* ignore */ }
  }

  function formatSize(bytes) {
    if (!bytes) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function timeAgo(iso) {
    if (!iso) return "never";
    const d = new Date(iso);
    const now = new Date();
    const mins = Math.floor((now - d) / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  }

  function formatDue(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const now = new Date();
    if (d <= now) return "now";
    const mins = Math.floor((d - now) / 60000);
    if (mins < 60) return `in ${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `in ${hrs}h`;
    const days = Math.floor(hrs / 24);
    return `in ${days}d`;
  }

  async function saveAutoBackupSettings() {
    if (!backupSettingsReady) return;  // not yet loaded -- skip spurious saves
    clearTimeout(backupSaveTimer);
    backupSaveTimer = setTimeout(async () => {
      try {
        await Promise.all([
          fetch("/api/settings/auto_backup_enabled", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: autoBackupEnabled ? "true" : "false" }),
          }),
          fetch("/api/settings/auto_backup_hours", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: String(autoBackupHours) }),
          }),
          fetch("/api/settings/auto_backup_max", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: String(autoBackupMax) }),
          }),
        ]);
        loadBackupStatus();
      } catch { /* ignore */ }
    }, 300);
  }

  async function performBackup() {
    backingUp = true;
    backupMessage = "";
    try {
      const res = await fetch("/api/settings/backup", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        const sizeKB = (data.size / 1024).toFixed(1);
        backupMessage = `Saved to ${data.path} (${sizeKB} KB)`;
        backupMessageType = "success";
      } else {
        const data = await res.json().catch(() => null);
        backupMessage = data?.detail || "Backup failed";
        backupMessageType = "error";
      }
    } catch (e) {
      backupMessage = `Backup failed: ${e.message}`;
      backupMessageType = "error";
    }
    backingUp = false;
  }

  // Danger zone
  let dangerConfirmName = "";
  let entryCount = 0;
  let deleteError = "";
  let deleting = false;
  let clearing = false;
  let clearError = "";

  async function clearAllEntries() {
    if (dangerConfirmName !== logbookName) {
      clearError = "Name does not match";
      return;
    }
    let count = "all";
    try {
      const res = await fetch("/api/records/");
      if (res.ok) { const data = await res.json(); count = data.length; }
    } catch {}
    if (!confirm(`Are you sure you want to delete ${count} entries from "${logbookName}"? This cannot be undone.`)) {
      return;
    }
    clearError = "";
    clearing = true;
    try {
      const res = await fetch("/api/records/all", { method: "DELETE" });
      if (res.ok) {
        const data = await res.json();
        clearError = `Deleted ${data.deleted} entries.`;
      } else {
        const data = await res.json().catch(() => null);
        clearError = data?.detail || "Failed to clear entries";
      }
    } catch {
      clearError = "Failed to clear entries";
    }
    clearing = false;
  }

  async function deleteLogbook() {
    if (dangerConfirmName !== logbookName) {
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

  function disconnectOthers() {
    const others = clientCount - 1;
    if (!confirm(`Disconnect ${others} other client${others !== 1 ? "s" : ""}? It may take up to 30s to process this request.`)) return;
    dispatch("disconnect-others");
  }

  async function shutdownServer() {
    if (!confirm("Are you sure you want to shut down the Guidebook server?")) return;
    dispatch("shutdown-pending");
    try {
      const res = await fetch("/api/logbooks/shutdown", { method: "POST" });
      if (res.ok) {
        dispatch("shutdown");
        dispatch("deleted", { shutdown: true });
      }
    } catch {
      dispatch("shutdown");
      dispatch("deleted", { shutdown: true });
    }
  }

  async function enableDesktopNotifications() {
    if (typeof Notification === "undefined") return;
    const perm = await Notification.requestPermission();
    desktopNotifPermission = perm;
    if (perm === "granted") {
      desktopNotifEnabled = true;
      storageSet("desktop_notifications_enabled", "true");
    }
  }

  function disableDesktopNotifications() {
    desktopNotifEnabled = false;
    storageSet("desktop_notifications_enabled", "false");
  }

  async function sendTestNotification() {
    // Ensure permission is granted before testing
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      const perm = await Notification.requestPermission();
      desktopNotifPermission = perm;
      if (perm === "granted") {
        desktopNotifEnabled = true;
        storageSet("desktop_notifications_enabled", "true");
      }
    }
    testPending = true;
    try {
      await fetch("/api/notifications/test", { method: "POST" });
    } catch {}
    setTimeout(() => { testPending = false; }, 5000);
  }

  async function onThemeChange() {
    applyThemeVars(theme, themeContrast, themeBrightness, themeHue, themeSaturation, themeGradient, themeGrain, themeGlow, themeScanlines);
    storageSet("guidebook-theme", theme);
    await saveSetting("theme", theme);
    await saveSetting("theme_mode", "preset");
    dispatch("saved");
  }


  function applyCurrentTheme() {
    if (themeMode === "preset") {
      applyThemeVars(theme, themeContrast, themeBrightness, themeHue, themeSaturation, themeGradient, themeGrain, themeGlow, themeScanlines);
    } else {
      applyCustomThemeVars(customBg, customText, customAccent, customSecondary, themeContrast, themeBrightness, themeHue, themeSaturation, themeGradient, themeGrain, themeGlow, themeScanlines);
    }
  }

  function broadcastThemePreview(key, value) {
    fetch(`/api/settings/theme-preview?key=${encodeURIComponent(key)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    }).catch(() => {});
  }

  function onContrastInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_contrast", String(themeContrast));
  }
  async function onContrastCommit() {
    applyCurrentTheme();
    await saveSetting("theme_contrast", String(themeContrast));
    dispatch("saved");
  }

  function onBrightnessInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_brightness", String(themeBrightness));
  }
  async function onBrightnessCommit() {
    applyCurrentTheme();
    await saveSetting("theme_brightness", String(themeBrightness));
    dispatch("saved");
  }

  function onHueInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_hue", String(themeHue));
  }
  async function onHueCommit() {
    applyCurrentTheme();
    await saveSetting("theme_hue", String(themeHue));
    dispatch("saved");
  }

  function onSaturationInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_saturation", String(themeSaturation));
  }
  async function onSaturationCommit() {
    applyCurrentTheme();
    await saveSetting("theme_saturation", String(themeSaturation));
    dispatch("saved");
  }

  function onGradientInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_gradient", String(themeGradient));
  }
  async function onGradientCommit() {
    applyCurrentTheme();
    await saveSetting("theme_gradient", String(themeGradient));
    dispatch("saved");
  }

  function onGrainInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_grain", String(themeGrain));
  }
  async function onGrainCommit() {
    applyCurrentTheme();
    await saveSetting("theme_grain", String(themeGrain));
    dispatch("saved");
  }

  function onGlowInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_glow", String(themeGlow));
  }
  async function onGlowCommit() {
    applyCurrentTheme();
    await saveSetting("theme_glow", String(themeGlow));
    dispatch("saved");
  }

  function onScanlinesInput() {
    applyCurrentTheme();
    broadcastThemePreview("theme_scanlines", String(themeScanlines));
  }
  async function onScanlinesCommit() {
    applyCurrentTheme();
    await saveSetting("theme_scanlines", String(themeScanlines));
    dispatch("saved");
  }

  async function resetSliders() {
    themeContrast = 50;
    themeBrightness = 50;
    themeHue = 0;
    themeSaturation = 50;
    themeGradient = 50;
    themeGrain = 0;
    themeGlow = 0;
    themeScanlines = 0;
    applyCurrentTheme();
    await Promise.all([
      saveSetting("theme_contrast", "50"),
      saveSetting("theme_brightness", "50"),
      saveSetting("theme_hue", "0"),
      saveSetting("theme_saturation", "50"),
      saveSetting("theme_gradient", "50"),
      saveSetting("theme_grain", "0"),
      saveSetting("theme_glow", "0"),
      saveSetting("theme_scanlines", "0"),
    ]);
    dispatch("saved");
  }

  async function onThemeModeChange() {
    if (themeMode === "preset") {
      applyThemeVars(theme, themeContrast, themeBrightness, themeHue, themeSaturation, themeGradient, themeGrain, themeGlow, themeScanlines);
      storageSet("guidebook-theme", theme);
      await saveSetting("theme_mode", "preset");
    } else {
      applyCustomThemeVars(customBg, customText, customAccent, customSecondary, themeContrast, themeBrightness, themeHue, themeSaturation, themeGradient, themeGrain, themeGlow, themeScanlines);
      storageSet("guidebook-theme", "custom");
      await saveSetting("theme_mode", "custom");
      await saveCustomColors();
    }
    dispatch("saved");
  }

  function onCustomColorInput() {
    applyCustomThemeVars(customBg, customText, customAccent, customSecondary, themeContrast, themeBrightness, themeHue, themeSaturation, themeGradient, themeGrain, themeGlow, themeScanlines);
    storageSet("guidebook-theme", "custom");
    broadcastThemePreview("custom_theme_colors", JSON.stringify({ bg: customBg, text: customText, accent: customAccent, secondary: customSecondary }));
  }

  async function onCustomColorCommit() {
    onCustomColorInput();
    await saveCustomColors();
    dispatch("saved");
  }

  function onCustomColorChange() {
    onCustomColorCommit();
  }

  async function saveCustomColors() {
    const colors = JSON.stringify({ bg: customBg, text: customText, accent: customAccent, secondary: customSecondary });
    await saveSetting("custom_theme_colors", colors);
  }

  let colorDragging = false;

  function colorPicker(node, { getValue, setValue }) {
    node.setAttribute("color", getValue());
    const onChange = (e) => { setValue(e.detail.value); onCustomColorInput(); };
    const onDown = () => { colorDragging = true; };
    const onUp = () => { if (colorDragging) { colorDragging = false; onCustomColorCommit(); } };
    node.addEventListener("color-changed", onChange);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchend", onUp);
    node.addEventListener("mousedown", onDown);
    node.addEventListener("touchstart", onDown);
    return {
      update({ getValue }) { node.setAttribute("color", getValue()); },
      destroy() {
        node.removeEventListener("color-changed", onChange);
        window.removeEventListener("mouseup", onUp);
        window.removeEventListener("touchend", onUp);
        node.removeEventListener("mousedown", onDown);
        node.removeEventListener("touchstart", onDown);
      },
    };
  }

  // --- Auto-save helpers ---

  async function saveSetting(key, value) {
    await fetch(`/api/settings/${key}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    });
    // Re-check source: if saved value is blank, it may fall back to global
    try {
      const res = await fetch(`/api/settings/${key}`);
      if (res.ok) {
        const data = await res.json();
        settingSources[key] = data.source || "logbook";
        if (data.source === "global" && data.value) {
          globalPlaceholders[key] = data.value;
        } else {
          delete globalPlaceholders[key];
        }
      }
    } catch {}
    settingSources = settingSources;
    globalPlaceholders = globalPlaceholders;
  }

  const dirtyFields = new Set();
  const debounceTimers = {};

  function markDirty(key) {
    dirtyFields.add(key);
    clearTimeout(debounceTimers[key]);
    debounceTimers[key] = setTimeout(() => {
      if (dirtyFields.has(key) && fieldSavers[key]) {
        dirtyFields.delete(key);
        fieldSavers[key]();
      }
    }, 2000);
  }

  async function flushPending() {
    for (const key of dirtyFields) {
      if (fieldSavers[key]) await fieldSavers[key]();
    }
    dirtyFields.clear();
  }

  async function switchTab(tab) {
    await flushPending();
    activeTab = tab;
    window.location.hash = `/settings/${tab}`;
  }

  // --- Masonry layout action ---
  function masonry(node) {
    let col1, col2;
    const MIN_WIDTH = 640;

    function collectSections() {
      const direct = [...node.querySelectorAll(":scope > .settings-section")];
      const inCols = col1 ? [...col1.querySelectorAll(":scope > .settings-section"), ...col2.querySelectorAll(":scope > .settings-section")] : [];
      return [...direct, ...inCols];
    }

    function teardownColumns() {
      if (col1 && col1.parentNode === node) {
        const sections = collectSections();
        for (const s of sections) node.appendChild(s);
        if (col1.parentNode === node) node.removeChild(col1);
        if (col2.parentNode === node) node.removeChild(col2);
      }
    }

    function layout() {
      const width = node.parentElement?.offsetWidth || node.offsetWidth;

      if (width < MIN_WIDTH) {
        teardownColumns();
        return;
      }

      const sections = collectSections();
      if (!sections.length) return;

      for (const s of sections) node.appendChild(s);
      if (col1 && col1.parentNode === node) {
        node.removeChild(col1);
        node.removeChild(col2);
      }

      if (!col1) {
        col1 = document.createElement("div");
        col1.className = "masonry-col";
        col2 = document.createElement("div");
        col2.className = "masonry-col";
      }

      const heights = sections.map(s => s.offsetHeight);

      let h1 = 0, h2 = 0;
      const assign1 = [], assign2 = [];
      for (let i = 0; i < sections.length; i++) {
        if (h1 <= h2) {
          assign1.push(sections[i]);
          h1 += heights[i];
        } else {
          assign2.push(sections[i]);
          h2 += heights[i];
        }
      }

      for (const s of assign1) col1.appendChild(s);
      for (const s of assign2) col2.appendChild(s);
      node.appendChild(col1);
      node.appendChild(col2);
    }

    let lastMode = null;

    function layoutIfModeChanged() {
      const width = node.parentElement?.offsetWidth || node.offsetWidth;
      const mode = width < MIN_WIDTH ? "single" : "dual";
      if (mode === lastMode) return;
      lastMode = mode;
      layout();
    }

    const raf = requestAnimationFrame(() => { layout(); lastMode = (node.parentElement?.offsetWidth || node.offsetWidth) < MIN_WIDTH ? "single" : "dual"; });
    let resizeTimer;
    const onResize = () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => requestAnimationFrame(layoutIfModeChanged), 150);
    };
    window.addEventListener("resize", onResize);

    return {
      destroy() {
        cancelAnimationFrame(raf);
        clearTimeout(resizeTimer);
        window.removeEventListener("resize", onResize);
        teardownColumns();
      },
    };
  }

  // --- Per-field auto-save handlers ---

  const fieldSavers = {
    wide_breakpoint: async () => {
      await saveSetting("wide_breakpoint", wide_mode_enabled ? String(wide_breakpoint) : "0");
      dispatch("saved");
    },
    custom_header: async () => {
      await saveSetting("custom_header", custom_header.trim());
      dispatch("saved");
    },
  };

  function onFieldKeydown(e) {
    if (e.key === "Enter") e.target.blur();
  }

  async function onFieldBlur(key) {
    clearTimeout(debounceTimers[key]);
    if (dirtyFields.has(key) && fieldSavers[key]) {
      dirtyFields.delete(key);
      await fieldSavers[key]();
    }
  }

  async function onSqlQueryEnabledChange() {
    await saveSetting("sql_query_enabled", sql_query_enabled ? "true" : "false");
    dispatch("saved");
  }

  async function onUpdateCheckEnabledChange() {
    await saveGlobalSetting("update_check_enabled", update_check_enabled ? "true" : "false");
    if (update_check_enabled) {
      await fetchUpdateCheck();
    } else {
      updateCheckResult = null;
    }
    dispatch("saved");
  }

  async function onLogbookRightChange() {
    await saveSetting("logbook_right", logbook_right ? "true" : "false");
    dispatch("saved");
  }

  async function onWideModeEnabledChange() {
    if (wide_mode_enabled) {
      await saveSetting("wide_breakpoint", String(wide_breakpoint));
    } else {
      await saveSetting("wide_breakpoint", "0");
    }
    dispatch("saved");
  }

  function onWideBreakpointInput() {
    markDirty("wide_breakpoint");
  }

  async function onDefaultPageChange() {
    await saveSetting("default_page", default_page);
    dispatch("saved");
  }

  function onCustomHeaderInput() {
    markDirty("custom_header");
  }

  async function fetchSettings() {
    try {
      const res = await fetch("/api/settings/");
      if (res.ok) {
        const data = await res.json();
        settingSources = {};
        globalPlaceholders = {};
        for (const s of data) {
          if (s.source) settingSources[s.key] = s.source;
          if (s.key === "sql_query_enabled") sql_query_enabled = s.value === "true";
          if (s.key === "update_check_enabled") update_check_enabled = s.value !== "false";
          if (s.key === "wide_breakpoint") {
            if (s.value === "0") {
              wide_mode_enabled = false;
              wide_breakpoint = "1200";
            } else {
              wide_mode_enabled = true;
              wide_breakpoint = s.value || "1500";
            }
          }
          if (s.key === "logbook_right") logbook_right = s.value === "true";
          if (s.key === "custom_header") custom_header = s.value || "";
          if (s.key === "default_page") default_page = s.value || "log";
          if (s.key === "theme") theme = s.value || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
          if (s.key === "theme_contrast") { const v = parseInt(s.value); themeContrast = isNaN(v) ? 50 : v; }
          if (s.key === "theme_brightness") { const v = parseInt(s.value); themeBrightness = isNaN(v) ? 50 : v; }
          if (s.key === "theme_hue") { const v = parseInt(s.value); themeHue = isNaN(v) ? 0 : v; }
          if (s.key === "theme_saturation") { const v = parseInt(s.value); themeSaturation = isNaN(v) ? 50 : v; }
          if (s.key === "theme_gradient") { const v = parseInt(s.value); themeGradient = isNaN(v) ? 50 : v; }
          if (s.key === "theme_grain") { const v = parseInt(s.value); themeGrain = isNaN(v) ? 0 : v; }
          if (s.key === "theme_glow") { const v = parseInt(s.value); themeGlow = isNaN(v) ? 0 : v; }
          if (s.key === "theme_scanlines") { const v = parseInt(s.value); themeScanlines = isNaN(v) ? 0 : v; }
          if (s.key === "theme_mode") themeMode = s.value || "preset";
          if (s.key === "custom_theme_colors") {
            try {
              const c = JSON.parse(s.value);
              if (c.bg) customBg = c.bg;
              if (c.text) customText = c.text;
              if (c.accent) customAccent = c.accent;
              if (c.secondary) customSecondary = c.secondary;
            } catch {}
          }
          if (s.key === "popup_notifications_enabled") popupNotifEnabled = s.value === "true";
        }
      }
      settingsLoaded = true;
    } catch {}
  }

  async function fetchLogbookList() {
    try {
      const res = await fetch("/api/logbooks/");
      if (res.ok) availableLogbooks = (await res.json()).map(d => d.name);
    } catch {}
  }

  async function fetchGlobalSettings() {
    try {
      const res = await fetch("/api/global-settings/");
      if (res.ok) {
        const data = await res.json();
        for (const s of data) {
          if (s.key === "default_pick_mode") global_default_pick_mode = s.value !== "false";
          if (s.key === "default_host") global_default_host = s.value || "127.0.0.1";
          if (s.key === "default_port") global_default_port = s.value || "8073";
          if (s.key === "default_logbook_name") global_default_logbook_name = s.value || "guidebook";
          if (s.key === "open_browser_on_startup") global_open_browser_on_startup = s.value !== "false";
          if (s.key === "auto_shutdown_delay") global_auto_shutdown_delay = s.value || "300";
          if (s.key === "browser_url_override") global_browser_url_override = s.value || "";
          if (s.key === "shutdown_in_menu") shutdownInMenu = s.value === "true";
          if (s.key === "auto_shutdown_on_disconnect") autoShutdownOnDisconnect = s.value === "true";
          if (s.key === "disable_shutdown") disableShutdown = s.value === "true";
          if (s.key === "update_check_enabled") update_check_enabled = s.value !== "false";
        }
        globalSettingsLoaded = true;
      }
    } catch {}
  }

  async function saveGlobalSetting(key, value) {
    await fetch(`/api/global-settings/${key}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    });
    // Re-fetch per-logbook settings so placeholders and fallbacks update
    await fetchSettings();
    dispatch("saved");
  }

  async function loadUpdateCheck() {
    try {
      const res = await fetch("/api/update-check");
      if (res.ok) updateCheckResult = await res.json();
    } catch {}
    try {
      const res = await fetch("/api/update/platform");
      if (res.ok) {
        const data = await res.json();
        updateSupported = (data.supported && data.writable) || false;
        updateNotWritable = data.supported && !data.writable;
        updateBuildRepo = data.build_origin_repo || "";
        updateBuildSha = data.build_git_sha || "";
        updateGithubRepo = data.github_repo || "";
        updateOfficialBuild = data.build_github_actions || false;
        updateCustomRepo = !!updateBuildRepo && updateBuildRepo !== "EnigmaCurry/guidebook";
      }
    } catch {}
  }

  async function skipUpdate() {
    try {
      const res = await fetch("/api/update-check/skip", { method: "POST" });
      if (res.ok && updateCheckResult) {
        updateCheckResult.update_skipped = true;
        updateCheckResult = updateCheckResult; // trigger reactivity
      }
    } catch {}
  }

  function confirmAndApplyUpdate() {
    if (!updateCheckResult) return;
    if (confirm(`Update Guidebook from v${updateCheckResult.current} to v${updateCheckResult.latest}? The server will restart.`)) {
      applyUpdate();
    }
  }

  async function applyUpdate() {
    updateApplying = true;
    updateApplyError = "";
    try {
      const res = await fetch("/api/update/apply", { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        updateApplyError = data.detail || "Update failed";
        updateApplying = false;
        return;
      }
      if (data.status === "up_to_date") {
        updateApplyError = "Already up to date";
        updateApplying = false;
        return;
      }
      // Server is restarting -- poll until it comes back
      await new Promise(r => setTimeout(r, 2000));
      for (let i = 0; i < 30; i++) {
        try {
          const check = await fetch("/api/version");
          if (check.ok) {
            window.location.reload();
            return;
          }
        } catch {}
        await new Promise(r => setTimeout(r, 1000));
      }
      updateApplyError = "Server did not come back after update -- check manually";
      updateApplying = false;
    } catch (e) {
      updateApplyError = "Update failed: " + e.message;
      updateApplying = false;
    }
  }

  async function fetchUpdateCheck() {
    updateChecking = true;
    try {
      const res = await fetch("/api/update-check?bust=true");
      if (res.ok) updateCheckResult = await res.json();
    } catch {}
    updateChecking = false;
  }

  function formatTimeAgo(epochSecs) {
    const diff = Math.floor(Date.now() / 1000 - epochSecs);
    if (diff < 5) return "just now";
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  function formatTimeUntil(epochSecs) {
    const diff = Math.floor(epochSecs - Date.now() / 1000);
    if (diff <= 0) return "soon";
    if (diff < 60) return `in ${diff}s`;
    if (diff < 3600) return `in ${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `in ${Math.floor(diff / 3600)}h`;
    return `in ${Math.floor(diff / 86400)}d`;
  }

  async function fetchEntryCount() {
    try {
      const res = await fetch("/api/records/");
      if (res.ok) { const data = await res.json(); entryCount = data.length; }
    } catch {}
  }

  async function fetchNoShutdown() {
    try {
      const res = await fetch("/api/version");
      if (res.ok) {
        const data = await res.json();
        noShutdown = !!data.no_shutdown;
        await tick();
        window.dispatchEvent(new Event("resize"));
      }
    } catch {}
  }

  async function toggleDisableShutdown() {
    await saveGlobalSetting("disable_shutdown", disableShutdown ? "true" : "false");
    await fetchNoShutdown();
  }

  onMount(() => {
    fetchSettings();
    fetchGlobalSettings();
    fetchLogbookList();
    fetchEntryCount();
    loadDbInfo();
    loadBackupStatus();
    fetchNoShutdown();
  });

  onDestroy(() => {
    flushPending();
  });
</script>

<div class="settings">
  <h2>Settings <span class="autosave-hint">(are saved automatically on change)</span></h2>

  <div class="tab-bar">
    <button class="tab" class:active={activeTab === "features"} on:click={() => switchTab("features")}>Features</button>
    <button class="tab" class:active={activeTab === "appearance"} on:click={() => switchTab("appearance")}>Appearance</button>
    <button class="tab" class:active={activeTab === "updates"} on:click={() => switchTab("updates")}>Updates</button>
    <button class="tab" class:active={activeTab === "data"} on:click={() => switchTab("data")}>Data</button>
    <button class="tab" class:active={activeTab === "global"} on:click={() => switchTab("global")}>Global</button>
  </div>

  {#if activeTab === "features"}
  <div class="tab-scroll"><div class="tab-content" use:masonry>
  <section class="settings-section">
    <h3>SQL Query (read-only view)</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={sql_query_enabled} on:change={onSqlQueryEnabledChange} />
        Enable SQL query page
      </label>
    </div>
  </section>

  <section class="settings-section">
    <h3>Notifications</h3>
    <div class="setting-row toggle-row">
      {#if desktopNotifPermission === "denied"}
        <span class="hint">Desktop notifications blocked by browser. Allow notifications for this site in your browser settings.</span>
      {:else if desktopNotifPermission === "granted" && desktopNotifEnabled}
        <span style="font-size:0.85rem; color:var(--accent);">Desktop notifications are enabled</span>
        <button class="theme-toggle" on:click={disableDesktopNotifications}>Disable</button>
      {:else if desktopNotifPermission === "granted" && !desktopNotifEnabled}
        <span style="font-size:0.85rem; color:var(--text-muted);">Desktop notifications are disabled</span>
        <button class="theme-toggle" on:click={() => { desktopNotifEnabled = true; storageSet("desktop_notifications_enabled", "true"); }}>Enable</button>
      {:else}
        <button class="theme-toggle" on:click={enableDesktopNotifications}>Enable Desktop Notifications</button>
      {/if}
    </div>
    <p class="hint">In-app notifications are always enabled. Desktop notifications show browser popups when new alerts arrive.</p>
    <div class="setting-row toggle-row" style="margin-top: 0.5rem;">
      <label>
        <input type="checkbox" bind:checked={popupNotifEnabled} on:change={async () => { await saveSetting("popup_notifications_enabled", popupNotifEnabled ? "true" : "false"); dispatch("saved"); }} />
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
  </div></div>
  {/if}

  {#if activeTab === "appearance"}
  <div class="tab-scroll"><div class="tab-content" use:masonry>
  <section class="settings-section">
    <h3>Theme</h3>
    <p class="hint">Theme changes sync live to all open windows. Try opening Guidebook side-by-side in another window to preview your changes on any page.</p>
    <div class="setting-row toggle-row">
      <label>Mode</label>
      <div class="theme-mode-switch">
        <button class="mode-btn" class:active={themeMode === "preset"} on:click={() => { themeMode = "preset"; onThemeModeChange(); }}>Preset</button>
        <button class="mode-btn" class:active={themeMode === "custom"} on:click={() => { themeMode = "custom"; onThemeModeChange(); }}>Custom</button>
      </div>
    </div>
    {#if themeMode === "preset"}
    <div class="setting-row">
      <label for="theme_select">Theme</label>
      <div class="theme-select-row">
        <select id="theme_select" bind:value={theme} on:change={onThemeChange}>
          {#each THEME_NAMES as t}
            <option value={t}>{THEMES[t].label}{t !== "dark" && t !== "light" ? ` (${THEMES[t].base})` : ""}</option>
          {/each}
        </select>
        <button class="contrast-reset" on:click={resetSliders} disabled={themeContrast === 50 && themeBrightness === 50 && themeHue === 0 && themeSaturation === 50 && themeGradient === 50 && themeGrain === 0 && themeGlow === 0 && themeScanlines === 0}>Reset Sliders</button>
      </div>
    </div>
    {:else}
    <div class="color-pickers">
      <div class="color-picker-group">
        <label>Background</label>
        <hex-color-picker use:colorPicker={{ getValue: () => customBg, setValue: (v) => { customBg = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={customBg} on:input={onCustomColorInput} on:blur={onCustomColorCommit} maxlength="7" />
      </div>
      <div class="color-picker-group">
        <label>Text</label>
        <hex-color-picker use:colorPicker={{ getValue: () => customText, setValue: (v) => { customText = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={customText} on:input={onCustomColorInput} on:blur={onCustomColorCommit} maxlength="7" />
      </div>
      <div class="color-picker-group">
        <label>Accent</label>
        <hex-color-picker use:colorPicker={{ getValue: () => customAccent, setValue: (v) => { customAccent = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={customAccent} on:input={onCustomColorInput} on:blur={onCustomColorCommit} maxlength="7" />
      </div>
      <div class="color-picker-group">
        <label>Secondary</label>
        <hex-color-picker use:colorPicker={{ getValue: () => customSecondary, setValue: (v) => { customSecondary = v; } }}></hex-color-picker>
        <input type="text" class="color-hex-input" bind:value={customSecondary} on:input={onCustomColorInput} on:blur={onCustomColorCommit} maxlength="7" />
      </div>
    </div>
    {/if}
    <div class="slider-pair">
      <div class="slider-group">
        <label for="contrast_slider">Contrast <span class="slider-value">{themeContrast}</span></label>
        <div class="slider-control">
          <input id="contrast_slider" type="range" min="40" max="60" bind:value={themeContrast} on:input={onContrastInput} on:change={onContrastCommit} />
        </div>
      </div>
      <div class="slider-group">
        <label for="brightness_slider">Brightness <span class="slider-value">{themeBrightness}</span></label>
        <div class="slider-control">
          <input id="brightness_slider" type="range" min="40" max="60" bind:value={themeBrightness} on:input={onBrightnessInput} on:change={onBrightnessCommit} />
        </div>
      </div>
    </div>
    <div class="slider-pair">
      <div class="slider-group">
        <label for="hue_slider">Hue Shift <span class="slider-value">{themeHue}&deg;</span></label>
        <div class="slider-control">
          <input id="hue_slider" type="range" min="0" max="360" bind:value={themeHue} on:input={onHueInput} on:change={onHueCommit} class="hue-range" />
        </div>
      </div>
      <div class="slider-group">
        <label for="saturation_slider">Saturation <span class="slider-value">{themeSaturation}</span></label>
        <div class="slider-control">
          <input id="saturation_slider" type="range" min="0" max="100" bind:value={themeSaturation} on:input={onSaturationInput} on:change={onSaturationCommit} />
        </div>
      </div>
    </div>
    <div class="slider-pair">
      <div class="slider-group">
        <label for="gradient_slider">Gradient <span class="slider-value">{themeGradient - 50}</span></label>
        <div class="slider-control">
          <input id="gradient_slider" type="range" min="0" max="100" bind:value={themeGradient} on:input={onGradientInput} on:change={onGradientCommit} />
        </div>
      </div>
      <div class="slider-group">
        <label for="grain_slider">Grain <span class="slider-value">{themeGrain}</span></label>
        <div class="slider-control">
          <input id="grain_slider" type="range" min="0" max="100" bind:value={themeGrain} on:input={onGrainInput} on:change={onGrainCommit} />
        </div>
      </div>
    </div>
    <div class="slider-pair">
      <div class="slider-group">
        <label for="glow_slider">Glow <span class="slider-value">{themeGlow}</span></label>
        <div class="slider-control">
          <input id="glow_slider" type="range" min="0" max="100" bind:value={themeGlow} on:input={onGlowInput} on:change={onGlowCommit} />
        </div>
      </div>
      <div class="slider-group">
        <label for="scanlines_slider">Scanlines <span class="slider-value">{themeScanlines}</span></label>
        <div class="slider-control">
          <input id="scanlines_slider" type="range" min="0" max="45" bind:value={themeScanlines} on:input={onScanlinesInput} on:change={onScanlinesCommit} />
        </div>
      </div>
    </div>
    <p class="hint">Grain, Glow, and Scanlines may impact performance on low-powered devices. Set these to 0 to disable. Grain is paper-like unless combined with Scanlines to produce static.</p>
  </section>
  <section class="settings-section" data-section="content">
    <h3>Content</h3>
    <div class="setting-row">
      <label for="custom_header">Custom Header</label>
      <input id="custom_header" type="text" bind:value={custom_header} on:input={onCustomHeaderInput} on:keydown={onFieldKeydown} on:blur={() => onFieldBlur("custom_header")} autocomplete="off" placeholder="Header text" />
      <span class="hint">Custom text displayed in the header.</span>
    </div>
    <div class="setting-row">
      <label for="default_page">Home Page</label>
      <select id="default_page" bind:value={default_page} on:change={onDefaultPageChange}>
        <option value="log">Log</option>
        <option value="notifications">Notifications</option>
      </select>
    </div>
  </section>
  <section class="settings-section">
    <h3>Wide Mode</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={wide_mode_enabled} on:change={onWideModeEnabledChange} />
        Wide Mode
      </label>
    </div>
    <div class="setting-row">
      <label for="wide_breakpoint">Breakpoint: {wide_breakpoint}px</label>
      <input id="wide_breakpoint" type="range" min="1200" max="2500" step="50" bind:value={wide_breakpoint} on:input={onWideBreakpointInput} on:change={() => onFieldBlur("wide_breakpoint")} disabled={!wide_mode_enabled} />
    </div>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={logbook_right} on:change={onLogbookRightChange} disabled={!wide_mode_enabled} />
        Logbook on right side
      </label>
    </div>
  </section>
  </div></div>
  {/if}

  {#if activeTab === "updates"}
  <div class="tab-scroll"><div class="tab-content" use:masonry>
  <section class="settings-section">
    <h3>Update Checker</h3>
    {#if updateOfficialBuild}
      <div class="setting-row toggle-row">
        <label>
          <input type="checkbox" bind:checked={update_check_enabled} on:change={onUpdateCheckEnabledChange} />
          Check for new Guidebook releases on GitHub
        </label>
      </div>
      {#if update_check_enabled && updateCheckResult}
        <div class="update-status">
          <div>Current version: <strong>v{updateCheckResult.current}</strong>{#if updateBuildSha}
            (<a href="https://github.com/{updateGithubRepo}/commit/{updateBuildSha}" target="_blank" rel="noopener" class="sha-link">{updateBuildSha}</a>){/if}
          {#if updateCheckResult.is_dev}
            — Development version — update checker is disabled
          {:else if updateCheckResult.is_exact}
            — You're running the latest version
          {:else if updateCheckResult.latest && !updateCheckResult.update_available}
            — You're ahead of the latest release (v{updateCheckResult.latest})
          {:else if !updateCheckResult.latest}
            — Unable to check for updates
          {/if}
          </div>
          {#if updateCheckResult.update_available && !updateCheckResult.update_skipped}
            <div><span class="update-available">Update available: v{updateCheckResult.latest}</span></div>
            <div class="update-actions">
              {#if updateSupported}
                <button class="check-now-btn apply-update-btn" on:click={confirmAndApplyUpdate} disabled={updateApplying}>
                  {updateApplying ? "Updating..." : "Apply Update"}
                </button>
                <button class="check-now-btn" on:click={skipUpdate}>Skip</button>
              {:else}
                <a href={updateCheckResult.url} target="_blank" rel="noopener" class="update-available">Download</a>
                {#if updateNotWritable}
                  <span class="update-error">In-app update unavailable: no write permission to the binary location</span>
                {/if}
              {/if}
              {#if updateApplyError}
                <span class="update-error">{updateApplyError}</span>
              {/if}
            </div>
          {:else if updateCheckResult.update_skipped}
            <div>v{updateCheckResult.latest} available (skipped)</div>
            <div class="update-actions">
              {#if updateSupported}
                <button class="check-now-btn apply-update-btn" on:click={confirmAndApplyUpdate} disabled={updateApplying}>
                  {updateApplying ? "Updating..." : "Apply Update"}
                </button>
              {:else}
                <a href={updateCheckResult.url} target="_blank" rel="noopener" class="update-available">Download</a>
                {#if updateNotWritable}
                  <span class="update-error">In-app update unavailable: no write permission to the binary location</span>
                {/if}
              {/if}
              {#if updateApplyError}
                <span class="update-error">{updateApplyError}</span>
              {/if}
            </div>
          {/if}
        </div>
        <div class="update-check-meta">
          {#if updateCheckResult.checked_at}
            Checked {formatTimeAgo(updateCheckResult.checked_at)}{#if updateCheckResult.next_check_at}, next check {formatTimeUntil(updateCheckResult.next_check_at)}{/if}
          {/if}
          <button class="check-now-btn" on:click={fetchUpdateCheck} disabled={updateChecking}>
            {updateChecking ? "Checking..." : "Check now"}
          </button>
        </div>
      {/if}
      {#if updateCustomRepo}
        <div class="update-custom-repo-warning">
          Warning: using custom update source <a href="https://github.com/{updateBuildRepo}" target="_blank" rel="noopener"><strong>{updateBuildRepo}</strong></a>
        </div>
      {/if}
    {:else}
      <div class="update-status">
        Version: <strong>v{updateCheckResult?.current || '...'}</strong>{#if updateBuildSha}
          (<a href="https://github.com/{updateGithubRepo}/commit/{updateBuildSha}" target="_blank" rel="noopener" class="sha-link">{updateBuildSha}</a>){/if}
      </div>
      <p class="hint">Update checking is disabled for local builds.</p>
    {/if}
  </section>
  </div></div>
  {/if}

  {#if activeTab === "data"}
  <div class="tab-scroll"><div class="tab-content" use:masonry>

  <section class="settings-section">
    <h3>Backup</h3>
    <p class="hint">Backup settings are configured separately for each logbook.</p>
    {#if dbInfo}
      <p class="hint">Database: {dbInfo.path} ({formatSize(dbInfo.size)})</p>
      <p class="hint">Backups: {dbInfo.directory}</p>
    {/if}
    <div class="setting-row">
      <button on:click={performBackup} disabled={backingUp}>
        {backingUp ? "Backing up..." : "Backup Now"}
      </button>
    </div>
    {#if backupMessage}
      <p class="hint" class:danger-error={backupMessageType === "error"} style={backupMessageType === "success" ? "color: var(--accent)" : ""}>{backupMessage}</p>
    {/if}
    <div class="setting-row toggle-row">
      <label class="toggle-label">
        <input type="checkbox" bind:checked={autoBackupEnabled} on:change={saveAutoBackupSettings} />
        Auto-backup
      </label>
    </div>
    {#if autoBackupEnabled}
      <div class="setting-row">
        <label>Interval (hours)</label>
        <input type="number" min="1" max="720" bind:value={autoBackupHours} on:input={saveAutoBackupSettings} style="width: 5rem" />
      </div>
      <div class="setting-row">
        <label>Keep max</label>
        <input type="number" min="1" max="100" bind:value={autoBackupMax} on:input={saveAutoBackupSettings} style="width: 5rem" />
      </div>
    {/if}
    {#if backupStatus}
      <p class="hint">
        {#if backupStatus.auto_enabled}
          Last auto-backup: {timeAgo(backupStatus.last_backup)} — Next: {formatDue(backupStatus.next_due)}
        {:else}
          Auto-backup disabled
        {/if}
        {#if backupStatus.auto_backup_count > 0 || backupStatus.manual_backup_count > 0}
          — {backupStatus.auto_backup_count} auto, {backupStatus.manual_backup_count} manual
        {/if}
      </p>
    {/if}
  </section>

  {#if !noShutdown}
  <section class="settings-section">
    <h3>Shutdown</h3>
    <p class="hint">Connected clients: {clientCount}</p>
    {#if clientCount > 1}
      <div class="setting-row">
        <button class="warning-btn" on:click={disconnectOthers}>Disconnect all other clients</button>
      </div>
    {/if}
    <div class="setting-row">
      <button class="danger-btn" on:click={shutdownServer}>Shutdown Now</button>
    </div>
  </section>
  {/if}

  {#if logbookName}
    <section class="settings-section danger-zone">
      <h3>Danger Zone</h3>
      <div class="setting-row">
        <label for="danger-confirm">Type <strong>{logbookName}</strong> to enable the Danger Zone</label>
        <input id="danger-confirm" type="text" bind:value={dangerConfirmName} placeholder={logbookName} autocomplete="off" />
      </div>
      <div class="danger-separator"></div>
      <p class="danger-text">Delete all entries from <strong>{logbookName}</strong> but keep the logbook and settings.</p>
      {#if clearError}
        <p class="danger-error">{clearError}</p>
      {/if}
      <div class="setting-row">
        <button class="danger-btn" on:click={clearAllEntries} disabled={clearing || dangerConfirmName !== logbookName || entryCount === 0}>
          {clearing ? "Clearing..." : entryCount === 0 ? "No entries to clear" : "Clear All Entries"}
        </button>
      </div>
      <div class="danger-separator"></div>
      <p class="danger-text">Permanently delete the logbook <strong>{logbookName}</strong> and all its data. This cannot be undone.</p>
      {#if deleteError}
        <p class="danger-error">{deleteError}</p>
      {/if}
      <div class="setting-row">
        <button class="danger-btn" on:click={deleteLogbook} disabled={deleting || dangerConfirmName !== logbookName}>
          {deleting ? "Deleting..." : "Delete Logbook"}
        </button>
      </div>
    </section>
  {/if}
  </div></div>
  {/if}

  {#if activeTab === "global"}
  <div class="tab-scroll"><p class="hint" style="max-width:1100px;margin:0 auto;width:100%;box-sizing:border-box">Global defaults are used when a per-logbook setting is not set. Changes here apply across all logbooks.</p>
  <div class="tab-content" use:masonry>

  <section class="settings-section">
    <h3>Logbook</h3>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={global_default_pick_mode} on:change={() => saveGlobalSetting("default_pick_mode", global_default_pick_mode ? "true" : "false")} />
        Ask which logbook to open on start
      </label>
    </div>
    <div class="setting-row">
      <label for="global_default_logbook">Default Logbook Name</label>
      {#if availableLogbooks.length > 0}
        <select id="global_default_logbook" bind:value={global_default_logbook_name} on:change={() => saveGlobalSetting("default_logbook_name", global_default_logbook_name)} style="max-width: 14rem">
          {#each availableLogbooks as name}
            <option value={name}>{name}</option>
          {/each}
        </select>
      {:else}
        <span class="hint">No logbooks exist yet</span>
      {/if}
      <span class="hint">Logbook opened when running guidebook without arguments</span>
    </div>
  </section>

  <section class="settings-section">
    <h3>Network</h3>
    <span class="hint">Changing these settings requires restarting guidebook.</span>
    <div class="setting-row">
      <label for="global_default_host">Default Host</label>
      <span style="display: inline-flex; align-items: center; gap: 0.5rem;">
        <input id="global_default_host" type="text" bind:value={global_default_host} on:blur={() => saveGlobalSetting("default_host", global_default_host.trim())} autocomplete="off" style="max-width: 10rem" />
        {#if global_default_host.trim() !== "127.0.0.1"}
          <button type="button" class="btn btn-sm" on:click={() => { global_default_host = "127.0.0.1"; saveGlobalSetting("default_host", "127.0.0.1"); }}>Reset</button>
        {/if}
      </span>
      <span class="hint">Bind address. Use <code>0.0.0.0</code> to listen on all interfaces. Override with <code>GUIDEBOOK_HOST</code> env var.</span>
      {#if global_default_host.trim() && global_default_host.trim() !== "127.0.0.1"}
        <span class="hint" style="color: var(--warning-color, #e6a700); font-weight: bold;">Warning: guidebook has no authentication. Serving on a public network is not recommended.</span>
      {/if}
    </div>
    <div class="setting-row">
      <label for="global_default_port">Default Port</label>
      <input id="global_default_port" type="text" bind:value={global_default_port} on:blur={() => saveGlobalSetting("default_port", global_default_port.trim())} autocomplete="off" style="max-width: 6rem" />
    </div>
    <div class="setting-row toggle-row">
      <label>
        <input type="checkbox" bind:checked={global_open_browser_on_startup} on:change={() => saveGlobalSetting("open_browser_on_startup", global_open_browser_on_startup ? "true" : "false")} />
        Open browser on startup (unless <code>--no-browser</code> argument given)
      </label>
    </div>
    <div class="setting-row">
      <label for="global_browser_url">Browser URL Override</label>
      <input id="global_browser_url" type="text" bind:value={global_browser_url_override} on:blur={() => saveGlobalSetting("browser_url_override", global_browser_url_override.trim())} autocomplete="off" placeholder="e.g. https://guidebook.local" style="max-width: 20rem" disabled={!global_open_browser_on_startup} />
      <span class="hint">Custom URL opened in browser on startup (for proxies/TLS). Leave blank for http://127.0.0.1:{global_default_port || "8073"}.</span>
    </div>
  </section>

  <section class="settings-section">
    <h3>Shutdown</h3>
    <div class="setting-row toggle-row">
      <label class="toggle-label">
        <input type="checkbox" bind:checked={disableShutdown} on:change={toggleDisableShutdown} />
        Disable shutdown
      </label>
    </div>
    <div class="setting-row toggle-row">
      <label class="toggle-label">
        <input type="checkbox" bind:checked={autoShutdownOnDisconnect} on:change={() => saveGlobalSetting("auto_shutdown_on_disconnect", autoShutdownOnDisconnect ? "true" : "false")} disabled={disableShutdown} />
        Shutdown automatically when no clients are connected
      </label>
    </div>
    <div class="setting-row">
      <label for="global_shutdown_delay">Shutdown delay (seconds)</label>
      <input id="global_shutdown_delay" type="number" min="5" bind:value={global_auto_shutdown_delay} on:blur={() => { const v = Math.max(5, parseInt(global_auto_shutdown_delay) || 300); global_auto_shutdown_delay = String(v); saveGlobalSetting("auto_shutdown_delay", String(v)); }} autocomplete="off" style="max-width: 5rem" disabled={disableShutdown || !autoShutdownOnDisconnect} />
    </div>
    <p class="hint">Shuts down the server after {global_auto_shutdown_delay} consecutive seconds with no connected clients.</p>
    <div class="setting-row toggle-row">
      <label class="toggle-label">
        <input type="checkbox" bind:checked={shutdownInMenu} on:change={() => { saveGlobalSetting("shutdown_in_menu", shutdownInMenu ? "true" : "false"); }} disabled={disableShutdown} />
        Add Shutdown action to the main menu
      </label>
    </div>
  </section>
  </div></div>
  {/if}
</div>

<style>
  .settings {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 5rem);
    overflow: hidden;
  }
  .settings > h2,
  .settings > .setup-hint,
  .settings > .tab-bar {
    max-width: 1100px;
    width: 100%;
    margin-left: auto;
    margin-right: auto;
    box-sizing: border-box;
  }

  .tab-bar {
    display: flex;
    gap: 0;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border);
  }

  .tab {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text);
    padding: 0.5rem 0.5rem;
    font-size: 0.8rem;
    font-weight: bold;
    cursor: pointer;
    font-family: inherit;
  }

  .tab:hover {
    background: var(--accent);
    color: var(--accent-text);
    font-weight: bold;
  }

  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }

  .tab.active:hover {
    background: var(--accent);
    color: var(--accent-text);
  }

  .tab-scroll {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }
  .tab-content {
    display: flex;
    flex-wrap: wrap;
    gap: 0 1rem;
    max-width: 1100px;
    width: 100%;
    margin: 0 auto;
    box-sizing: border-box;
  }

  /* Single-column fallback (no masonry columns created) */
  .tab-content > :global(.settings-section) {
    width: 100%;
  }

  :global(.masonry-col) {
    flex: 1;
    min-width: 0;
  }

  h2 {
    color: var(--accent);
    font-size: 1.2rem;
    margin: 0 0 1rem 0;
  }

  .autosave-hint {
    font-size: 0.7rem;
    font-weight: normal;
    color: var(--text-muted);
  }

  .settings-section {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
  }
  .settings-section:global(.highlight-flash) {
    animation: highlight-pulse 1.5s ease-out;
  }
  @keyframes highlight-pulse {
    0%, 10% { border-color: var(--accent); box-shadow: 0 0 8px color-mix(in srgb, var(--accent) 40%, transparent); }
    30% { border-color: var(--border); box-shadow: none; }
    50%, 60% { border-color: var(--accent); box-shadow: 0 0 8px color-mix(in srgb, var(--accent) 40%, transparent); }
    100% { border-color: var(--border); box-shadow: none; }
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

  label {
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  input:not([type="range"]):not([type="checkbox"]), select {
    background: var(--bg-input);
    border: 1px solid var(--border-input);
    color: var(--text);
    padding: 0.4rem 0.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    border-radius: 3px;
    width: 100%;
    max-width: 20rem;
  }

  input:not([type="range"]):not([type="checkbox"]):focus, select:focus {
    outline: none;
    border-color: var(--accent);
  }

  input[type="range"] {
    width: 100%;
    max-width: 20rem;
    accent-color: var(--accent);
  }

  input:disabled, select:disabled {
    opacity: 0.4;
  }

  input[type="checkbox"] {
    accent-color: var(--accent);
  }

  .color-pickers {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }

  @media (max-width: 360px) {
    .color-pickers {
      grid-template-columns: 1fr;
    }
  }

  .color-picker-group {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.4rem;
  }

  .color-picker-group label {
    font-size: 0.8rem;
    color: var(--text-muted);
    font-weight: bold;
  }

  .color-picker-group hex-color-picker {
    width: 120px;
    height: 120px;
    touch-action: none;
  }

  .color-hex-input {
    width: 5.5rem !important;
    text-align: center;
    font-size: 0.8rem !important;
  }

  .slider-pair {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .slider-group {
    flex: 1;
    min-width: 10rem;
  }
  .slider-group label {
    display: block;
    font-size: 0.85rem;
    margin-bottom: 0.25rem;
    color: var(--text-muted);
  }
  .slider-value {
    opacity: 0.6;
    font-size: 0.8rem;
  }
  .hue-range {
    -webkit-appearance: none;
    appearance: none;
    height: 6px;
    border-radius: 3px;
    background: linear-gradient(to right, #ff0000, #ffff00, #00ff00, #00ffff, #0000ff, #ff00ff, #ff0000);
    outline: none;
  }
  .hue-range::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--text);
    border: 2px solid var(--bg);
    cursor: pointer;
  }
  .hue-range::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--text);
    border: 2px solid var(--bg);
    cursor: pointer;
  }
  .slider-control {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .slider-control input[type="range"] {
    flex: 1;
    accent-color: var(--accent);
  }
  .theme-select-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .contrast-reset {
    font-family: inherit;
    font-size: 0.8rem;
    padding: 0.2rem 0.6rem;
    background: var(--btn-secondary);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 3px;
    cursor: pointer;
  }
  .contrast-reset:hover:not(:disabled) {
    color: var(--accent-text);
  }
  .contrast-reset:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .theme-mode-switch {
    display: flex;
    gap: 0;
    border: 1px solid var(--border);
    border-radius: 3px;
    overflow: hidden;
  }

  .mode-btn {
    padding: 0.3rem 1rem;
    font-family: inherit;
    font-size: 0.8rem;
    font-weight: bold;
    border: none;
    cursor: pointer;
    background: var(--bg-input);
    color: var(--text-muted);
  }

  .mode-btn.active {
    background: var(--accent);
    color: var(--accent-text);
  }

  .mode-btn:hover:not(.active) {
    background: var(--menu-hover);
  }

  button {
    background: var(--accent);
    color: var(--accent-text);
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

  p.hint {
    font-size: 0.7rem;
    color: var(--text-dim);
    margin: 0;
  }

  .danger-zone {
    border-color: #ff4444;
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
  .warning-btn {
    background: #e67e22;
    color: #fff;
  }
  .warning-btn:hover {
    background: #cf6d17;
  }
  .update-status {
    margin-top: 0.5rem;
    font-size: 0.9rem;
    color: var(--text-muted);
  }
  .update-available {
    color: #2ecc40;
    font-weight: bold;
    text-decoration: none;
  }
  .update-available:hover {
    text-decoration: underline;
  }
  .update-actions {
    margin-top: 0.3rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .update-check-meta {
    margin-top: 0.7rem;
    font-size: 0.8rem;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .check-now-btn {
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    cursor: pointer;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-input, transparent);
    color: var(--text);
    align-self: flex-start;
  }
  .check-now-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .apply-update-btn {
    background: #2ecc40;
    color: var(--accent-text);
    font-weight: bold;
    border-color: #2ecc40;
    margin-left: 0.5rem;
  }
  .apply-update-btn:disabled {
    background: #2ecc40;
    opacity: 0.6;
  }
  .update-error {
    color: #e74c3c;
    font-size: 0.8rem;
    margin-left: 0.5rem;
  }
  .update-custom-repo-warning {
    margin-top: 0.5rem;
    padding: 0.4rem 0.6rem;
    font-size: 0.85rem;
    color: #f39c12;
    border: 1px solid #f39c12;
    border-radius: 4px;
    background: rgba(243, 156, 18, 0.1);
  }
  .update-custom-repo-warning a {
    color: #2ecc40;
  }
  .sha-link {
    font-family: monospace;
    color: var(--accent);
  }
</style>
