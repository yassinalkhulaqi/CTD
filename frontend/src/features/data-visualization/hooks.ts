/** Data loading and local state for the visualisation gallery. */

import { useCallback, useEffect, useMemo, useState } from "react";
import { visualizationsApi } from "./api";
import { CHART_TYPE_OPTIONS, sampleSpec } from "./samples";
import type {
  AggregateResult,
  ChartGeometry,
  ChartSpec,
  ChartSpecCreate,
  ChartSpecUpdate,
  ChartTheme,
  ChartType,
  DataPointInput,
  Palette,
  ViewMode,
} from "./types";

/** The value exposed by the gallery data hook. */
export interface UseVisualizationsResult {
  specs: ChartSpec[];
  palettes: Palette[];
  selected: ChartSpec | null;
  geometry: ChartGeometry | null;
  aggregate: AggregateResult | null;
  loading: boolean;
  analysisLoading: boolean;
  error: string | null;
  viewMode: ViewMode;
  select: (chartId: string) => void;
  setViewMode: (mode: ViewMode) => void;
  refresh: () => Promise<void>;
  create: (payload: ChartSpecCreate) => Promise<ChartSpec>;
  createSamples: () => Promise<void>;
  update: (chartId: string, payload: ChartSpecUpdate) => Promise<void>;
  ingest: (chartId: string, points: DataPointInput[]) => Promise<void>;
}

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Unexpected visualisation error";
}

function currentTheme(): ChartTheme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

/** Track the document theme so SVG palettes can follow light and dark modes. */
export function useInterfaceTheme(): ChartTheme {
  const [theme, setTheme] = useState<ChartTheme>(currentTheme);
  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(currentTheme()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);
  return theme;
}

/** Load chart metadata and keep geometry in sync with the active selection. */
export function useVisualizations(theme: ChartTheme): UseVisualizationsResult {
  const [specs, setSpecs] = useState<ChartSpec[]>([]);
  const [palettes, setPalettes] = useState<Palette[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [geometry, setGeometry] = useState<ChartGeometry | null>(null);
  const [aggregate, setAggregate] = useState<AggregateResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("chart");
  const [revision, setRevision] = useState(0);

  const load = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const [loadedSpecs, loadedPalettes] = await Promise.all([
        visualizationsApi.list(),
        visualizationsApi.palettes(),
      ]);
      setSpecs(loadedSpecs);
      setPalettes(loadedPalettes);
      setSelectedId((current) =>
        loadedSpecs.some((spec) => spec.id === current)
          ? current
          : (loadedSpecs[0]?.id ?? null),
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selectedId) {
      setGeometry(null);
      setAggregate(null);
      return;
    }
    let active = true;
    setAnalysisLoading(true);
    Promise.all([
      visualizationsApi.geometry(selectedId, { theme }),
      visualizationsApi.aggregate(selectedId),
    ])
      .then(([nextGeometry, nextAggregate]) => {
        if (!active) return;
        setGeometry(nextGeometry);
        setAggregate(nextAggregate);
        setError(null);
      })
      .catch((cause: unknown) => {
        if (active) setError(errorMessage(cause));
      })
      .finally(() => {
        if (active) setAnalysisLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedId, theme, revision]);

  const select = useCallback((chartId: string) => setSelectedId(chartId), []);

  const refresh = useCallback(async (): Promise<void> => {
    await load();
    setRevision((value) => value + 1);
  }, [load]);

  const create = useCallback(
    async (payload: ChartSpecCreate): Promise<ChartSpec> => {
      const created = await visualizationsApi.create(payload);
      await load();
      setSelectedId(created.id);
      setRevision((value) => value + 1);
      return created;
    },
    [load],
  );

  const createSamples = useCallback(async (): Promise<void> => {
    const types = CHART_TYPE_OPTIONS.map((option) => option.value as ChartType);
    for (const chartType of types) {
      await create(sampleSpec(chartType));
    }
  }, [create]);

  const update = useCallback(
    async (chartId: string, payload: ChartSpecUpdate): Promise<void> => {
      await visualizationsApi.update(chartId, payload);
      await load();
      setRevision((value) => value + 1);
    },
    [load],
  );

  const ingest = useCallback(
    async (chartId: string, points: DataPointInput[]): Promise<void> => {
      await visualizationsApi.ingest(chartId, { points, replace: true });
      await load();
      setRevision((value) => value + 1);
    },
    [load],
  );

  const selected = useMemo(
    () => specs.find((spec) => spec.id === selectedId) ?? null,
    [specs, selectedId],
  );

  return {
    specs,
    palettes,
    selected,
    geometry,
    aggregate,
    loading,
    analysisLoading,
    error,
    viewMode,
    select,
    setViewMode,
    refresh,
    create,
    createSamples,
    update,
    ingest,
  };
}
