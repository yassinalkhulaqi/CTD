import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const getPreferences = vi.fn();
const updatePreferences = vi.fn();
const getTheme = vi.fn();
const getLayout = vi.fn();
const updateLayout = vi.fn();
const resetPreferences = vi.fn();
const exportConfig = vi.fn();
const importConfig = vi.fn();

vi.mock("./api", () => ({
  getPreferences: (...args: unknown[]) => getPreferences(...args),
  updatePreferences: (...args: unknown[]) => updatePreferences(...args),
  getTheme: (...args: unknown[]) => getTheme(...args),
  updateTheme: vi.fn(),
  getLayout: (...args: unknown[]) => getLayout(...args),
  updateLayout: (...args: unknown[]) => updateLayout(...args),
  resetPreferences: (...args: unknown[]) => resetPreferences(...args),
  exportConfig: (...args: unknown[]) => exportConfig(...args),
  importConfig: (...args: unknown[]) => importConfig(...args),
}));

import { PreferencesPage } from "./PreferencesPage";

const basePrefs = {
  user_id: "default",
  values: {
    "notifications.email": true,
    "notifications.desktop": false,
    "notifications.digest": "daily",
    "appearance.theme": "system",
    "appearance.accent": "indigo",
    "workspace.autoSaveSeconds": 30,
    "workspace.showHints": true,
  },
  defaults: {
    "notifications.email": true,
    "notifications.desktop": false,
    "notifications.digest": "daily",
    "appearance.theme": "system",
    "appearance.accent": "indigo",
    "workspace.autoSaveSeconds": 30,
    "workspace.showHints": true,
  },
  schema_fields: [
    {
      key: "appearance.theme",
      value_type: "enum",
      default: "system",
      label: "Theme mode",
      description: "Preferred color scheme.",
      choices: ["system", "light", "dark"],
      min_value: null,
      max_value: null,
    },
    {
      key: "appearance.accent",
      value_type: "enum",
      default: "indigo",
      label: "Accent color",
      description: "Primary accent token.",
      choices: ["indigo", "teal"],
      min_value: null,
      max_value: null,
    },
    {
      key: "workspace.autoSaveSeconds",
      value_type: "integer",
      default: 30,
      label: "Autosave interval",
      description: "Seconds between autosaves.",
      choices: [],
      min_value: 5,
      max_value: 300,
    },
    {
      key: "workspace.showHints",
      value_type: "boolean",
      default: true,
      label: "Show hints",
      description: "Display contextual hints in workspace views.",
      choices: [],
      min_value: null,
      max_value: null,
    },
    {
      key: "notifications.email",
      value_type: "boolean",
      default: true,
      label: "Email notifications",
      description: "Receive important updates by email.",
      choices: [],
      min_value: null,
      max_value: null,
    },
    {
      key: "notifications.desktop",
      value_type: "boolean",
      default: false,
      label: "Desktop notifications",
      description: "Show browser desktop notifications.",
      choices: [],
      min_value: null,
      max_value: null,
    },
    {
      key: "notifications.digest",
      value_type: "enum",
      default: "daily",
      label: "Digest frequency",
      description: "How often summary digests are sent.",
      choices: ["off", "daily", "weekly"],
      min_value: null,
      max_value: null,
    },
  ],
};
const baseTheme = {
  tokens: {
    surface: "#FFFFFF",
    surfaceMuted: "#F1F5F9",
    textPrimary: "#0F172A",
    textMuted: "#475569",
    accent: "#4F46E5",
    accentText: "#FFFFFF",
    danger: "#DC2626",
  },
  contrast: [],
  passes: true,
};
const baseLayout = {
  user_id: "default",
  density: "comfortable",
  sidebar_position: "left",
  show_activity: true,
  timezone: "UTC",
  date_format: "YYYY-MM-DD",
  updated_at: "2026-01-01T00:00:00+00:00",
};

describe("PreferencesPage", () => {
  it("renders sections and saves dirty changes", async () => {
    getPreferences.mockResolvedValue(basePrefs);
    getTheme.mockResolvedValue(baseTheme);
    getLayout.mockResolvedValue(baseLayout);
    updatePreferences.mockResolvedValue({
      ...basePrefs,
      values: { ...basePrefs.values, "appearance.theme": "dark" },
    });
    updateLayout.mockResolvedValue(baseLayout);

    render(<PreferencesPage />);
    expect(
      await screen.findByRole("heading", { name: "Preferences" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Appearance")).toBeInTheDocument();
    expect(screen.getByText("Workspace")).toBeInTheDocument();
    expect(screen.getByText("Notifications")).toBeInTheDocument();

    const selects = screen.getAllByRole("combobox");
    await userEvent.selectOptions(selects[0], "dark");
    expect(await screen.findByText("Unsaved changes")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(updatePreferences).toHaveBeenCalled();
  });

  it("resets and exports", async () => {
    getPreferences.mockResolvedValue(basePrefs);
    getTheme.mockResolvedValue(baseTheme);
    getLayout.mockResolvedValue(baseLayout);
    resetPreferences.mockResolvedValue({
      preferences: basePrefs.values,
      layout: baseLayout,
      theme: baseTheme,
    });
    exportConfig.mockResolvedValue({
      version: 1,
      user_id: "default",
      preferences: basePrefs.values,
      theme: baseTheme.tokens,
      layout: baseLayout,
    });
    // mock URL/createElement for export
    const createObjectURL = vi.fn(() => "blob:x");
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = vi.fn();
    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = origCreate(tag);
      if (tag === "a") (el as HTMLAnchorElement).click = click;
      return el;
    });

    render(<PreferencesPage />);
    await screen.findByRole("heading", { name: "Preferences" });
    await userEvent.click(
      screen.getAllByRole("button", { name: "Reset defaults" })[0],
    );
    expect(resetPreferences).toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Export JSON" }));
    expect(exportConfig).toHaveBeenCalled();
    vi.restoreAllMocks();
  });
});
