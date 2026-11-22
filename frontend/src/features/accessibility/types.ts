export type Severity = "info" | "warning" | "critical";

export type ContrastLevel = "fail" | "aa" | "aaa";

export interface A11yIssue {
  id: string;
  path: string;
  rule_id: string;
  severity: Severity;
  description: string;
  suggestion: string;
  detected_at: string;
  resolved_at: string | null;
  is_resolved: boolean;
  severity_weight: number;
}

export interface Shortcut {
  id: string;
  keys: string;
  canonical_keys: string;
  display_keys: string;
  action: string;
  scope: string;
  is_global: boolean;
  is_chord: boolean;
}

export interface ShortcutConflict {
  description: string;
  left_id: string;
  right_id: string;
  keys: string;
}

export interface ContrastPairResult {
  foreground: string;
  background: string;
  path: string;
  label: string;
  large_text: boolean;
  ratio: number;
  passes_aa: boolean;
  passes_aaa: boolean;
  level: ContrastLevel;
  suggestion: string;
}

export interface ContrastAudit {
  pairs: ContrastPairResult[];
  issues: A11yIssue[];
  failures: number;
  pass_rate: number;
  average_ratio: number;
}

export interface FocusOrderEntry {
  id: string;
  label: string;
  order: number;
  aria_label: string;
}

export interface FocusTrapSnapshot {
  entries: FocusOrderEntry[];
  index: number;
  size: number;
  current_id: string | null;
  next_id: string | null;
  previous_id: string | null;
}

export interface AccessibilityStats {
  total_issues: number;
  open_issues: number;
  resolved_issues: number;
  critical_open: number;
  warning_open: number;
  info_open: number;
  shortcut_count: number;
  focus_entry_count: number;
  scopes: string[];
  severity_counts: Record<Severity, number>;
  resolution_rate: number;
  risk_score: number;
}

export interface IssueCreatePayload {
  path: string;
  rule_id: string;
  severity: Severity;
  description: string;
  suggestion?: string;
}

export interface ShortcutCreatePayload {
  keys: string;
  action: string;
  scope: string;
}

export interface ContrastAuditPayload {
  foreground: string;
  background: string;
  path?: string;
  label?: string;
  large_text?: boolean;
  record_issue?: boolean;
}

export interface FocusOrderCreatePayload {
  label: string;
  order?: number;
}

export interface AriaSuggestionPayload {
  text: string;
  context?: string;
  action?: string;
}

export interface ContrastDraft {
  foreground: string;
  background: string;
  label: string;
  largeText: boolean;
}

export interface ShortcutDraft {
  keys: string;
  action: string;
  scope: string;
}

export interface MotionPreferences {
  reducedMotion: boolean;
  highContrast: boolean;
}

export interface IssueFilters {
  severity: Severity | "all";
  includeResolved: boolean;
  query: string;
}

export const SEVERITY_OPTIONS: ReadonlyArray<{
  value: Severity | "all";
  label: string;
}> = [
  { value: "all", label: "All" },
  { value: "info", label: "Info" },
  { value: "warning", label: "Warning" },
  { value: "critical", label: "Critical" },
];

export const EMPTY_STATS: AccessibilityStats = {
  total_issues: 0,
  open_issues: 0,
  resolved_issues: 0,
  critical_open: 0,
  warning_open: 0,
  info_open: 0,
  shortcut_count: 0,
  focus_entry_count: 0,
  scopes: [],
  severity_counts: { info: 0, warning: 0, critical: 0 },
  resolution_rate: 0,
  risk_score: 0,
};
