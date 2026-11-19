import { useEffect, useState } from "react";

/** The theme modes supported by the dashboard. */
export type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "ctfd.theme";

/**
 * Resolve the effective theme for the current system preference.
 *
 * @param theme - The requested theme.
 * @returns The effective `light` or `dark` value.
 */
export function resolveTheme(theme: Theme): "light" | "dark" {
  if (theme !== "system") return theme;
  if (typeof window === "undefined" || !window.matchMedia) return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

/**
 * Read the persisted theme preference.
 *
 * @returns The stored theme or `system` when nothing was stored.
 */
export function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system")
    return stored;
  return "system";
}

/**
 * Apply the theme to the document root.
 *
 * @param theme - The theme to apply.
 */
export function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.dataset.theme = resolveTheme(theme);
  root.style.colorScheme = resolveTheme(theme);
}

/**
 * Manage the dashboard colour scheme.
 *
 * @returns The current theme and a setter that persists the choice.
 */
export function useTheme(): [Theme, (theme: Theme) => void] {
  const [theme, setThemeState] = useState<Theme>(() => readStoredTheme());

  useEffect(() => {
    applyTheme(theme);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, theme);
    }
  }, [theme]);

  useEffect(() => {
    if (
      theme !== "system" ||
      typeof window === "undefined" ||
      !window.matchMedia
    )
      return;
    const query = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => applyTheme("system");
    query.addEventListener("change", listener);
    return () => query.removeEventListener("change", listener);
  }, [theme]);

  return [theme, setThemeState];
}
