/** Pure helpers shared by the search page, the palette and the tests. */

import type { Command, SearchKind, SearchResult } from "./types";

const STOPWORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "be",
  "by",
  "for",
  "from",
  "in",
  "is",
  "it",
  "of",
  "on",
  "or",
  "the",
  "to",
  "with",
]);

export interface LocalQuery {
  text: string;
  kinds: SearchKind[];
  tags: string[];
}

const KINDS: SearchKind[] = ["challenge", "team", "member", "custom"];

/**
 * Fold text into lowercase ASCII-like tokens for matching.
 *
 * @param raw - The text to fold.
 * @returns The folded text.
 */
export function foldText(raw: string): string {
  return raw
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * Tokenise a query, dropping stopwords unless every word is a stopword.
 *
 * @param raw - The raw query text.
 * @returns The normalised tokens.
 */
export function tokenizeQuery(raw: string): string[] {
  const words = foldText(raw).split(" ").filter(Boolean);
  const meaningful = words.filter((word) => !STOPWORDS.has(word));
  return meaningful.length > 0 ? meaningful : words;
}

/**
 * Extract inline `kind:` and `tag:` filters from a query string.
 *
 * @param raw - The raw query text.
 * @returns The text and filters in a normalised form.
 */
export function parseQueryText(raw: string): LocalQuery {
  const words: string[] = [];
  const kinds: SearchKind[] = [];
  const tags: string[] = [];
  for (const word of raw.split(/\s+/)) {
    const lower = word.toLowerCase();
    if (lower.startsWith("kind:") && lower.length > 5) {
      const value = foldText(lower.slice(5));
      const kind = KINDS.find((candidate) => candidate === value);
      if (kind && !kinds.includes(kind)) kinds.push(kind);
    } else if (lower.startsWith("tag:") && lower.length > 4) {
      const value = foldText(lower.slice(4));
      if (value && !tags.includes(value)) tags.push(value);
    } else if (word) {
      words.push(word);
    }
  }
  return { text: words.join(" ").trim(), kinds, tags };
}

/**
 * Rank results by score with an identifier tie-break.
 *
 * @param results - The results to order.
 * @param limit - Optional maximum number of results.
 * @returns The ordered results.
 */
export function rankResults(
  results: SearchResult[],
  limit?: number,
): SearchResult[] {
  const ordered = [...results].sort(
    (a, b) => b.score - a.score || a.document_id.localeCompare(b.document_id),
  );
  return limit === undefined ? ordered : ordered.slice(0, limit);
}

/**
 * Return up to four initials for a command name.
 *
 * @param name - The command name.
 * @returns The initials in uppercase.
 */
export function commandInitials(name: string): string {
  return foldText(name)
    .split(" ")
    .filter(Boolean)
    .slice(0, 4)
    .map((word) => word[0])
    .join("");
}

/**
 * Score a command against a query by substring, initials and keywords.
 *
 * @param command - The command to score.
 * @param query - The raw query.
 * @returns A non-negative match score.
 */
export function commandScore(command: Command, query: string): number {
  const phrase = foldText(query);
  if (!phrase) return 0;
  const name = foldText(command.name);
  const initials = commandInitials(command.name);
  const keywords = command.keywords.map(foldText);
  if (name === phrase) return 12;
  let score = 0;
  if (name.includes(phrase)) score = name.startsWith(phrase) ? 9 : 8;
  if (initials.includes(phrase)) score = Math.max(score, 6);
  for (const keyword of keywords) {
    if (keyword === phrase) score = Math.max(score, 5);
    else if (keyword.includes(phrase)) score = Math.max(score, 3);
  }
  if (foldText(command.description).includes(phrase))
    score = Math.max(score, 1.5);
  return score;
}

/**
 * Filter and rank commands using fuzzy matching.
 *
 * @param commands - The available commands.
 * @param query - The raw query.
 * @returns The matching commands in display order.
 */
export function filterCommands(commands: Command[], query: string): Command[] {
  if (!query.trim())
    return [...commands].sort((a, b) => a.id.localeCompare(b.id));
  return commands
    .map((command) => ({ command, score: commandScore(command, query) }))
    .filter((entry) => entry.score > 0)
    .sort(
      (a, b) => b.score - a.score || a.command.id.localeCompare(b.command.id),
    )
    .map((entry) => entry.command);
}

/**
 * Group commands by their declared group name.
 *
 * @param commands - The commands to group.
 * @returns A mapping of group name to commands.
 */
export function groupCommands(commands: Command[]): Record<string, Command[]> {
  const grouped: Record<string, Command[]> = {};
  for (const command of commands) {
    const group = command.group || "General";
    grouped[group] = [...(grouped[group] ?? []), command];
  }
  return Object.fromEntries(
    Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)),
  );
}

/**
 * Maintain a bounded list of recent, unique queries.
 *
 * @param previous - Existing recent queries.
 * @param query - The query to add.
 * @param maximum - Maximum number of entries to keep.
 * @returns The updated list, newest first.
 */
export function buildRecentQueries(
  previous: string[],
  query: string,
  maximum = 6,
): string[] {
  const value = query.trim();
  if (!value) return previous.slice(0, maximum);
  return [value, ...previous.filter((item) => item !== value)].slice(
    0,
    maximum,
  );
}

/**
 * Return a coarse relevance label for a score.
 *
 * @param score - The relevance score.
 * @returns The display label.
 */
export function scoreLabel(score: number): string {
  if (score >= 12) return "Exact";
  if (score >= 5) return "Strong";
  if (score > 0) return "Related";
  return "Indexed";
}

/**
 * Format a shortcut for display.
 *
 * @param shortcut - The raw shortcut string.
 * @returns The display form.
 */
export function formatShortcut(shortcut: string): string {
  return shortcut.replace(/Mod/g, "⌘/Ctrl").trim();
}
