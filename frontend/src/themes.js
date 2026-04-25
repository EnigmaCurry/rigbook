/** Theme definitions for Guidebook.
 *  Each theme maps CSS custom-property names to values.
 *  `base` is "dark" or "light" — used for map-tile selection and fallback logic.
 */

export const THEMES = {
  dark: {
    label: "Dark",
    base: "dark",
    vars: {
      "--bg": "#24252b",
      "--bg-card": "#2a2d3e",
      "--bg-input": "#5a5c6a",
      "--bg-deep": "#11111b",
      "--border": "#5a5c6a",
      "--border-input": "#6e7080",
      "--text": "#eaeaea",
      "--text-muted": "#b0b2be",
      "--text-dim": "#8a8c98",
      "--text-dimmer": "#6e7080",
      "--accent": "#00ff88",
      "--accent-hover": "#00cc6a",
      "--accent-highlight": "#ffcc00",
      "--accent-secondary": "#00ccff",
      "--secondary-bg": "#111218",
      "--secondary-border": "#555",
      "--secondary-text": "#00ccff",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#ff6b6b",
      "--btn-secondary": "#6e7080",
      "--btn-secondary-hover": "#5a5c6a",
      "--row-hover": "#44465a",
      "--row-editing": "#3a5a3a",
      "--bar-color": "#eaeaea",
      "--menu-bg": "#2e303a",
      "--menu-hover": "#3e404a",
    },
  },
  light: {
    label: "Light",
    base: "light",
    vars: {
      "--bg": "#d8d8f8",
      "--bg-card": "#c8c8ee",
      "--bg-input": "#e8e8ff",
      "--bg-deep": "#c0c0e4",
      "--border": "#a0a0cc",
      "--border-input": "#9090bb",
      "--text": "#1a1a3e",
      "--text-muted": "#3a3a66",
      "--text-dim": "#5a5a88",
      "--text-dimmer": "#7a7aaa",
      "--accent": "#00884d",
      "--accent-hover": "#006a3d",
      "--accent-highlight": "#b8860b",
      "--accent-secondary": "#2a2040",
      "--secondary-bg": "#0c1e88",
      "--secondary-border": "#0c1e88",
      "--secondary-text": "#d8d8f8",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#9898bb",
      "--btn-secondary-hover": "#8888aa",
      "--row-hover": "#c0c0e0",
      "--row-editing": "#b0d8b0",
      "--bar-color": "#1a1a3e",
      "--menu-bg": "#c8c8ee",
      "--menu-hover": "#b8b8dd",
    },
  },
  amber: {
    label: "Amber CRT",
    base: "dark",
    vars: {
      "--bg": "#1a1206",
      "--bg-card": "#231a0a",
      "--bg-input": "#3a2e18",
      "--bg-deep": "#110c04",
      "--border": "#4a3a1e",
      "--border-input": "#5a4828",
      "--text": "#ffbf40",
      "--text-muted": "#cc9933",
      "--text-dim": "#997722",
      "--text-dimmer": "#775a18",
      "--accent": "#ffcc00",
      "--accent-hover": "#e6b800",
      "--accent-highlight": "#ff9900",
      "--accent-secondary": "#ffdd55",
      "--secondary-bg": "#110c04",
      "--secondary-border": "#4a3a1e",
      "--secondary-text": "#ffdd55",
      "--accent-delete": "#cc5500",
      "--accent-delete-hover": "#aa4400",
      "--accent-error": "#ff6633",
      "--btn-secondary": "#5a4828",
      "--btn-secondary-hover": "#4a3a1e",
      "--row-hover": "#2e2210",
      "--row-editing": "#3a3010",
      "--bar-color": "#ffbf40",
      "--menu-bg": "#231a0a",
      "--menu-hover": "#2e2210",
    },
  },
  "field-radio": {
    label: "Field Radio",
    base: "dark",
    vars: {
      "--bg": "#1a2018",
      "--bg-card": "#222e20",
      "--bg-input": "#3a4a38",
      "--bg-deep": "#111a10",
      "--border": "#4a5a44",
      "--border-input": "#556650",
      "--text": "#c8d8b0",
      "--text-muted": "#9aaa82",
      "--text-dim": "#788868",
      "--text-dimmer": "#5a6a4e",
      "--accent": "#88cc44",
      "--accent-hover": "#6eaa33",
      "--accent-highlight": "#ddcc55",
      "--accent-secondary": "#aade66",
      "--secondary-bg": "#111a10",
      "--secondary-border": "#4a5a44",
      "--secondary-text": "#aade66",
      "--accent-delete": "#bb4433",
      "--accent-delete-hover": "#993322",
      "--accent-error": "#dd5544",
      "--btn-secondary": "#556650",
      "--btn-secondary-hover": "#4a5a44",
      "--row-hover": "#2a3828",
      "--row-editing": "#334430",
      "--bar-color": "#c8d8b0",
      "--menu-bg": "#222e20",
      "--menu-hover": "#2a3828",
    },
  },
  nixie: {
    label: "Nixie Tube",
    base: "dark",
    vars: {
      "--bg": "#0f0a08",
      "--bg-card": "#1a1210",
      "--bg-input": "#2e2220",
      "--bg-deep": "#080504",
      "--border": "#3a2a24",
      "--border-input": "#4a3830",
      "--text": "#ff8855",
      "--text-muted": "#cc6640",
      "--text-dim": "#994d30",
      "--text-dimmer": "#773a24",
      "--accent": "#ff6633",
      "--accent-hover": "#e65528",
      "--accent-highlight": "#ffaa44",
      "--accent-secondary": "#ff7744",
      "--secondary-bg": "#080504",
      "--secondary-border": "#3a2a24",
      "--secondary-text": "#ff7744",
      "--accent-delete": "#cc2200",
      "--accent-delete-hover": "#aa1a00",
      "--accent-error": "#ff4422",
      "--btn-secondary": "#4a3830",
      "--btn-secondary-hover": "#3a2a24",
      "--row-hover": "#221816",
      "--row-editing": "#2e2018",
      "--bar-color": "#ff8855",
      "--menu-bg": "#1a1210",
      "--menu-hover": "#221816",
    },
  },
  "solarized-dark": {
    label: "Solarized Dark",
    base: "dark",
    vars: {
      "--bg": "#002b36",
      "--bg-card": "#073642",
      "--bg-input": "#1a4a55",
      "--bg-deep": "#001e26",
      "--border": "#2a6070",
      "--border-input": "#3a7080",
      "--text": "#839496",
      "--text-muted": "#657b83",
      "--text-dim": "#586e75",
      "--text-dimmer": "#4a6068",
      "--accent": "#2aa198",
      "--accent-hover": "#22887f",
      "--accent-highlight": "#b58900",
      "--accent-secondary": "#268bd2",
      "--secondary-bg": "#001e26",
      "--secondary-border": "#2a6070",
      "--secondary-text": "#268bd2",
      "--accent-delete": "#dc322f",
      "--accent-delete-hover": "#c02020",
      "--accent-error": "#dc322f",
      "--btn-secondary": "#3a7080",
      "--btn-secondary-hover": "#2a6070",
      "--row-hover": "#0a404c",
      "--row-editing": "#0a3a30",
      "--bar-color": "#839496",
      "--menu-bg": "#073642",
      "--menu-hover": "#0a404c",
    },
  },
  "boat-anchor": {
    label: "Boat Anchor",
    base: "dark",
    vars: {
      "--bg": "#1e1008",
      "--bg-card": "#2a1810",
      "--bg-input": "#3e2a1e",
      "--bg-deep": "#140a04",
      "--border": "#5a3e2a",
      "--border-input": "#6a4e38",
      "--text": "#e8c89a",
      "--text-muted": "#c4a070",
      "--text-dim": "#9a7a52",
      "--text-dimmer": "#7a5e3e",
      "--accent": "#f0a830",
      "--accent-hover": "#d89420",
      "--accent-highlight": "#ffe088",
      "--accent-secondary": "#f0c060",
      "--secondary-bg": "#140a04",
      "--secondary-border": "#5a3e2a",
      "--secondary-text": "#f0c060",
      "--accent-delete": "#cc4422",
      "--accent-delete-hover": "#aa3318",
      "--accent-error": "#e85533",
      "--btn-secondary": "#6a4e38",
      "--btn-secondary-hover": "#5a3e2a",
      "--row-hover": "#342010",
      "--row-editing": "#3a2e18",
      "--bar-color": "#e8c89a",
      "--menu-bg": "#2a1810",
      "--menu-hover": "#342010",
    },
  },
  "qsl-card": {
    label: "QSL Card",
    base: "light",
    vars: {
      "--bg": "#ede0c0",
      "--bg-card": "#e2d4aa",
      "--bg-input": "#f5ecd0",
      "--bg-deep": "#d8c898",
      "--border": "#c0a878",
      "--border-input": "#b09868",
      "--text": "#2a1a08",
      "--text-muted": "#4a3420",
      "--text-dim": "#6a5040",
      "--text-dimmer": "#8a7060",
      "--accent": "#cc2233",
      "--accent-hover": "#aa1a28",
      "--accent-highlight": "#1a3a88",
      "--accent-secondary": "#2a1a08",
      "--secondary-bg": "#2a1a08",
      "--secondary-border": "#4a3420",
      "--secondary-text": "#ede0c0",
      "--accent-delete": "#cc2233",
      "--accent-delete-hover": "#aa1a28",
      "--accent-error": "#cc2233",
      "--btn-secondary": "#b09868",
      "--btn-secondary-hover": "#a08858",
      "--row-hover": "#d8c8a0",
      "--row-editing": "#c8d8a0",
      "--bar-color": "#2a1a08",
      "--menu-bg": "#e2d4aa",
      "--menu-hover": "#d8c8a0",
    },
  },
  moonbounce: {
    label: "Moonbounce",
    base: "dark",
    vars: {
      "--bg": "#0a0e18",
      "--bg-card": "#121828",
      "--bg-input": "#1e2a40",
      "--bg-deep": "#060a12",
      "--border": "#2a3650",
      "--border-input": "#384868",
      "--text": "#c0c8e0",
      "--text-muted": "#8890aa",
      "--text-dim": "#667088",
      "--text-dimmer": "#4a5268",
      "--accent": "#e8e8f0",
      "--accent-hover": "#c8c8d8",
      "--accent-highlight": "#a0b8e8",
      "--accent-secondary": "#8899cc",
      "--secondary-bg": "#060a12",
      "--secondary-border": "#2a3650",
      "--secondary-text": "#8899cc",
      "--accent-delete": "#cc4455",
      "--accent-delete-hover": "#aa3344",
      "--accent-error": "#dd5566",
      "--btn-secondary": "#384868",
      "--btn-secondary-hover": "#2a3650",
      "--row-hover": "#1a2438",
      "--row-editing": "#1a2e30",
      "--bar-color": "#c0c8e0",
      "--menu-bg": "#121828",
      "--menu-hover": "#1a2438",
    },
  },
  sunspot: {
    label: "Sunspot",
    base: "dark",
    vars: {
      "--bg": "#1a1818",
      "--bg-card": "#242020",
      "--bg-input": "#3a3434",
      "--bg-deep": "#111010",
      "--border": "#4a4242",
      "--border-input": "#5a5050",
      "--text": "#d4b070",
      "--text-muted": "#b08e50",
      "--text-dim": "#8a6e3a",
      "--text-dimmer": "#6a5428",
      "--accent": "#f0a820",
      "--accent-hover": "#d89418",
      "--accent-highlight": "#ffcc44",
      "--accent-secondary": "#e8b830",
      "--secondary-bg": "#111010",
      "--secondary-border": "#4a4242",
      "--secondary-text": "#e8b830",
      "--accent-delete": "#cc3322",
      "--accent-delete-hover": "#aa2818",
      "--accent-error": "#e84422",
      "--btn-secondary": "#5a5050",
      "--btn-secondary-hover": "#4a4242",
      "--row-hover": "#2e2828",
      "--row-editing": "#343020",
      "--bar-color": "#d4b070",
      "--menu-bg": "#242020",
      "--menu-hover": "#2e2828",
    },
  },
  ares: {
    label: "EMCOMM",
    base: "dark",
    vars: {
      "--bg": "#141418",
      "--bg-card": "#1e1e24",
      "--bg-input": "#2e2e38",
      "--bg-deep": "#0a0a0e",
      "--border": "#3e3e4a",
      "--border-input": "#4e4e5a",
      "--text": "#f0f0f0",
      "--text-muted": "#c0c0c8",
      "--text-dim": "#9090a0",
      "--text-dimmer": "#686878",
      "--accent": "#ff8800",
      "--accent-hover": "#e07800",
      "--accent-highlight": "#ffdd00",
      "--accent-secondary": "#ffaa22",
      "--secondary-bg": "#0a0a0e",
      "--secondary-border": "#3e3e4a",
      "--secondary-text": "#ffaa22",
      "--accent-delete": "#dd2222",
      "--accent-delete-hover": "#bb1818",
      "--accent-error": "#ff3333",
      "--btn-secondary": "#4e4e5a",
      "--btn-secondary-hover": "#3e3e4a",
      "--row-hover": "#28282e",
      "--row-editing": "#2e3420",
      "--bar-color": "#f0f0f0",
      "--menu-bg": "#1e1e24",
      "--menu-hover": "#28282e",
    },
  },
  contest: {
    label: "Contest Mode",
    base: "dark",
    vars: {
      "--bg": "#080808",
      "--bg-card": "#111111",
      "--bg-input": "#1e1e1e",
      "--bg-deep": "#040404",
      "--border": "#2a2a2a",
      "--border-input": "#3a3a3a",
      "--text": "#f0f0f0",
      "--text-muted": "#bbbbbb",
      "--text-dim": "#888888",
      "--text-dimmer": "#555555",
      "--accent": "#00ee55",
      "--accent-hover": "#00cc44",
      "--accent-highlight": "#ffffff",
      "--accent-secondary": "#00dd44",
      "--secondary-bg": "#040404",
      "--secondary-border": "#2a2a2a",
      "--secondary-text": "#00dd44",
      "--accent-delete": "#ee2222",
      "--accent-delete-hover": "#cc1818",
      "--accent-error": "#ff3333",
      "--btn-secondary": "#3a3a3a",
      "--btn-secondary-hover": "#2a2a2a",
      "--row-hover": "#181818",
      "--row-editing": "#0e1e0e",
      "--bar-color": "#f0f0f0",
      "--menu-bg": "#111111",
      "--menu-hover": "#181818",
    },
  },
  "field-day": {
    label: "Field Day",
    base: "light",
    vars: {
      "--bg": "#c8e0c0",
      "--bg-card": "#b8d4ae",
      "--bg-input": "#d8ecd0",
      "--bg-deep": "#a8c8a0",
      "--border": "#88aa78",
      "--border-input": "#789a68",
      "--text": "#0e2810",
      "--text-muted": "#2a4828",
      "--text-dim": "#4a6848",
      "--text-dimmer": "#6a8868",
      "--accent": "#2e7b30",
      "--accent-hover": "#1e6020",
      "--accent-highlight": "#1a5c3c",
      "--accent-secondary": "#0e2810",
      "--secondary-bg": "#0e2810",
      "--secondary-border": "#2a4828",
      "--secondary-text": "#c8e0c0",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#789a68",
      "--btn-secondary-hover": "#689058",
      "--row-hover": "#b0d0a8",
      "--row-editing": "#a0c8a0",
      "--bar-color": "#0e2810",
      "--menu-bg": "#b8d4ae",
      "--menu-hover": "#a8c8a0",
    },
  },
  logbook: {
    label: "Logbook",
    base: "light",
    vars: {
      "--bg": "#d8d0c0",
      "--bg-card": "#ccc4b0",
      "--bg-input": "#e4dcc8",
      "--bg-deep": "#c0b8a4",
      "--border": "#a09880",
      "--border-input": "#908870",
      "--text": "#18140a",
      "--text-muted": "#3a3420",
      "--text-dim": "#5a5440",
      "--text-dimmer": "#7a7460",
      "--accent": "#2a5caa",
      "--accent-hover": "#204a90",
      "--accent-highlight": "#1a3a78",
      "--accent-secondary": "#18140a",
      "--secondary-bg": "#18140a",
      "--secondary-border": "#3a3420",
      "--secondary-text": "#d8d0c0",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#908870",
      "--btn-secondary-hover": "#807860",
      "--row-hover": "#c4bca8",
      "--row-editing": "#b8c8a8",
      "--bar-color": "#18140a",
      "--menu-bg": "#ccc4b0",
      "--menu-hover": "#c0b8a0",
    },
  },
  "shack-window": {
    label: "Shack Window",
    base: "light",
    vars: {
      "--bg": "#e0c8a8",
      "--bg-card": "#d4b890",
      "--bg-input": "#ecd8b8",
      "--bg-deep": "#c8b088",
      "--border": "#a89068",
      "--border-input": "#988058",
      "--text": "#2e1808",
      "--text-muted": "#4e3418",
      "--text-dim": "#6e5038",
      "--text-dimmer": "#8e7058",
      "--accent": "#b06828",
      "--accent-hover": "#985820",
      "--accent-highlight": "#6e4420",
      "--accent-secondary": "#2e1808",
      "--secondary-bg": "#2e1808",
      "--secondary-border": "#4e3418",
      "--secondary-text": "#e0c8a8",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#988058",
      "--btn-secondary-hover": "#887048",
      "--row-hover": "#c8b088",
      "--row-editing": "#c0c088",
      "--bar-color": "#2e1808",
      "--menu-bg": "#d4b890",
      "--menu-hover": "#c8b088",
    },
  },
  "dx-pileup": {
    label: "DX Pileup",
    base: "light",
    vars: {
      "--bg": "#dcc8e8",
      "--bg-card": "#d0b8e0",
      "--bg-input": "#e8d8f0",
      "--bg-deep": "#c4aad8",
      "--border": "#a888c0",
      "--border-input": "#9878b0",
      "--text": "#1a0828",
      "--text-muted": "#3a2050",
      "--text-dim": "#5a4070",
      "--text-dimmer": "#7a6090",
      "--accent": "#cc2277",
      "--accent-hover": "#aa1a66",
      "--accent-highlight": "#881a88",
      "--accent-secondary": "#1a0828",
      "--secondary-bg": "#1a0828",
      "--secondary-border": "#3a2050",
      "--secondary-text": "#dcc8e8",
      "--accent-delete": "#cc2233",
      "--accent-delete-hover": "#aa1a28",
      "--accent-error": "#cc2233",
      "--btn-secondary": "#9878b0",
      "--btn-secondary-hover": "#8868a0",
      "--row-hover": "#c8b0d8",
      "--row-editing": "#c0c8c0",
      "--bar-color": "#1a0828",
      "--menu-bg": "#d0b8e0",
      "--menu-hover": "#c4aad8",
    },
  },
  elmer: {
    label: "Elmer",
    base: "light",
    vars: {
      "--bg": "#b8d8d4",
      "--bg-card": "#a8ccc8",
      "--bg-input": "#c8e4e0",
      "--bg-deep": "#98c0bc",
      "--border": "#78a0a0",
      "--border-input": "#689090",
      "--text": "#082420",
      "--text-muted": "#204440",
      "--text-dim": "#406460",
      "--text-dimmer": "#608480",
      "--accent": "#2a7a6a",
      "--accent-hover": "#206058",
      "--accent-highlight": "#1a5050",
      "--accent-secondary": "#082420",
      "--secondary-bg": "#082420",
      "--secondary-border": "#204440",
      "--secondary-text": "#b8d8d4",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#689090",
      "--btn-secondary-hover": "#588080",
      "--row-hover": "#a0c4c0",
      "--row-editing": "#98c0a8",
      "--bar-color": "#082420",
      "--menu-bg": "#a8ccc8",
      "--menu-hover": "#98c0bc",
    },
  },
  ragchew: {
    label: "Ragchew",
    base: "light",
    vars: {
      "--bg": "#e8c0a8",
      "--bg-card": "#dcb098",
      "--bg-input": "#f0d0b8",
      "--bg-deep": "#d0a488",
      "--border": "#b08868",
      "--border-input": "#a07858",
      "--text": "#301008",
      "--text-muted": "#502818",
      "--text-dim": "#704838",
      "--text-dimmer": "#906858",
      "--accent": "#cc5530",
      "--accent-hover": "#b04828",
      "--accent-highlight": "#884030",
      "--accent-secondary": "#301008",
      "--secondary-bg": "#301008",
      "--secondary-border": "#502818",
      "--secondary-text": "#e8c0a8",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#a07858",
      "--btn-secondary-hover": "#906848",
      "--row-hover": "#d0a888",
      "--row-editing": "#c8b888",
      "--bar-color": "#301008",
      "--menu-bg": "#dcb098",
      "--menu-hover": "#d0a488",
    },
  },
  qrp: {
    label: "QRP",
    base: "light",
    vars: {
      "--bg": "#c0d0e8",
      "--bg-card": "#b0c0dc",
      "--bg-input": "#d0ddf0",
      "--bg-deep": "#a0b0d0",
      "--border": "#8090b8",
      "--border-input": "#7080a8",
      "--text": "#081028",
      "--text-muted": "#202848",
      "--text-dim": "#404868",
      "--text-dimmer": "#606888",
      "--accent": "#3468b0",
      "--accent-hover": "#2858a0",
      "--accent-highlight": "#2e4880",
      "--accent-secondary": "#081028",
      "--secondary-bg": "#081028",
      "--secondary-border": "#202848",
      "--secondary-text": "#c0d0e8",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#7080a8",
      "--btn-secondary-hover": "#607098",
      "--row-hover": "#a8b8d4",
      "--row-editing": "#a8c0b8",
      "--bar-color": "#081028",
      "--menu-bg": "#b0c0dc",
      "--menu-hover": "#a0b0d0",
    },
  },
  "solarized-light": {
    label: "Solarized Light",
    base: "light",
    vars: {
      "--bg": "#eee8d5",
      "--bg-card": "#e0d8c0",
      "--bg-input": "#f5eed8",
      "--bg-deep": "#d4ccb0",
      "--border": "#b8b098",
      "--border-input": "#a8a088",
      "--text": "#586e75",
      "--text-muted": "#657b83",
      "--text-dim": "#839496",
      "--text-dimmer": "#93a1a1",
      "--accent": "#2aa198",
      "--accent-hover": "#22887f",
      "--accent-highlight": "#b58900",
      "--accent-secondary": "#073642",
      "--secondary-bg": "#073642",
      "--secondary-border": "#073642",
      "--secondary-text": "#eee8d5",
      "--accent-delete": "#dc322f",
      "--accent-delete-hover": "#c02020",
      "--accent-error": "#dc322f",
      "--btn-secondary": "#a8a088",
      "--btn-secondary-hover": "#989078",
      "--row-hover": "#d4ccb0",
      "--row-editing": "#c8d8b0",
      "--bar-color": "#586e75",
      "--menu-bg": "#e0d8c0",
      "--menu-hover": "#d4ccb0",
    },
  },
};

export const THEME_NAMES = Object.keys(THEMES);

/** Apply a theme's CSS variables to document.documentElement.
 *  contrast: 0–100, 50 = unchanged. brightness: 0–100, 50 = unchanged. hue: 0–360, 0 = unchanged. */
export function applyThemeVars(themeName, contrast = 50, brightness = 50, hue = 0, saturation = 50, gradient = 50, grain = 0, glow = 0, scanlines = 0) {
  const theme = THEMES[themeName] || THEMES.dark;
  const style = document.documentElement.style;
  for (const [prop, val] of Object.entries(theme.vars)) {
    style.setProperty(prop, _adjustColor(val, contrast, brightness, hue, saturation));
  }
  _setAccentText(style);
  _setGradient(style, gradient);
  _setGrain(grain, scanlines);
  _setGlow(style, glow);
  _setScanlines(scanlines);
}

function _setAccentText(style) {
  const accent = style.getPropertyValue("--accent").trim();
  if (/^#[0-9a-fA-F]{6}$/.test(accent)) {
    style.setProperty("--accent-text", luminance(accent) > 0.5 ? "#000000" : "#ffffff");
  }
}

function _setGradient(style, gradient) {
  if (gradient === 50) {
    style.setProperty("--bg-gradient", "var(--bg)");
    return;
  }
  const bg = style.getPropertyValue("--bg").trim();
  if (!/^#[0-9a-fA-F]{6}$/.test(bg)) { style.setProperty("--bg-gradient", bg); return; }
  // intensity: 0 at center (50), up to 0.5 at edges (0 or 100)
  const intensity = Math.abs(gradient - 50) / 50 * 0.5;
  const lighter = mix(bg, "#ffffff", intensity);
  const darker = mix(bg, "#000000", intensity);
  if (gradient > 50) {
    // top lighter, bottom darker
    style.setProperty("--bg-gradient", `linear-gradient(to bottom, ${lighter}, ${darker})`);
  } else {
    // top darker, bottom lighter
    style.setProperty("--bg-gradient", `linear-gradient(to bottom, ${darker}, ${lighter})`);
  }
}

let _grainRaf = null;

function _setGrain(grain, scanlines) {
  let overlay = document.getElementById("guidebook-grain-overlay");
  // Stop any running animation
  if (_grainRaf) { cancelAnimationFrame(_grainRaf); _grainRaf = null; }
  if (grain === 0) {
    if (overlay) overlay.style.display = "none";
    return;
  }
  if (!overlay) {
    // Create SVG noise filter
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", "0");
    svg.setAttribute("height", "0");
    svg.style.position = "absolute";
    svg.innerHTML = `<filter id="guidebook-noise"><feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="4" stitchTiles="stitch" seed="0"/><feColorMatrix type="saturate" values="0"/></filter>`;
    document.body.appendChild(svg);
    // Create overlay div
    overlay = document.createElement("div");
    overlay.id = "guidebook-grain-overlay";
    overlay.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:99999;filter:url(#guidebook-noise);mix-blend-mode:overlay;";
    document.body.appendChild(overlay);
  }
  overlay.style.display = "block";
  overlay.style.opacity = String(grain / 100);
  // Paper mode (scrolls with page) vs static mode (fixed)
  if (scanlines > 0) {
    overlay.style.position = "fixed";
    overlay.style.height = "100%";
  } else {
    overlay.style.position = "absolute";
    overlay.style.height = document.documentElement.scrollHeight + "px";
  }
  // Animate grain when scanlines > 0
  if (scanlines > 0) {
    const turb = document.querySelector("#guidebook-noise feTurbulence");
    if (turb) {
      const fps = 4 + Math.round(scanlines / 45 * 12); // 4–16 fps based on scanlines
      const interval = 1000 / fps;
      let last = 0;
      function tick(now) {
        _grainRaf = requestAnimationFrame(tick);
        if (now - last < interval) return;
        last = now;
        turb.setAttribute("seed", String(Math.random() * 1000 | 0));
      }
      _grainRaf = requestAnimationFrame(tick);
    }
  }
}

function _setGlow(style, glow) {
  if (glow === 0) {
    style.setProperty("--glow-shadow", "none");
    style.setProperty("--glow-shadow-sm", "none");
    style.setProperty("--glow-text-shadow", "none");
    return;
  }
  const accent = style.getPropertyValue("--accent").trim();
  const spread = Math.round(glow / 100 * 20);
  const spreadSm = Math.round(glow / 100 * 6);
  const blur = Math.round(glow / 100 * 12);
  const opacity = Math.round(glow / 100 * 80) / 100;
  const opacitySm = Math.round(glow / 100 * 50) / 100;
  style.setProperty("--glow-shadow", `0 0 ${spread}px color-mix(in srgb, ${accent} ${Math.round(opacity * 100)}%, transparent)`);
  style.setProperty("--glow-shadow-sm", `0 0 ${spreadSm}px color-mix(in srgb, ${accent} ${Math.round(opacitySm * 100)}%, transparent)`);
  style.setProperty("--glow-text-shadow", `0 0 ${blur}px ${accent}`);
}

function _setScanlines(scanlines) {
  let overlay = document.getElementById("guidebook-scanlines-overlay");
  if (scanlines === 0) {
    if (overlay) overlay.style.display = "none";
    return;
  }
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "guidebook-scanlines-overlay";
    overlay.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:99998;";
    document.body.appendChild(overlay);
  }
  overlay.style.display = "block";
  const opacity = (scanlines / 100 * 0.3).toFixed(3);
  overlay.style.background = `repeating-linear-gradient(to bottom, transparent, transparent 2px, rgba(0,0,0,${opacity}) 2px, rgba(0,0,0,${opacity}) 4px)`;
  overlay.style.animation = "none";
}

function _adjustColor(hex, contrast, brightness, hue, saturation) {
  if (contrast === 50 && brightness === 50 && hue === 0 && saturation === 50) return hex;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) return hex;
  let [r, g, b] = hex.replace("#", "").match(/.{2}/g).map(c => parseInt(c, 16));
  // Hue shift and saturation in HSL space
  if (hue !== 0 || saturation !== 50) {
    let [h, s, l] = _rgbToHsl(r, g, b);
    if (hue !== 0) h = (h + hue) % 360;
    if (saturation !== 50) s = Math.min(1, s * (saturation / 50));
    [r, g, b] = _hslToRgb(h, s, l);
  }
  // Contrast: scale around mid-gray
  if (contrast !== 50) {
    const cf = contrast / 50;
    r = 128 + (r - 128) * cf;
    g = 128 + (g - 128) * cf;
    b = 128 + (b - 128) * cf;
  }
  // Brightness: shift toward black (<50) or white (>50)
  if (brightness !== 50) {
    if (brightness < 50) {
      const t = brightness / 50;
      r *= t; g *= t; b *= t;
    } else {
      const t = (brightness - 50) / 50;
      r += (255 - r) * t; g += (255 - g) * t; b += (255 - b) * t;
    }
  }
  const clamp = (c) => Math.max(0, Math.min(255, Math.round(c)));
  return "#" + [r, g, b].map(clamp).map(c => c.toString(16).padStart(2, "0")).join("");
}

function _rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) * 60;
  else if (max === g) h = ((b - r) / d + 2) * 60;
  else h = ((r - g) / d + 4) * 60;
  return [h, s, l];
}

function _hslToRgb(h, s, l) {
  if (s === 0) { const v = Math.round(l * 255); return [v, v, v]; }
  const hueToRgb = (p, q, t) => {
    if (t < 0) t += 1; if (t > 1) t -= 1;
    if (t < 1/6) return p + (q - p) * 6 * t;
    if (t < 1/2) return q;
    if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
    return p;
  };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  return [
    Math.round(hueToRgb(p, q, h / 360 + 1/3) * 255),
    Math.round(hueToRgb(p, q, h / 360) * 255),
    Math.round(hueToRgb(p, q, h / 360 - 1/3) * 255),
  ];
}

/** Resolve a theme name from storage/system-preference, falling back to "dark"/"light". */
export function resolveDefaultTheme() {
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

// --- Custom theme generation from 4 seed colors ---

function hexToRgb(hex) {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function rgbToHex([r, g, b]) {
  return "#" + [r, g, b].map(c => Math.max(0, Math.min(255, Math.round(c))).toString(16).padStart(2, "0")).join("");
}

function mix(c1, c2, t) {
  const a = hexToRgb(c1), b = hexToRgb(c2);
  return rgbToHex(a.map((v, i) => v + (b[i] - v) * t));
}

function lighten(hex, amount) { return mix(hex, "#ffffff", amount); }
function darken(hex, amount) { return mix(hex, "#000000", amount); }

function luminance(hex) {
  const [r, g, b] = hexToRgb(hex).map(c => c / 255);
  return 0.299 * r + 0.587 * g + 0.114 * b;
}

/** Generate a full theme vars object from 4 seed colors. */
export function generateCustomTheme(bg, text, accent, secondary) {
  const isDark = luminance(bg) < 0.5;
  const shift = isDark ? lighten : darken;
  const antiShift = isDark ? darken : lighten;

  return {
    base: isDark ? "dark" : "light",
    vars: {
      "--bg": bg,
      "--bg-card": shift(bg, 0.06),
      "--bg-input": shift(bg, 0.15),
      "--bg-deep": antiShift(bg, 0.08),
      "--border": shift(bg, 0.22),
      "--border-input": shift(bg, 0.30),
      "--text": text,
      "--text-muted": mix(text, bg, 0.25),
      "--text-dim": mix(text, bg, 0.45),
      "--text-dimmer": mix(text, bg, 0.60),
      "--accent": accent,
      "--accent-hover": antiShift(accent, 0.15),
      "--accent-highlight": mix(accent, secondary, 0.5),
      "--accent-secondary": secondary,
      "--secondary-bg": isDark ? antiShift(bg, 0.08) : darken(secondary, 0.6),
      "--secondary-border": isDark ? shift(bg, 0.22) : darken(secondary, 0.6),
      "--secondary-text": isDark ? secondary : lighten(secondary, 0.85),
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": isDark ? "#ff6b6b" : "#cc2222",
      "--btn-secondary": shift(bg, 0.30),
      "--btn-secondary-hover": shift(bg, 0.22),
      "--row-hover": shift(bg, 0.10),
      "--row-editing": mix(shift(bg, 0.10), accent, 0.15),
      "--bar-color": text,
      "--menu-bg": shift(bg, 0.06),
      "--menu-hover": shift(bg, 0.12),
    },
  };
}

/** Apply a custom theme's vars with optional modifiers. */
export function applyCustomThemeVars(bg, text, accent, secondary, contrast = 50, brightness = 50, hue = 0, saturation = 50, gradient = 50, grain = 0, glow = 0, scanlines = 0) {
  const theme = generateCustomTheme(bg, text, accent, secondary);
  const style = document.documentElement.style;
  for (const [prop, val] of Object.entries(theme.vars)) {
    style.setProperty(prop, _adjustColor(val, contrast, brightness, hue, saturation));
  }
  _setAccentText(style);
  _setGradient(style, gradient);
  _setGrain(grain, scanlines);
  _setGlow(style, glow);
  _setScanlines(scanlines);
  return theme;
}
