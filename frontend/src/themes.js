/** Theme definitions for Rigbook.
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
      "--accent-callsign": "#ffcc00",
      "--accent-vfo": "#00ccff",
      "--vfo-bg": "#111218",
      "--vfo-border": "#555",
      "--vfo-text": "#00ccff",
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
      "--bg": "#e8e8ff",
      "--bg-card": "#f4f4f6",
      "--bg-input": "#ffffff",
      "--bg-deep": "#f0f0f2",
      "--border": "#c8c8d0",
      "--border-input": "#b0b0b8",
      "--text": "#1a1a2e",
      "--text-muted": "#555566",
      "--text-dim": "#777788",
      "--text-dimmer": "#999aaa",
      "--accent": "#00994d",
      "--accent-hover": "#007a3d",
      "--accent-callsign": "#b8860b",
      "--accent-vfo": "#332525",
      "--vfo-bg": "#0c1e88",
      "--vfo-border": "#0c1e88",
      "--vfo-text": "#fbfbfb",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#aaaabc",
      "--btn-secondary-hover": "#9999ab",
      "--row-hover": "#dddde4",
      "--row-editing": "#c8ecc8",
      "--bar-color": "#333344",
      "--menu-bg": "#d8d8e0",
      "--menu-hover": "#c8c8d4",
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
      "--accent-callsign": "#ff9900",
      "--accent-vfo": "#ffdd55",
      "--vfo-bg": "#110c04",
      "--vfo-border": "#4a3a1e",
      "--vfo-text": "#ffdd55",
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
      "--accent-callsign": "#ddcc55",
      "--accent-vfo": "#aade66",
      "--vfo-bg": "#111a10",
      "--vfo-border": "#4a5a44",
      "--vfo-text": "#aade66",
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
      "--accent-callsign": "#ffaa44",
      "--accent-vfo": "#ff7744",
      "--vfo-bg": "#080504",
      "--vfo-border": "#3a2a24",
      "--vfo-text": "#ff7744",
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
      "--accent-callsign": "#b58900",
      "--accent-vfo": "#268bd2",
      "--vfo-bg": "#001e26",
      "--vfo-border": "#2a6070",
      "--vfo-text": "#268bd2",
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
      "--accent-callsign": "#ffe088",
      "--accent-vfo": "#f0c060",
      "--vfo-bg": "#140a04",
      "--vfo-border": "#5a3e2a",
      "--vfo-text": "#f0c060",
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
      "--bg": "#f5f0e0",
      "--bg-card": "#ebe6d4",
      "--bg-input": "#fffdf5",
      "--bg-deep": "#ede8d8",
      "--border": "#c8c0a8",
      "--border-input": "#b8b098",
      "--text": "#1a2244",
      "--text-muted": "#3a4466",
      "--text-dim": "#5a6488",
      "--text-dimmer": "#8088a0",
      "--accent": "#cc2233",
      "--accent-hover": "#aa1a28",
      "--accent-callsign": "#1a3a88",
      "--accent-vfo": "#1a2244",
      "--vfo-bg": "#1a2244",
      "--vfo-border": "#1a2244",
      "--vfo-text": "#f5f0e0",
      "--accent-delete": "#cc2233",
      "--accent-delete-hover": "#aa1a28",
      "--accent-error": "#cc2233",
      "--btn-secondary": "#b8b098",
      "--btn-secondary-hover": "#a8a088",
      "--row-hover": "#e4dfc8",
      "--row-editing": "#d8e8c8",
      "--bar-color": "#1a2244",
      "--menu-bg": "#ebe6d4",
      "--menu-hover": "#e4dfc8",
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
      "--accent-callsign": "#a0b8e8",
      "--accent-vfo": "#8899cc",
      "--vfo-bg": "#060a12",
      "--vfo-border": "#2a3650",
      "--vfo-text": "#8899cc",
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
      "--accent-callsign": "#ffcc44",
      "--accent-vfo": "#e8b830",
      "--vfo-bg": "#111010",
      "--vfo-border": "#4a4242",
      "--vfo-text": "#e8b830",
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
      "--accent-callsign": "#ffdd00",
      "--accent-vfo": "#ffaa22",
      "--vfo-bg": "#0a0a0e",
      "--vfo-border": "#3e3e4a",
      "--vfo-text": "#ffaa22",
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
      "--accent-callsign": "#ffffff",
      "--accent-vfo": "#00dd44",
      "--vfo-bg": "#040404",
      "--vfo-border": "#2a2a2a",
      "--vfo-text": "#00dd44",
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
      "--bg": "#e8f0fa",
      "--bg-card": "#f0f5fc",
      "--bg-input": "#ffffff",
      "--bg-deep": "#dce8f4",
      "--border": "#b8c8e0",
      "--border-input": "#a0b4d0",
      "--text": "#1a2844",
      "--text-muted": "#3a4e6e",
      "--text-dim": "#5a7090",
      "--text-dimmer": "#8098b4",
      "--accent": "#2e8b40",
      "--accent-hover": "#247030",
      "--accent-callsign": "#1a5c9c",
      "--accent-vfo": "#1a2844",
      "--vfo-bg": "#1a2844",
      "--vfo-border": "#1a2844",
      "--vfo-text": "#e8f0fa",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#a0b4d0",
      "--btn-secondary-hover": "#90a4c0",
      "--row-hover": "#d4e4f4",
      "--row-editing": "#c8e8c8",
      "--bar-color": "#1a2844",
      "--menu-bg": "#dce8f4",
      "--menu-hover": "#d0e0f0",
    },
  },
  logbook: {
    label: "Logbook",
    base: "light",
    vars: {
      "--bg": "#f8f5ee",
      "--bg-card": "#f0ece2",
      "--bg-input": "#fffdf8",
      "--bg-deep": "#efe9de",
      "--border": "#d0c8b4",
      "--border-input": "#c0b8a0",
      "--text": "#1e2030",
      "--text-muted": "#404858",
      "--text-dim": "#687080",
      "--text-dimmer": "#909aa8",
      "--accent": "#2a5caa",
      "--accent-hover": "#204a90",
      "--accent-callsign": "#1a3a78",
      "--accent-vfo": "#1e2030",
      "--vfo-bg": "#1e2030",
      "--vfo-border": "#1e2030",
      "--vfo-text": "#f8f5ee",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#c0b8a0",
      "--btn-secondary-hover": "#b0a890",
      "--row-hover": "#e8e2d4",
      "--row-editing": "#d4e4cc",
      "--bar-color": "#1e2030",
      "--menu-bg": "#f0ece2",
      "--menu-hover": "#e8e2d4",
    },
  },
  "shack-window": {
    label: "Shack Window",
    base: "light",
    vars: {
      "--bg": "#f6f0e8",
      "--bg-card": "#eee6da",
      "--bg-input": "#fdfaf5",
      "--bg-deep": "#ece4d8",
      "--border": "#d0c4b0",
      "--border-input": "#c0b49e",
      "--text": "#2e2218",
      "--text-muted": "#5a4e3e",
      "--text-dim": "#7a6e5e",
      "--text-dimmer": "#9a9080",
      "--accent": "#b06830",
      "--accent-hover": "#985828",
      "--accent-callsign": "#6e4420",
      "--accent-vfo": "#2e2218",
      "--vfo-bg": "#2e2218",
      "--vfo-border": "#2e2218",
      "--vfo-text": "#f6f0e8",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#c0b49e",
      "--btn-secondary-hover": "#b0a48e",
      "--row-hover": "#e4dace",
      "--row-editing": "#d4e0c8",
      "--bar-color": "#2e2218",
      "--menu-bg": "#eee6da",
      "--menu-hover": "#e4dace",
    },
  },
  "dx-pileup": {
    label: "DX Pileup",
    base: "light",
    vars: {
      "--bg": "#f4f0f8",
      "--bg-card": "#ece8f2",
      "--bg-input": "#ffffff",
      "--bg-deep": "#e8e4ee",
      "--border": "#c8c0d4",
      "--border-input": "#b8b0c4",
      "--text": "#1a1028",
      "--text-muted": "#44385a",
      "--text-dim": "#686080",
      "--text-dimmer": "#908aa0",
      "--accent": "#cc2277",
      "--accent-hover": "#aa1a66",
      "--accent-callsign": "#881a88",
      "--accent-vfo": "#1a1028",
      "--vfo-bg": "#1a1028",
      "--vfo-border": "#1a1028",
      "--vfo-text": "#f4f0f8",
      "--accent-delete": "#cc2233",
      "--accent-delete-hover": "#aa1a28",
      "--accent-error": "#cc2233",
      "--btn-secondary": "#b8b0c4",
      "--btn-secondary-hover": "#a8a0b4",
      "--row-hover": "#e0daea",
      "--row-editing": "#d8e4d0",
      "--bar-color": "#1a1028",
      "--menu-bg": "#ece8f2",
      "--menu-hover": "#e0daea",
    },
  },
  elmer: {
    label: "Elmer",
    base: "light",
    vars: {
      "--bg": "#e8f0ea",
      "--bg-card": "#f0f6f0",
      "--bg-input": "#fafffe",
      "--bg-deep": "#dfe8e0",
      "--border": "#b4c8b8",
      "--border-input": "#a0b8a4",
      "--text": "#1a2820",
      "--text-muted": "#3a5040",
      "--text-dim": "#5a7862",
      "--text-dimmer": "#809888",
      "--accent": "#2a8a7a",
      "--accent-hover": "#207068",
      "--accent-callsign": "#1a6050",
      "--accent-vfo": "#1a2820",
      "--vfo-bg": "#1a2820",
      "--vfo-border": "#1a2820",
      "--vfo-text": "#e8f0ea",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#a0b8a4",
      "--btn-secondary-hover": "#90a894",
      "--row-hover": "#d8e8da",
      "--row-editing": "#c8e0c8",
      "--bar-color": "#1a2820",
      "--menu-bg": "#dfe8e0",
      "--menu-hover": "#d4e0d4",
    },
  },
  ragchew: {
    label: "Ragchew",
    base: "light",
    vars: {
      "--bg": "#f8ece4",
      "--bg-card": "#f2e4da",
      "--bg-input": "#fffaf6",
      "--bg-deep": "#efe0d4",
      "--border": "#d4c0b0",
      "--border-input": "#c4b0a0",
      "--text": "#2e2020",
      "--text-muted": "#584440",
      "--text-dim": "#7a6660",
      "--text-dimmer": "#a09088",
      "--accent": "#cc6644",
      "--accent-hover": "#b05838",
      "--accent-callsign": "#884830",
      "--accent-vfo": "#2e2020",
      "--vfo-bg": "#2e2020",
      "--vfo-border": "#2e2020",
      "--vfo-text": "#f8ece4",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#c4b0a0",
      "--btn-secondary-hover": "#b4a090",
      "--row-hover": "#edd8cc",
      "--row-editing": "#dce4cc",
      "--bar-color": "#2e2020",
      "--menu-bg": "#f2e4da",
      "--menu-hover": "#edd8cc",
    },
  },
  qrp: {
    label: "QRP",
    base: "light",
    vars: {
      "--bg": "#f4f6f8",
      "--bg-card": "#eef0f4",
      "--bg-input": "#ffffff",
      "--bg-deep": "#e8eaee",
      "--border": "#c8ccd4",
      "--border-input": "#b4b8c4",
      "--text": "#20242e",
      "--text-muted": "#484e5e",
      "--text-dim": "#6e7484",
      "--text-dimmer": "#9498a4",
      "--accent": "#4478bb",
      "--accent-hover": "#3868a8",
      "--accent-callsign": "#2e5890",
      "--accent-vfo": "#20242e",
      "--vfo-bg": "#20242e",
      "--vfo-border": "#20242e",
      "--vfo-text": "#f4f6f8",
      "--accent-delete": "#cc3333",
      "--accent-delete-hover": "#aa2222",
      "--accent-error": "#cc2222",
      "--btn-secondary": "#b4b8c4",
      "--btn-secondary-hover": "#a4a8b4",
      "--row-hover": "#dce0e8",
      "--row-editing": "#d0e0d0",
      "--bar-color": "#20242e",
      "--menu-bg": "#e8eaee",
      "--menu-hover": "#dce0e8",
    },
  },
  "solarized-light": {
    label: "Solarized Light",
    base: "light",
    vars: {
      "--bg": "#fdf6e3",
      "--bg-card": "#eee8d5",
      "--bg-input": "#ffffff",
      "--bg-deep": "#f5eed8",
      "--border": "#d3cbb7",
      "--border-input": "#c0b8a4",
      "--text": "#657b83",
      "--text-muted": "#839496",
      "--text-dim": "#93a1a1",
      "--text-dimmer": "#a8b4b4",
      "--accent": "#2aa198",
      "--accent-hover": "#22887f",
      "--accent-callsign": "#b58900",
      "--accent-vfo": "#073642",
      "--vfo-bg": "#073642",
      "--vfo-border": "#073642",
      "--vfo-text": "#eee8d5",
      "--accent-delete": "#dc322f",
      "--accent-delete-hover": "#c02020",
      "--accent-error": "#dc322f",
      "--btn-secondary": "#c0b8a4",
      "--btn-secondary-hover": "#b0a894",
      "--row-hover": "#e6dfcc",
      "--row-editing": "#d5e8c8",
      "--bar-color": "#586e75",
      "--menu-bg": "#eee8d5",
      "--menu-hover": "#e6dfcc",
    },
  },
};

export const THEME_NAMES = Object.keys(THEMES);

/** Apply a theme's CSS variables to document.documentElement.
 *  contrast: 0–100, 50 = unchanged. brightness: 0–100, 50 = unchanged. hue: 0–360, 0 = unchanged. */
export function applyThemeVars(themeName, contrast = 50, brightness = 50, hue = 0, saturation = 50) {
  const theme = THEMES[themeName] || THEMES.dark;
  const style = document.documentElement.style;
  for (const [prop, val] of Object.entries(theme.vars)) {
    style.setProperty(prop, _adjustColor(val, contrast, brightness, hue, saturation));
  }
  _setAccentText(style);
}

function _setAccentText(style) {
  const accent = style.getPropertyValue("--accent").trim();
  if (/^#[0-9a-fA-F]{6}$/.test(accent)) {
    style.setProperty("--accent-text", luminance(accent) > 0.5 ? "#000000" : "#ffffff");
  }
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
export function generateCustomTheme(bg, text, accent, vfo) {
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
      "--accent-callsign": mix(accent, vfo, 0.5),
      "--accent-vfo": vfo,
      "--vfo-bg": isDark ? antiShift(bg, 0.08) : darken(vfo, 0.6),
      "--vfo-border": isDark ? shift(bg, 0.22) : darken(vfo, 0.6),
      "--vfo-text": isDark ? vfo : lighten(vfo, 0.85),
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
export function applyCustomThemeVars(bg, text, accent, vfo, contrast = 50, brightness = 50, hue = 0, saturation = 50) {
  const theme = generateCustomTheme(bg, text, accent, vfo);
  const style = document.documentElement.style;
  for (const [prop, val] of Object.entries(theme.vars)) {
    style.setProperty(prop, _adjustColor(val, contrast, brightness, hue, saturation));
  }
  _setAccentText(style);
  return theme;
}
