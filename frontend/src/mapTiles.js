/** Normalize uppercase {Z}/{X}/{Y} to lowercase for Leaflet. */
function normUrl(url) {
  return url.replace(/\{Z\}/g, "{z}").replace(/\{X\}/g, "{x}").replace(/\{Y\}/g, "{y}");
}

export const TILE_THEMES = [
  { value: "default",            label: "Default (follows theme)" },
  { value: "usgs-topo",          label: "USGS: Topo" },
  { value: "usgs-imagery",       label: "USGS: Imagery" },
  { value: "esri-topo",          label: "ESRI: Topo" },
  { value: "esri-satellite",     label: "ESRI: Satellite" },
  { value: "natgeo",             label: "National Geographic" },
  { value: "blue-marble",        label: "Blue Marble" },
  { value: "nasa-citylight",     label: "NASA: City Lights" },
  { value: "carto-dark",         label: "Carto: Dark" },
  { value: "carto-light-nolabel",label: "Carto: Light (no labels)" },
  { value: "canvas-dark-grey",   label: "Canvas: World Dark Grey" },
  { value: "custom",             label: "Custom URL" },
];

const THEMES = {
  "default-light": {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
    maxZoom: 18,
  },
  "default-dark": {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}.jpg",
    attribution: '&copy; Esri',
    maxZoom: 16,
  },
  "carto-dark": {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 19,
  },
  "carto-light-nolabel": {
    url: "https://cartodb-basemaps-b.global.ssl.fastly.net/light_nolabels/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 19,
  },
  "usgs-topo": {
    url: "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
    attribution: '&copy; USGS',
    maxZoom: 16,
  },
  "usgs-imagery": {
    url: "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
    attribution: '&copy; USGS',
    maxZoom: 16,
  },
  "esri-topo": {
    url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}.jpg",
    attribution: '&copy; Esri',
    maxZoom: 19,
  },
  "esri-satellite": {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}.jpg",
    attribution: '&copy; Esri',
    maxZoom: 19,
  },
  "natgeo": {
    url: "https://services.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}",
    attribution: '&copy; Esri &copy; National Geographic',
    maxZoom: 16,
  },
  "blue-marble": {
    url: "https://s3.amazonaws.com/com.modestmaps.bluemarble/{z}-r{y}-c{x}.jpg",
    attribution: '&copy; NASA',
    maxZoom: 9,
  },
  "nasa-citylight": {
    url: "https://map1.vis.earthdata.nasa.gov/wmts-webmerc/VIIRS_CityLights_2012/default//GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg",
    attribution: '&copy; NASA',
    maxZoom: 8,
  },
  "canvas-dark-grey": {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}.jpg",
    attribution: '&copy; Esri',
    maxZoom: 16,
  },
};

/** Resolve tile config from theme name and optional custom URL (no fetch). */
export function resolveTileConfig(mapTheme, customUrl) {
  if (mapTheme === "custom" && customUrl) {
    return { url: normUrl(customUrl), attribution: "", maxZoom: 19 };
  }
  if (THEMES[mapTheme]) {
    return THEMES[mapTheme];
  }
  const stored = localStorage.getItem("rigbook-theme");
  const appTheme = stored || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  return appTheme === "dark" ? THEMES["default-dark"] : THEMES["default-light"];
}

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
    return { url: normUrl(customUrl), attribution: "", maxZoom: 19 };
  }

  if (THEMES[mapTheme]) {
    return THEMES[mapTheme];
  }

  // "default" — follow app theme
  const stored = localStorage.getItem("rigbook-theme");
  const appTheme = stored || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  return appTheme === "dark" ? THEMES["default-dark"] : THEMES["default-light"];
}
