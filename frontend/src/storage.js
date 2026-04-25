/** Per-logbook localStorage wrapper. */

let _logbook = "guidebook";

export function setLogbook(name) {
  _logbook = name || "guidebook";
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

/** One-time migration: copy un-prefixed keys to "guidebook:" prefix. */
const KNOWN_KEYS = [
  "dualSplit", "desktop_notifications_enabled", "popup_notifications_enabled",
  "guidebook-theme",
];

export function migrateStorage() {
  if (localStorage.getItem("guidebook-storage-migrated")) return;
  for (const k of KNOWN_KEYS) {
    const val = localStorage.getItem(k);
    if (val !== null && localStorage.getItem(`guidebook:${k}`) === null) {
      localStorage.setItem(`guidebook:${k}`, val);
    }
  }
  localStorage.setItem("guidebook-storage-migrated", "1");
}
