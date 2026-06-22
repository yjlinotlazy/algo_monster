(() => {
  const STORAGE_KEY = "algo_monster_theme";
  const VANILLA = {
    name: "Vanilla",
    vars: {
      "--bg": "#f6f7f4",
      "--panel": "#ffffff",
      "--panel-alt": "#f0f4f7",
      "--text": "#172026",
      "--muted": "#64717b",
      "--border": "#d8dee2",
      "--accent": "#226f54",
      "--accent-dark": "#18543f",
      "--title-text": "#18543f",
      "--danger": "#b42318",
      "--warning": "#9a6700",
      "--success": "#1f7a4d",
      "--code-bg": "#111820",
      "--code-text": "#edf3f7",
    },
  };

  const themeState = {
    themes: { [VANILLA.name]: VANILLA },
    loaded: false,
    currentName: VANILLA.name,
  };

  const root = document.documentElement;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function hexToRgb(hex) {
    const value = hex.replace("#", "");
    const expanded =
      value.length === 3
        ? value
            .split("")
            .map((ch) => ch + ch)
            .join("")
        : value;
    return {
      r: parseInt(expanded.slice(0, 2), 16),
      g: parseInt(expanded.slice(2, 4), 16),
      b: parseInt(expanded.slice(4, 6), 16),
    };
  }

  function rgbToHex({ r, g, b }) {
    return (
      "#" +
      [r, g, b]
        .map((n) => clamp(Math.round(n), 0, 255).toString(16).padStart(2, "0"))
        .join("")
    );
  }

  function mix(a, b, weight) {
    const left = hexToRgb(a);
    const right = hexToRgb(b);
    return rgbToHex({
      r: left.r * (1 - weight) + right.r * weight,
      g: left.g * (1 - weight) + right.g * weight,
      b: left.b * (1 - weight) + right.b * weight,
    });
  }

  function luminance(hex) {
    const { r, g, b } = hexToRgb(hex);
    const srgb = [r, g, b].map((n) => {
      const channel = n / 255;
      return channel <= 0.03928
        ? channel / 12.92
        : ((channel + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
  }

  function saturation(hex) {
    const { r, g, b } = hexToRgb(hex);
    const max = Math.max(r, g, b) / 255;
    const min = Math.min(r, g, b) / 255;
    const l = (max + min) / 2;
    if (max === min) return 0;
    return l > 0.5 ? (max - min) / (2 - max - min) : (max - min) / (max + min);
  }

  function deriveTheme(colors) {
    const sorted = [...colors].sort((a, b) => luminance(a) - luminance(b));
    const lightestHex = sorted[sorted.length - 1];
    const bgRgb = hexToRgb(lightestHex);

    // Title remains the second darkest color from the palette
    const titleText = sorted.length > 1 ? sorted[1] : sorted[0];
    
    // Normal text is now strictly black for best readability
    const normalText = "#000000";

    const accentSource =
      [...colors]
        .filter((hex) => hex !== lightestHex && hex !== sorted[0])
        .sort((a, b) => saturation(b) - saturation(a) || luminance(a) - luminance(b))[0] ||
      sorted[Math.floor(sorted.length / 2)];

    const panel = mix(lightestHex, "#ffffff", 0.92);
    const panelAlt = mix(lightestHex, accentSource, 0.12);

    // Use original logic for muted/border based on the palette's actual darkest color
    // to ensure borders and secondary text still look part of the theme.
    const muted = mix(sorted[0], lightestHex, 0.58);
    const border = mix(sorted[0], lightestHex, 0.87);

    return {
      "--bg": `rgba(${bgRgb.r}, ${bgRgb.g}, ${bgRgb.b}, 0.5)`,
      "--panel": panel,
      "--panel-alt": panelAlt,
      "--text": normalText,
      "--title-text": titleText,
      "--muted": muted,
      "--border": border,
      "--accent": accentSource,
      "--accent-dark": mix(accentSource, sorted[0], 0.24),
      "--danger": VANILLA.vars["--danger"],
      "--warning": VANILLA.vars["--warning"],
      "--success": VANILLA.vars["--success"],
      "--code-bg": VANILLA.vars["--code-bg"],
      "--code-text": VANILLA.vars["--code-text"],
    };
  }

  function setVars(vars) {
    for (const [key, value] of Object.entries(vars)) {
      root.style.setProperty(key, value);
    }
  }

  function applyTheme(themeName) {
    const theme = themeState.themes[themeName] || VANILLA;
    setVars(theme.vars);
    themeState.currentName = theme.name;
    root.dataset.theme = theme.name.toLowerCase().replaceAll(" ", "-");
  }

  function themeNames() {
    return Object.keys(themeState.themes);
  }

  function getStoredTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY) || VANILLA.name;
    } catch {
      return VANILLA.name;
    }
  }

  function storeTheme(name) {
    try {
      localStorage.setItem(STORAGE_KEY, name);
    } catch {
      // Ignore storage failures in private browsing or restricted contexts.
    }
  }

  function renderThemePicker(selectEl) {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    for (const name of themeNames()) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      selectEl.appendChild(option);
    }
    selectEl.value = getStoredTheme();
    selectEl.addEventListener("change", () => {
      const next = selectEl.value || VANILLA.name;
      storeTheme(next);
      applyTheme(next);
    });
  }

  async function loadPaletteThemes() {
    try {
      const response = await fetch("/color_palette/themes.json", {
        cache: "no-store",
      });
      if (!response.ok) return;
      const raw = await response.json();
      for (const [name, colors] of Object.entries(raw)) {
        if (Array.isArray(colors) && colors.length) {
          themeState.themes[name] = {
            name,
            vars: deriveTheme(colors.filter((hex) => typeof hex === "string")),
          };
        }
      }
      console.log("Loaded themes for selection:", Object.keys(themeState.themes));
      themeState.loaded = true;
    } catch {
      // Leave the vanilla theme in place if the palette file cannot be loaded.
    }
  }

  async function initThemeSystem() {
    applyTheme(getStoredTheme());
    await loadPaletteThemes();
    applyTheme(getStoredTheme());
    renderThemePicker(document.querySelector("[data-theme-picker]"));
  }

  window.AlgoMonsterTheme = {
    initThemeSystem,
    applyTheme,
    storeTheme,
    getStoredTheme,
    renderThemePicker,
    themeState,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initThemeSystem, { once: true });
  } else {
    initThemeSystem();
  }
})();
