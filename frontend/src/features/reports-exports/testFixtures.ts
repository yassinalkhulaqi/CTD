import type {
  ExportJob,
  Report,
  ReportPreview,
  ReportStats,
  ReportTemplate,
  SectionConfig,
} from "./types";

export const SECTIONS: SectionConfig[] = [
  {
    id: "summary",
    title: "Summary for {{ team }}",
    kind: "text",
    body: "Score: {{ score || unknown }}",
    source: "",
    columns: [],
    enabled: true,
    order: 0,
  },
  {
    id: "challenges",
    title: "Challenges",
    kind: "table",
    body: "",
    source: "challenges",
    columns: ["title", "points"],
    enabled: true,
    order: 1,
  },
  {
    id: "members",
    title: "Members",
    kind: "list",
    body: "",
    source: "members",
    columns: [],
    enabled: true,
    order: 2,
  },
];

export const TEMPLATE: ReportTemplate = {
  id: "tpl-1",
  name: "Weekly report",
  format: "markdown",
  scope: "team",
  updated_at: "2026-01-02T10:00:00Z",
  sections: SECTIONS,
  section_count: SECTIONS.length,
  description: "A weekly team summary with challenge detail.",
};

export const REPORT: Report = {
  id: "rep-1",
  template_id: "tpl-1",
  title: "Weekly report",
  scope_id: "redscribe",
  status: "final",
  created_at: "2026-01-03T10:00:00Z",
  data: {
    team: "redscribe",
    score: 900,
    challenges: [{ title: "Warmup", points: 100 }],
    members: ["Ada", "Lin"],
  },
  is_final: true,
};

export const DRAFT_REPORT: Report = {
  ...REPORT,
  id: "rep-2",
  status: "draft",
  is_final: false,
  title: "Draft report",
};

export const EXPORT_JOB: ExportJob = {
  id: "exp-1",
  report_id: "rep-1",
  format: "markdown",
  status: "complete",
  content: "# Weekly report",
  created_at: "2026-01-03T11:00:00Z",
  byte_size: 15,
  line_count: 1,
  extension: "md",
  mime_type: "text/markdown",
  is_complete: true,
};

export const PREVIEW: ReportPreview = {
  title: "Weekly report",
  format: "markdown",
  generated_at: "2026-01-03T10:00:00Z",
  summary: { challenges: 1, members: 2 },
  meta: {},
  warnings: [],
  sections: [
    {
      id: "summary",
      title: "Summary for redscribe",
      kind: "text",
      text: "Score: 900",
      columns: [],
      rows: [],
      items: [],
      metrics: [],
      warnings: [],
      row_count: 0,
      is_empty: false,
    },
    {
      id: "challenges",
      title: "Challenges",
      kind: "table",
      text: "",
      columns: ["title", "points"],
      rows: [["Warmup", "100"]],
      items: [],
      metrics: [],
      warnings: [],
      row_count: 1,
      is_empty: false,
    },
  ],
  section_count: 2,
  total_rows: 1,
  has_warnings: false,
  is_empty: false,
};

export const STATS: ReportStats = {
  templates: 1,
  reports: 1,
  draft_reports: 0,
  final_reports: 1,
  exports: 1,
  exports_by_format: { markdown: 1 },
  total_artifacts: 3,
  finalisation_rate: 100,
};
