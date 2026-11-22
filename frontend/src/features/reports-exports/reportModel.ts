/**
 * Pure view-model helpers for the report builder.
 *
 * Keeping these transformations independent of React makes the editor rules
 * easy to test and lets the page stay a thin composition layer.
 */

import type {
  DraftErrors,
  PlaceholderResult,
  ReportDraft,
  ReportFormat,
  ReportPreview,
  ReportStats,
  RenderedSection,
  SectionConfig,
  SectionKind,
  SectionPatch,
} from "./types";

/** Human readable labels for the four export formats. */
export const FORMAT_LABELS: Record<ReportFormat, string> = {
  markdown: "Markdown",
  csv: "CSV",
  json: "JSON",
  html: "HTML",
};

/** File extensions of the four export formats. */
export const FORMAT_EXTENSIONS: Record<ReportFormat, string> = {
  markdown: "md",
  csv: "csv",
  json: "json",
  html: "html",
};

/** Short descriptions shown in the export menu. */
export const FORMAT_HINTS: Record<ReportFormat, string> = {
  markdown: "Headings, tables and bullet lists",
  csv: "Flattened rows for spreadsheets",
  json: "Structured payload with pretty printing",
  html: "Standalone printable document",
};

/** Human readable labels for section kinds. */
export const KIND_LABELS: Record<SectionKind, string> = {
  text: "Text",
  table: "Table",
  list: "List",
  metrics: "Metrics",
};

/** Placeholder pattern shared with the backend renderer. */
export const PLACEHOLDER_RE =
  /\{\{\s*([A-Za-z0-9_.-]+)(?:\s*\|\|\s*([^{}]*?))?\s*\}\}/g;

/** All export formats in display order. */
export const FORMAT_ORDER: ReportFormat[] = ["markdown", "csv", "json", "html"];

/** All section kinds in display order. */
export const KIND_ORDER: SectionKind[] = ["text", "table", "list", "metrics"];

const DEFAULT_BODIES: Record<SectionKind, string> = {
  text: "Summarise the highlights for {{ team || the team }}.",
  table: "",
  list: "",
  metrics: "",
};

const DEFAULT_SOURCES: Record<SectionKind, string> = {
  text: "",
  table: "challenges",
  list: "members",
  metrics: "score",
};

const DEFAULT_COLUMNS: Record<SectionKind, string[]> = {
  text: [],
  table: ["title", "points"],
  list: [],
  metrics: [],
};

/**
 * Create a section with sensible defaults for its kind.
 *
 * @param kind - The kind of section to create.
 * @param order - The initial display order.
 * @returns A new section configuration.
 */
export function createSection(kind: SectionKind, order: number): SectionConfig {
  return {
    id: `section-${Date.now().toString(36)}-${order}`,
    title: `New ${KIND_LABELS[kind].toLowerCase()} section`,
    kind,
    body: DEFAULT_BODIES[kind],
    source: DEFAULT_SOURCES[kind],
    columns: [...DEFAULT_COLUMNS[kind]],
    enabled: true,
    order,
  };
}

/**
 * Sort sections and rewrite their order values as a contiguous sequence.
 *
 * @param sections - The sections to normalise.
 * @returns A new array with sequential order values.
 */
export function normaliseSections(sections: SectionConfig[]): SectionConfig[] {
  return [...sections]
    .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id))
    .map((section, index) => ({ ...section, order: index }));
}

/**
 * Apply a partial edit to one section.
 *
 * @param sections - The current sections.
 * @param id - The identifier of the section to edit.
 * @param patch - The fields to replace.
 * @returns A new array with the edited section.
 */
export function updateSection(
  sections: SectionConfig[],
  id: string,
  patch: SectionPatch,
): SectionConfig[] {
  return sections.map((section) =>
    section.id === id ? { ...section, ...patch } : section,
  );
}

/**
 * Toggle whether a section participates in rendering.
 *
 * @param sections - The current sections.
 * @param id - The identifier of the section to toggle.
 * @returns A new array with the toggled section.
 */
export function toggleSection(
  sections: SectionConfig[],
  id: string,
): SectionConfig[] {
  return updateSection(sections, id, {
    enabled: !sections.find((section) => section.id === id)?.enabled,
  });
}

/**
 * Move a section one position up or down and normalise the result.
 *
 * @param sections - The current sections.
 * @param id - The identifier of the section to move.
 * @param direction - `-1` moves up, `1` moves down.
 * @returns A new array in the new order.
 */
export function moveSection(
  sections: SectionConfig[],
  id: string,
  direction: -1 | 1,
): SectionConfig[] {
  const ordered = normaliseSections(sections);
  const index = ordered.findIndex((section) => section.id === id);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= ordered.length) return ordered;
  const next = [...ordered];
  const [moved] = next.splice(index, 1);
  if (!moved) return ordered;
  next.splice(target, 0, moved);
  return next.map((section, index) => ({ ...section, order: index }));
}

/**
 * Build an editable draft from a saved template.
 *
 * @param template - The template selected in the picker.
 * @returns A fresh draft with normalised sections.
 */
export function draftFromTemplate(template: {
  id: string;
  name: string;
  sections: SectionConfig[];
}): ReportDraft {
  return {
    templateId: template.id,
    title: template.name,
    scopeId: "team",
    sections: normaliseSections(template.sections),
  };
}

/**
 * Resolve placeholder tokens against a data snapshot.
 *
 * @param text - Text containing `{{ key || fallback }}` tokens.
 * @param data - The data snapshot.
 * @returns The resolved text and the list of missing keys.
 */
export function resolvePlaceholders(
  text: string,
  data: Record<string, unknown>,
): PlaceholderResult {
  const missing: string[] = [];
  const resolved = text.replace(
    PLACEHOLDER_RE,
    (_match: string, key: string, fallback: string | undefined) => {
      const value = lookup(data, key);
      if (value === undefined || value === null || value === "") {
        if (!missing.includes(key)) missing.push(key);
        return fallback ?? "";
      }
      return stringify(value);
    },
  );
  return { text: resolved, missing };
}

/**
 * Resolve a dotted path inside a nested snapshot.
 *
 * @param data - The data snapshot.
 * @param path - A dotted key path.
 * @returns The value or `undefined` when the path does not exist.
 */
function lookup(data: Record<string, unknown>, path: string): unknown {
  let current: unknown = data;
  for (const part of path.split(".")) {
    if (typeof current !== "object" || current === null) return undefined;
    if (!(part in current)) return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return current;
}

/**
 * Convert a snapshot value into a compact display string.
 *
 * @param value - The value to convert.
 * @returns The display string.
 */
function stringify(value: unknown): string {
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (Array.isArray(value)) return value.map(stringify).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/**
 * Return every unique placeholder token in a piece of text.
 *
 * @param text - The text to inspect.
 * @returns The token list in first-seen order.
 */
export function placeholderTokens(text: string): string[] {
  const tokens: string[] = [];
  for (const match of text.matchAll(PLACEHOLDER_RE)) {
    const key = match[1];
    if (key && !tokens.includes(key)) tokens.push(key);
  }
  return tokens;
}

/**
 * Validate the editable draft before a report is created.
 *
 * @param draft - The current builder state.
 * @returns A map of field errors, empty when the draft is valid.
 */
export function validateDraft(draft: ReportDraft): DraftErrors {
  const errors: DraftErrors = {};
  if (!draft.title.trim()) errors.title = "Give the report a title.";
  if (!draft.scopeId.trim()) errors.scopeId = "Choose a scope for this report.";
  if (!draft.templateId) errors.sections = "Select a template first.";
  else if (!draft.sections.some((section) => section.enabled))
    errors.sections = "Enable at least one section.";
  return errors;
}

/**
 * Build the API payload for creating a report.
 *
 * @param draft - The current builder state.
 * @param data - The data snapshot to capture.
 * @returns The request payload.
 */
export function buildCreatePayload(
  draft: ReportDraft,
  data: Record<string, unknown>,
): {
  template_id: string;
  title: string;
  scope_id: string;
  data: Record<string, unknown>;
} {
  return {
    template_id: draft.templateId,
    title: draft.title.trim(),
    scope_id: draft.scopeId.trim(),
    data,
  };
}

/**
 * Format a byte count for display.
 *
 * @param bytes - The number of bytes.
 * @returns A human readable size.
 */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Format an ISO timestamp as a stable calendar date.
 *
 * @param iso - The ISO timestamp.
 * @returns A `YYYY-MM-DD` string.
 */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso.slice(0, 10);
  return date.toISOString().slice(0, 10);
}

/**
 * Collapse and truncate text for compact previews.
 *
 * @param text - The text to shorten.
 * @param limit - The maximum length.
 * @returns The shortened text.
 */
export function excerpt(text: string, limit = 160): string {
  const collapsed = text.replace(/\s+/g, " ").trim();
  return collapsed.length <= limit
    ? collapsed
    : `${collapsed.slice(0, limit - 1)}…`;
}

/**
 * Summarise studio counters in one line.
 *
 * @param stats - The studio counters.
 * @returns A short status sentence.
 */
export function statsSentence(stats: ReportStats): string {
  return `${stats.reports} reports · ${stats.templates} templates · ${stats.exports} exports`;
}

/**
 * Return whether a report can be exported.
 *
 * @param isFinal - The finalisation state of the selected report.
 * @returns `true` when exports are allowed.
 */
export function canExport(isFinal: boolean): boolean {
  return isFinal;
}

export function buildLocalPreview(
  draft: ReportDraft,
  data: Record<string, unknown>,
  format: ReportFormat,
): ReportPreview {
  const sections: RenderedSection[] = draft.sections
    .filter((section) => section.enabled)
    .map((section) => {
      const title = resolvePlaceholders(section.title, data);
      const body = resolvePlaceholders(section.body, data);
      const source = resolvePlaceholders(section.source, data);
      const value = source.text ? data[source.text] : undefined;
      const warnings = [...title.missing, ...body.missing, ...source.missing];
      const rendered: RenderedSection = {
        id: section.id,
        title: title.text || section.title,
        kind: section.kind,
        text: body.text,
        columns: [],
        rows: [],
        items: [],
        metrics: [],
        warnings: [...new Set(warnings)],
        row_count: 0,
        is_empty: true,
      };

      if (section.kind === "table") {
        const records = Array.isArray(value)
          ? value.filter(
              (item): item is Record<string, unknown> =>
                typeof item === "object" && item !== null,
            )
          : [];
        const columns =
          section.columns.length > 0
            ? section.columns
            : [...new Set(records.flatMap((record) => Object.keys(record)))];
        rendered.columns = columns;
        rendered.rows = records.map((record) =>
          columns.map((column) => stringify(record[column] ?? "")),
        );
        rendered.row_count = rendered.rows.length;
      } else if (section.kind === "list") {
        rendered.items = Array.isArray(value)
          ? value.map(stringify)
          : value === undefined
            ? []
            : [stringify(value)];
        rendered.row_count = rendered.items.length;
      } else if (section.kind === "metrics") {
        if (
          typeof value === "object" &&
          value !== null &&
          !Array.isArray(value)
        ) {
          rendered.metrics = Object.entries(value).map(([key, item]) => [
            key,
            stringify(item),
          ]);
        } else if (value !== undefined) {
          rendered.metrics = [[source.text || "value", stringify(value)]];
        }
        rendered.row_count = rendered.metrics.length;
      }

      rendered.is_empty =
        rendered.row_count === 0 &&
        rendered.items.length === 0 &&
        rendered.metrics.length === 0 &&
        rendered.text.trim().length === 0;
      return rendered;
    });

  const summary: Record<string, number> = {};
  Object.entries(data).forEach(([key, value]) => {
    if (Array.isArray(value) || (typeof value === "object" && value !== null)) {
      summary[key] = Array.isArray(value)
        ? value.length
        : Object.keys(value as Record<string, unknown>).length;
    } else if (typeof value === "number") {
      summary[key] = value;
    }
  });

  const warnings = [
    ...new Set(sections.flatMap((section) => section.warnings)),
  ];
  return {
    title: draft.title,
    format,
    generated_at: new Date().toISOString(),
    summary,
    meta: {
      template: draft.templateId,
      scope: draft.scopeId,
    },
    warnings,
    sections,
    section_count: sections.length,
    total_rows: sections.reduce(
      (total, section) => total + section.row_count,
      0,
    ),
    has_warnings: warnings.length > 0,
    is_empty:
      sections.length === 0 || sections.every((section) => section.is_empty),
  };
}
