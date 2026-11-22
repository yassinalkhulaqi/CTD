/**
 * Data loading and editor state for the report studio.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { reportsApi } from "./api";
import {
  createSection,
  draftFromTemplate,
  moveSection,
  normaliseSections,
  toggleSection,
  updateSection,
  validateDraft,
} from "./reportModel";
import type {
  ExportJob,
  Report,
  ReportDraft,
  ReportStats,
  ReportTemplate,
  SectionKind,
  SectionPatch,
} from "./types";

/** Data returned by the catalogue loader. */
export interface ReportCatalog {
  templates: ReportTemplate[];
  reports: Report[];
  exports: ExportJob[];
  stats: ReportStats | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

/**
 * Load templates, reports, exports and counters in one coordinated request.
 *
 * @returns The catalogue state and a refresh callback.
 */
export function useReportCatalog(): ReportCatalog {
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [exports, setExports] = useState<ExportJob[]>([]);
  const [stats, setStats] = useState<ReportStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const [nextTemplates, nextReports, nextExports, nextStats] =
        await Promise.all([
          reportsApi.listTemplates({ signal }),
          reportsApi.listReports({}, { signal }),
          reportsApi.listExports(100, { signal }),
          reportsApi.stats({ signal }),
        ]);
      setTemplates(nextTemplates);
      setReports(nextReports);
      setExports(nextExports);
      setStats(nextStats);
    } catch (caught) {
      if (signal?.aborted) return;
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load the report catalogue",
      );
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const refresh = useCallback(async (): Promise<void> => load(), [load]);

  return { templates, reports, exports, stats, loading, error, refresh };
}

/** State and actions of the local report editor. */
export interface ReportDraftState {
  draft: ReportDraft;
  errors: ReturnType<typeof validateDraft>;
  selectTemplate: (template: ReportTemplate) => void;
  loadReport: (report: Report) => void;
  setTitle: (title: string) => void;
  setScope: (scopeId: string) => void;
  addSection: (kind: SectionKind) => void;
  patchSection: (id: string, patch: SectionPatch) => void;
  toggle: (id: string) => void;
  move: (id: string, direction: -1 | 1) => void;
  remove: (id: string) => void;
  reset: () => void;
}

/**
 * Manage the editable draft derived from the selected template.
 *
 * @param templates - Available templates.
 * @returns The draft state and editor actions.
 */
export function useReportDraft(templates: ReportTemplate[]): ReportDraftState {
  const initial = useMemo<ReportDraft>(
    () =>
      templates.length > 0
        ? draftFromTemplate(templates[0])
        : {
            templateId: "",
            title: "",
            scopeId: "team",
            sections: [],
          },
    [templates],
  );
  const [draft, setDraft] = useState<ReportDraft>(initial);

  useEffect(() => {
    setDraft(initial);
  }, [initial]);

  const selectTemplate = useCallback((template: ReportTemplate) => {
    setDraft(draftFromTemplate(template));
  }, []);

  const loadReport = useCallback(
    (report: Report) => {
      const template = templates.find((item) => item.id === report.template_id);
      setDraft({
        templateId: report.template_id,
        title: report.title,
        scopeId: report.scope_id,
        sections: template ? draftFromTemplate(template).sections : [],
      });
    },
    [templates],
  );

  const setTitle = useCallback((title: string) => {
    setDraft((current) => ({ ...current, title }));
  }, []);

  const setScope = useCallback((scopeId: string) => {
    setDraft((current) => ({ ...current, scopeId }));
  }, []);

  const addSection = useCallback((kind: SectionKind) => {
    setDraft((current) => ({
      ...current,
      sections: normaliseSections([
        ...current.sections,
        createSection(kind, current.sections.length),
      ]),
    }));
  }, []);

  const patchSection = useCallback((id: string, patch: SectionPatch) => {
    setDraft((current) => ({
      ...current,
      sections: updateSection(current.sections, id, patch),
    }));
  }, []);

  const toggle = useCallback((id: string) => {
    setDraft((current) => ({
      ...current,
      sections: toggleSection(current.sections, id),
    }));
  }, []);

  const move = useCallback((id: string, direction: -1 | 1) => {
    setDraft((current) => ({
      ...current,
      sections: moveSection(current.sections, id, direction),
    }));
  }, []);

  const remove = useCallback((id: string) => {
    setDraft((current) => ({
      ...current,
      sections: normaliseSections(
        current.sections.filter((section) => section.id !== id),
      ),
    }));
  }, []);

  const reset = useCallback(() => setDraft(initial), [initial]);

  return {
    draft,
    errors: validateDraft(draft),
    selectTemplate,
    loadReport,
    setTitle,
    setScope,
    addSection,
    patchSection,
    toggle,
    move,
    remove,
    reset,
  };
}
