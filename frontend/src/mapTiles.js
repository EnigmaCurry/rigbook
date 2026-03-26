const LIGHT_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const LIGHT_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>';

const DARK_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const DARK_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>';

/** Fetch map tile settings and resolve to { url, attribution, maxZoom }. */
export async function getMapTileConfig() {
  let mapTheme = "default";
  let customUrl = "";
  try {
    const [themeRes, urlRes] = await Promise.all([
      fetch("/api/settings/map_theme"),
      fetch("/api/settings/map_custom_url"),
    ]);
    if (themeRes.ok) {
      const d = await themeRes.json();
      if (d.value) mapTheme = d.value;
    }
    if (urlRes.ok) {
      const d = await urlRes.json();
      if (d.value) customUrl = d.value;
    }
  } catch {}

  if (mapTheme === "custom" && customUrl) {
    // Normalize uppercase {Z}/{X}/{Y} to lowercase for Leaflet
    const url = customUrl.replace(/\{Z\}/g, "{z}").replace(/\{X\}/g, "{x}").replace(/\{Y\}/g, "{y}");
    return { url, attribution: "", maxZoom: 19 };
  }

  let useDark;
  if (mapTheme === "dark") {
    useDark = true;
  } else if (mapTheme === "light") {
    useDark = false;
  } else {
    // default: follow app theme
    const stored = localStorage.getItem("rigbook-theme");
    const appTheme = stored || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    useDark = appTheme === "dark";
  }

  return useDark
    ? { url: DARK_URL, attribution: DARK_ATTR, maxZoom: 19 }
    : { url: LIGHT_URL, attribution: LIGHT_ATTR, maxZoom: 18 };
}
