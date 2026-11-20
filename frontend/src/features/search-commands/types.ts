/** Domain types and view models for the search workspace. */

/** Kinds of document that can be indexed. */
export type SearchKind = "challenge" | "team" | "member" | "custom";

/** A normalised document held in the search index. */
export interface SearchDocument {
  id: string;
  kind: SearchKind;
  title: string;
  body: string;
  tags: string[];
  path: string;
  updated_at: string;
  key: string;
}

/** A highlighted span with offsets relative to a result field. */
export interface SearchHighlight {
  start: number;
  end: number;
  text: string;
  field: string;
}

/** A ranked hit returned by the search API. */
export interface SearchResult {
  document_id: string;
  kind: SearchKind;
  title: string;
  snippet: string;
  score: number;
  highlights: SearchHighlight[];
  path: string;
  relevance: string;
}

/** Echo of the query that produced a result set. */
export interface ParsedQuery {
  text: string;
  kinds: SearchKind[];
  tags: string[];
  limit: number;
  tokens: string[];
  has_filters: boolean;
}

/** The payload returned by the search endpoint. */
export interface SearchResponse {
  query: ParsedQuery;
  results: SearchResult[];
  total_indexed: number;
  returned: number;
}

/** A command available in the palette. */
export interface Command {
  id: string;
  name: string;
  description: string;
  group: string;
  shortcut: string;
  keywords: string[];
  initials: string;
  shortcut_label: string;
}

/** The command catalogue and its groups. */
export interface CommandList {
  commands: Command[];
  groups: string[];
  total: number;
}

/** Descriptor returned after a command is executed. */
export interface CommandExecution {
  command_id: string;
  name: string;
  action: string;
  target: string;
  message: string;
  arguments: string;
  is_navigation: boolean;
}

/** Counters describing the index. */
export interface SearchStats {
  document_count: number;
  command_count: number;
  documents_by_kind: Record<string, number>;
  top_tags: Array<[string, number]>;
  average_body_length: number;
  has_documents: boolean;
  distinct_kinds: number;
}

/** Query parameters accepted by the search endpoint. */
export interface SearchQuery {
  q: string;
  limit?: number;
  kinds?: SearchKind[];
  tags?: string[];
}

/** Payload for the bulk index endpoint. */
export interface IndexRequest {
  documents?: SearchDocumentInput[];
  include_repositories?: boolean;
  clear?: boolean;
}

/** A custom document submitted for indexing. */
export interface SearchDocumentInput {
  id: string;
  kind: SearchKind;
  title: string;
  body: string;
  tags: string[];
  path: string;
}

/** Summary returned after an indexing run. */
export interface IndexResponse {
  indexed: number;
  by_kind: Record<string, number>;
  skipped: number;
  document_count: number;
}

/** Payload for registering a command. */
export interface CommandInput {
  id: string;
  name: string;
  description: string;
  group: string;
  shortcut: string;
  keywords: string[];
}

/** Options presented by the result-kind filter. */
export const KIND_OPTIONS: Array<{
  value: SearchKind;
  label: string;
  accent: string;
}> = [
  { value: "challenge", label: "Challenges", accent: "accent" },
  { value: "team", label: "Teams", accent: "info" },
  { value: "member", label: "Members", accent: "success" },
  { value: "custom", label: "Custom", accent: "warning" },
];

/** Return the display label of a document kind. */
export function kindLabel(kind: SearchKind): string {
  return KIND_OPTIONS.find((option) => option.value === kind)?.label ?? kind;
}
