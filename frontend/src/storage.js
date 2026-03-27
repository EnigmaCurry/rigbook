/** Per-logbook localStorage wrapper. */

let _logbook = "rigbook";

export function setLogbook(name) {
  _logbook = name || "rigbook";
}

export function getLogbook() {
  return _logbook;
}

function prefixedKey(k) {
  return `${_logbook}:${k}`;
}

export function storageGet(k) {
  return localStorage.getItem(prefixedKey(k));
}

export function storageSet(k, v) {
  localStorage.setItem(prefixedKey(k), v);
}

/** One-time migration: copy un-prefixed keys to "rigbook:" prefix. */
const KNOWN_KEYS = [
  "spotsMapEnabled", "spotsMapHeight", "parksMapEnabled", "parksMapHeight",
  "logSortCol", "logSortAsc", "logColumnOrder", "logColumnWidths",
  "dualSplit", "desktop_notifications_enabled", "popup_notifications_enabled",
  "rigbook-theme",
];

export function migrateStorage() {
  if (localStorage.getItem("rigbook-storage-migrated")) return;
  for (const k of KNOWN_KEYS) {
    const val = localStorage.getItem(k);
    if (val !== null && localStorage.getItem(`rigbook:${k}`) === null) {
      localStorage.setItem(`rigbook:${k}`, val);
    }
  }
  localStorage.setItem("rigbook-storage-migrated", "1");
}
