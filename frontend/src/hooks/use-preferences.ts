"use client";

import { useEffect } from "react";
import { create } from "zustand";

export type FontScale = "100" | "125" | "150" | "200";
export type ThemeMode = "light" | "dark" | "high-contrast";
export type FontFamily = "default" | "dyslexic";

interface PreferencesState {
  fontScale: FontScale;
  theme: ThemeMode;
  fontFamily: FontFamily;
  reducedMotion: boolean;
  setFontScale: (s: FontScale) => void;
  setTheme: (t: ThemeMode) => void;
  setFontFamily: (f: FontFamily) => void;
  setReducedMotion: (r: boolean) => void;
  reset: () => void;
}

const STORAGE_KEY = "palp:preferences:v1";

const DEFAULTS: Pick<PreferencesState, "fontScale" | "theme" | "fontFamily" | "reducedMotion"> = {
  fontScale: "100",
  theme: "light",
  fontFamily: "default",
  reducedMotion: false,
};

function loadFromStorage(): typeof DEFAULTS {
  if (typeof window === "undefined") return DEFAULTS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return DEFAULTS;
  }
}

function persist(state: typeof DEFAULTS) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // localStorage might be disabled (incognito); fail silently.
  }
}

export const usePreferences = create<PreferencesState>((set, get) => ({
  ...DEFAULTS,
  setFontScale: (fontScale) => {
    set({ fontScale });
    persist({ ...get(), fontScale });
  },
  setTheme: (theme) => {
    set({ theme });
    persist({ ...get(), theme });
  },
  setFontFamily: (fontFamily) => {
    set({ fontFamily });
    persist({ ...get(), fontFamily });
  },
  setReducedMotion: (reducedMotion) => {
    set({ reducedMotion });
    persist({ ...get(), reducedMotion });
  },
  reset: () => {
    set(DEFAULTS);
    persist(DEFAULTS);
  },
}));

/**
 * Apply preferences to the document root. Must be called from a client
 * component near the root layout (e.g. <PreferencesProvider />).
 */
export function applyPreferences(prefs: typeof DEFAULTS) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.style.setProperty("--palp-font-scale", `${parseInt(prefs.fontScale, 10) / 100}`);
  root.dataset.theme = prefs.theme;
  root.dataset.fontFamily = prefs.fontFamily;
  if (prefs.reducedMotion) {
    root.dataset.reducedMotion = "true";
  } else {
    delete root.dataset.reducedMotion;
  }
}

/**
 * Mounted at the top of every authenticated layout so theme classes are
 * applied before children render. Also seeds from system prefers-reduced-motion.
 */
export function PreferencesEffect() {
  const { fontScale, theme, fontFamily, reducedMotion, setReducedMotion } = usePreferences();

  useEffect(() => {
    const stored = loadFromStorage();
    usePreferences.setState(stored);

    // Honour the OS-level prefers-reduced-motion if the user hasn't opted in.
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches && !stored.reducedMotion) {
      setReducedMotion(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    applyPreferences({ fontScale, theme, fontFamily, reducedMotion });
  }, [fontScale, theme, fontFamily, reducedMotion]);

  return null;
}
