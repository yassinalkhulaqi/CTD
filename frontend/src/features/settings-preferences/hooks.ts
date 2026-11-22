import { useCallback, useEffect, useMemo, useState } from "react";
import {
  exportConfig,
  getLayout,
  getPreferences,
  getTheme,
  importConfig,
  resetPreferences,
  updateLayout,
  updatePreferences,
} from "./api";
import type {
  LayoutResponse,
  PreferencesResponse,
  SaveState,
  ThemeResponse,
} from "./types";

export interface PreferencesState {
  loading: boolean;
  error: string | null;
  saveState: SaveState;
  userId: string;
  preferences: PreferencesResponse | null;
  theme: ThemeResponse | null;
  layout: LayoutResponse | null;
  draftValues: Record<string, unknown>;
  draftLayout: Partial<LayoutResponse>;
  dirty: boolean;
  setDraftValue: (key: string, value: unknown) => void;
  setDraftLayout: (patch: Partial<LayoutResponse>) => void;
  save: () => Promise<void>;
  reset: () => Promise<void>;
  exportJson: () => Promise<string>;
  importJson: (text: string) => Promise<void>;
  reload: () => Promise<void>;
}

function isDifferent(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) !== JSON.stringify(b);
}

export function usePreferences(userId = "default"): PreferencesState {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>({
    status: "idle",
    message: "",
  });
  const [preferences, setPreferences] = useState<PreferencesResponse | null>(
    null,
  );
  const [theme, setTheme] = useState<ThemeResponse | null>(null);
  const [layout, setLayout] = useState<LayoutResponse | null>(null);
  const [draftValues, setDraftValues] = useState<Record<string, unknown>>({});
  const [draftLayout, setDraftLayout] = useState<Partial<LayoutResponse>>({});

  const applyLoaded = useCallback(
    (p: PreferencesResponse, t: ThemeResponse, l: LayoutResponse) => {
      setPreferences(p);
      setTheme(t);
      setLayout(l);
      setDraftValues(p.values);
      setDraftLayout(l);
    },
    [],
  );

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, t, l] = await Promise.all([
        getPreferences(userId),
        getTheme(),
        getLayout(userId),
      ]);
      applyLoaded(p, t, l);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load preferences");
    } finally {
      setLoading(false);
    }
  }, [applyLoaded, userId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const dirty = useMemo(() => {
    if (!preferences || !layout) return false;
    const valueDirty = Object.keys(draftValues).some((k) =>
      isDifferent(draftValues[k], preferences.values[k]),
    );
    const layoutKeys: (keyof LayoutResponse)[] = [
      "density",
      "sidebar_position",
      "show_activity",
      "timezone",
      "date_format",
    ];
    const layoutDirty = layoutKeys.some((k) =>
      isDifferent(draftLayout[k], layout[k]),
    );
    return valueDirty || layoutDirty;
  }, [draftLayout, draftValues, layout, preferences]);

  const setDraftValue = useCallback((key: string, value: unknown) => {
    setDraftValues((prev) => ({ ...prev, [key]: value }));
    setSaveState({ status: "idle", message: "" });
  }, []);

  const setDraftLayoutPatch = useCallback((patch: Partial<LayoutResponse>) => {
    setDraftLayout((prev) => ({ ...prev, ...patch }));
    setSaveState({ status: "idle", message: "" });
  }, []);

  const save = useCallback(async () => {
    if (!preferences || !layout) return;
    setSaveState({ status: "saving", message: "Saving..." });
    setError(null);
    try {
      const changed: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(draftValues)) {
        if (isDifferent(v, preferences.values[k])) changed[k] = v;
      }
      let nextP = preferences;
      let nextL = layout;
      if (Object.keys(changed).length > 0) {
        nextP = await updatePreferences(userId, changed);
      }
      const layoutPatch: Partial<LayoutResponse> = {};
      for (const key of [
        "density",
        "sidebar_position",
        "show_activity",
        "timezone",
        "date_format",
      ] as const) {
        if (isDifferent(draftLayout[key], layout[key])) {
          (layoutPatch as Record<string, unknown>)[key] = draftLayout[key];
        }
      }
      if (Object.keys(layoutPatch).length > 0) {
        nextL = await updateLayout(userId, layoutPatch);
      }
      const nextT = theme ?? (await getTheme());
      applyLoaded(nextP, nextT, nextL);
      setSaveState({ status: "saved", message: "Saved" });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Save failed";
      setSaveState({ status: "error", message: msg });
      setError(msg);
    }
  }, [
    applyLoaded,
    draftLayout,
    draftValues,
    layout,
    preferences,
    theme,
    userId,
  ]);

  const reset = useCallback(async () => {
    setSaveState({ status: "saving", message: "Resetting..." });
    try {
      const res = await resetPreferences(userId);
      const p = await getPreferences(userId);
      applyLoaded(p, res.theme, res.layout);
      setSaveState({ status: "saved", message: "Reset to defaults" });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Reset failed";
      setSaveState({ status: "error", message: msg });
    }
  }, [applyLoaded, userId]);

  const exportJson = useCallback(async () => {
    const config = await exportConfig(userId);
    return JSON.stringify(config, null, 2);
  }, [userId]);

  const importJson = useCallback(
    async (text: string) => {
      setSaveState({ status: "saving", message: "Importing..." });
      try {
        const parsed = JSON.parse(text) as Record<string, unknown>;
        await importConfig(userId, parsed);
        await reload();
        setSaveState({ status: "saved", message: "Imported" });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Import failed";
        setSaveState({ status: "error", message: msg });
        setError(msg);
      }
    },
    [reload, userId],
  );

  return {
    loading,
    error,
    saveState,
    userId,
    preferences,
    theme,
    layout,
    draftValues,
    draftLayout,
    dirty,
    setDraftValue,
    setDraftLayout: setDraftLayoutPatch,
    save,
    reset,
    exportJson,
    importJson,
    reload,
  };
}
