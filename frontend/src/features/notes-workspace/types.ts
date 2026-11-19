/**
 * Domain types and view models for the notes workspace feature.
 */

/** The rendering mode of a note body. */
export type NoteFormat = "markdown" | "plain" | "code";

/** The catalogue group of a note template. */
export type TemplateCategory =
  | "general"
  | "checklist"
  | "web"
  | "crypto"
  | "pwn"
  | "reverse"
  | "forensics"
  | "osint";

/** A Markdown heading extracted from a note body. */
export interface NoteHeading {
  level: number;
  text: string;
  line: number;
  anchor: string;
  indent: number;
}

/** A versioned note returned by the API. */
export interface NoteEntry {
  id: string;
  challenge_id: string;
  member_id: string;
  title: string;
  body: string;
  format: NoteFormat;
  tags: string[];
  pinned: boolean;
  version: number;
  created_at: string;
  updated_at: string;
  word_count: number;
  reading_time_minutes: number;
  excerpt: string;
  headings: NoteHeading[];
  tag_count: number;
  is_pinned: boolean;
}

/** A snapshot in the revision history of a note. */
export interface NoteRevision {
  id: string;
  note_id: string;
  version: number;
  body: string;
  author_id: string;
  created_at: string;
  added: number;
  removed: number;
  net: number;
  changed: boolean;
  magnitude: number;
  is_latest: boolean;
  change_summary: string;
}

/** A reusable note skeleton with template variables. */
export interface NoteTemplate {
  id: string;
  name: string;
  category: TemplateCategory;
  body: string;
  variables: string[];
  variable_count: number;
  line_count: number;
}

/** The outcome of rendering a template. */
export interface TemplateRenderResult {
  body: string;
  used_variables: string[];
  unused_variables: string[];
  variable_count: number;
}

/** Aggregated note statistics for one challenge. */
export interface ChallengeNotesSummary {
  challenge_id: string;
  note_count: number;
  pinned_count: number;
  revision_count: number;
  word_count: number;
  unique_authors: number;
  top_tags: string[];
  average_words: number;
  pinned_ratio: number;
}

/** Workspace wide note statistics. */
export interface NotesSummary {
  challenges: ChallengeNotesSummary[];
  total_notes: number;
  total_revisions: number;
  total_words: number;
  pinned_notes: number;
  unique_tags: string[];
  generated_at: string;
  challenge_count: number;
  average_words: number;
}

/** Filters accepted by the notes list endpoint. */
export interface NoteFilters {
  challengeId?: string;
  memberId?: string;
  tag?: string;
  query?: string;
  pinned?: boolean;
}

/** The editable representation of a note. */
export interface NoteDraft {
  title: string;
  body: string;
  format: NoteFormat;
  tags: string[];
  pinned: boolean;
}

/** The persistence state shown in the editor meta bar. */
export type SaveState = "saved" | "unsaved" | "saving" | "error";

/** A template variable paired with the value entered by the user. */
export interface TemplateVariableValue {
  name: string;
  value: string;
}

/** Payload accepted when a note is created. */
export interface NoteCreatePayload {
  challenge_id: string;
  member_id: string;
  title: string;
  body: string;
  format: NoteFormat;
  tags: string[];
  pinned: boolean;
}

/** Payload accepted when a note is updated. */
export interface NoteUpdatePayload {
  title?: string;
  body?: string;
  format?: NoteFormat;
  tags?: string[];
  expected_version?: number;
  author_id?: string;
}

/** Payload accepted when a template is created. */
export interface NoteTemplateCreatePayload {
  name: string;
  category: TemplateCategory;
  body: string;
}

/** Payload accepted by the template render endpoint. */
export interface TemplateRenderPayload {
  template_id?: string;
  body?: string;
  variables: Record<string, string>;
}
