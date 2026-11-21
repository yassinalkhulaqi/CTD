/**
 * Domain types of the report studio feature.
 */

/** Serialisation formats supported by the export pipeline. */
export type ReportFormat = "markdown" | "csv" | "json" | "html";

/** Lifecycle state of a report. */
export type ReportStatus = "draft" | "final";

/** Audience a template was designed for. */
export type TemplateScope = "team" | "event" | "global";

/** How a section obtains and displays its content. */
export type SectionKind = "text" | "table" | "list" | "metrics";

/** One configurable block inside a report template. */
export interface SectionConfig {
  id: string;
  title: string;
  kind: SectionKind;
  body: string;
  source: string;
  columns: string[];
  enabled: boolean;
  order: number;
}

/** A reusable arrangement of report sections. */
export interface ReportTemplate {
  id: string;
  name: string;
  format: ReportFormat;
  scope: TemplateScope;
  updated_at: string;
  sections: SectionConfig[];
  section_count: number;
  description: string;
}

/** A report instance created from a template. */
export interface Report {
  id: string;
  template_id: string;
  title: string;
  scope_id: string;
  status: ReportStatus;
  created_at: string;
  data: Record<string, unknown>;
  is_final: boolean;
}

/** A materialised export job. */
export interface ExportJob {
  id: string;
  report_id: string;
  format: ReportFormat;
  status: string;
  content: string;
  created_at: string;
  byte_size: number;
  line_count: number;
  extension: string;
  mime_type: string;
  is_complete: boolean;
}

/** Structured content of one rendered section. */
export interface RenderedSection {
  id: string;
  title: string;
  kind: SectionKind;
  text: string;
  columns: string[];
  rows: string[][];
  items: string[];
  metrics: string[][];
  warnings: string[];
  row_count: number;
  is_empty: boolean;
}

/** A rendered report preview returned by the API. */
export interface ReportPreview {
  title: string;
  format: ReportFormat;
  generated_at: string;
  summary: Record<string, number>;
  meta: Record<string, string>;
  warnings: string[];
  sections: RenderedSection[];
  section_count: number;
  total_rows: number;
  has_warnings: boolean;
  is_empty: boolean;
}

/** Aggregate counters for the studio. */
export interface ReportStats {
  templates: number;
  reports: number;
  draft_reports: number;
  final_reports: number;
  exports: number;
  exports_by_format: Record<string, number>;
  total_artifacts: number;
  finalisation_rate: number;
}

/** Local editable state of the report builder. */
export interface ReportDraft {
  templateId: string;
  title: string;
  scopeId: string;
  sections: SectionConfig[];
}

/** A partial edit applied to one section. */
export type SectionPatch = Partial<Omit<SectionConfig, "id">>;

/** Validation messages keyed by builder field. */
export interface DraftErrors {
  title?: string;
  scopeId?: string;
  sections?: string;
}

/** Payload sent when creating a report. */
export interface ReportCreatePayload {
  template_id: string;
  title: string;
  scope_id: string;
  data: Record<string, unknown>;
}

/** The outcome of a placeholder substitution. */
export interface PlaceholderResult {
  text: string;
  missing: string[];
}
