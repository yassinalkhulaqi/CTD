/** Pure helpers shared by the writeups UI. No React or network access here. */

import type { BadgeTone } from "../../components/ui";
import {
  CATEGORY_LABELS,
  type LibraryFilters,
  type MarkdownSection,
  type TocEntry,
  type Writeup,
  type WriteupCategory,
  type WriteupStatus,
} from "./types";

const PRIOR_MEAN = 3.5;
const PRIOR_WEIGHT = 4;
const MAX_TAGS = 8;

/**
 * Blend observed ratings with a prior so a single five-star vote cannot dominate.
 *
 * @param sum - Sum of all submitted scores.
 * @param count - Number of submitted scores.
 * @param priorMean - The neutral score assumed before any votes.
 * @param priorWeight - The weight of the prior, expressed in votes.
 * @returns A score clamped to the one-to-five range.
 */
export function bayesianScore(
  sum: number,
  count: number,
  priorMean = PRIOR_MEAN,
  priorWeight = PRIOR_WEIGHT,
): number {
  if (count <= 0) return priorMean;
  const blended = (sum + priorMean * priorWeight) / (count + priorWeight);
  return Math.round(Math.min(5, Math.max(1, blended)) * 100) / 100;
}

/**
 * Convert a title into a stable anchor slug.
 *
 * @param value - The raw title.
 * @returns A lowercase hyphenated slug.
 */
export function slugify(value: string): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/'/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || "writeup"
  );
}

/**
 * Clean and de-duplicate a list of tags.
 *
 * @param tags - Raw tag strings, optionally hash-prefixed.
 * @returns Normalised tags in first-seen order.
 */
export function normaliseTags(tags: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of tags) {
    const tag = raw
      .trim()
      .replace(/^#/, "")
      .toLowerCase()
      .replace(/[^a-z0-9+.-]+/g, "-")
      .replace(/^-|-$/g, "");
    if (!tag || seen.has(tag)) continue;
    seen.add(tag);
    result.push(tag);
    if (result.length >= MAX_TAGS) break;
  }
  return result;
}

/**
 * Count words in a markdown body.
 *
 * @param body - The markdown text.
 * @returns The number of words.
 */
export function countWords(body: string): number {
  return (body.match(/\b\w+(?:['’-]\w+)*\b/g) ?? []).length;
}

/**
 * Estimate reading time in minutes.
 *
 * @param body - The markdown text.
 * @param wordsPerMinute - Reading speed assumption.
 * @returns Minutes, with a one minute floor for non-empty text.
 */
export function readingTime(body: string, wordsPerMinute = 200): number {
  const words = countWords(body);
  if (words === 0) return 0;
  const speed = wordsPerMinute > 0 ? wordsPerMinute : 200;
  return Math.max(1, Math.ceil(words / speed));
}

/**
 * Produce a plain-text preview of a markdown body.
 *
 * @param body - The markdown text.
 * @param limit - Maximum length in characters.
 * @returns The truncated preview.
 */
export function excerpt(body: string, limit = 160): string {
  const plain = body
    .replace(/`{1,3}([^`]*)`{1,3}/g, "$1")
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/[*_>~-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (plain.length <= limit) return plain;
  const cut = plain.slice(0, limit);
  const boundary = cut.lastIndexOf(" ");
  return `${cut.slice(0, boundary > 0 ? boundary : limit).trimEnd()}…`;
}

function cleanHeading(raw: string): string {
  return raw
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/[*_`]+/g, "")
    .replace(/\s+#+\s*$/, "")
    .trim();
}

/**
 * Build a table of contents from ATX headings.
 *
 * Heading duplicates receive numeric suffixes so anchors stay unique.
 *
 * @param body - The markdown body.
 * @param minLevel - Lowest heading level included (defaults to h2).
 * @returns An ordered list of table of contents entries.
 */
export function buildToc(body: string, minLevel = 2): TocEntry[] {
  const used = new Map<string, number>();
  const entries: TocEntry[] = [];
  for (const line of body.split(/\r?\n/)) {
    const match = /^\s{0,3}(#{1,6})\s+(.+?)\s*$/.exec(line);
    if (!match) continue;
    const level = match[1].length;
    if (level < minLevel || level > 4) continue;
    const title = cleanHeading(match[2]);
    if (!title) continue;
    const base = slugify(title);
    const seen = used.get(base) ?? 0;
    used.set(base, seen + 1);
    entries.push({
      level,
      title,
      anchor: seen === 0 ? base : `${base}-${seen}`,
    });
  }
  return entries;
}

/**
 * Split markdown into heading-delimited sections for the reader.
 *
 * @param body - The markdown body.
 * @returns Sections with stable anchors and their raw content.
 */
export function splitMarkdownSections(body: string): MarkdownSection[] {
  const sections: MarkdownSection[] = [];
  const used = new Map<string, number>();
  let title = "Introduction";
  let level = 2;
  let anchor = "introduction";
  let lines: string[] = [];

  const flush = () => {
    sections.push({ level, title, anchor, content: lines.join("\n").trim() });
  };

  for (const line of body.split(/\r?\n/)) {
    const match = /^\s{0,3}(#{1,6})\s+(.+?)\s*$/.exec(line);
    if (!match) {
      lines.push(line);
      continue;
    }
    if (lines.length > 0 || sections.length > 0) flush();
    level = match[1].length;
    title = cleanHeading(match[2]) || "Untitled";
    const base = slugify(title);
    const seen = used.get(base) ?? 0;
    used.set(base, seen + 1);
    anchor = seen === 0 ? base : `${base}-${seen}`;
    lines = [];
  }
  flush();
  return sections;
}

/**
 * Format a count using compact notation for large values.
 *
 * @param value - The count to format.
 * @returns A compact label such as `1.2k`.
 */
export function formatCount(value: number): string {
  if (value < 1000) return String(value);
  const thousands = value / 1000;
  return `${thousands >= 10 ? Math.round(thousands) : thousands.toFixed(1)}k`;
}

/**
 * Map a status onto the semantic badge tone used by the design system.
 *
 * @param status - The publication status.
 * @returns The matching badge tone.
 */
export function statusTone(status: WriteupStatus): BadgeTone {
  if (status === "published") return "success";
  if (status === "review") return "warning";
  return "neutral";
}

/**
 * Return the display label of a category.
 *
 * @param category - The category key.
 * @returns The human readable label.
 */
export function categoryLabel(category: WriteupCategory): string {
  return CATEGORY_LABELS[category];
}

/**
 * Render an ISO timestamp as a short relative label.
 *
 * @param iso - The ISO timestamp.
 * @param now - Optional reference time, useful for deterministic tests.
 * @returns A relative label such as `3d ago`.
 */
export function relativeDate(iso: string, now = Date.now()): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const seconds = Math.max(0, Math.floor((now - then) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

/**
 * Apply library filters and sorting to an in-memory list.
 *
 * @param writeups - The source writeups.
 * @param filters - The active filter configuration.
 * @returns The filtered and ordered list.
 */
export function filterAndSort(
  writeups: Writeup[],
  filters: LibraryFilters,
): Writeup[] {
  const search = filters.search.trim().toLowerCase();
  const tag = filters.tag.trim().toLowerCase();
  const result = writeups.filter((writeup) => {
    if (filters.status !== "all" && writeup.status !== filters.status)
      return false;
    if (filters.category !== "all" && writeup.category !== filters.category)
      return false;
    if (tag && !writeup.tags.some((item) => item.includes(tag))) return false;
    if (!search) return true;
    const haystack = `${writeup.title} ${writeup.summary} ${writeup.body} ${writeup.tags.join(" ")}`;
    return search
      .split(/\s+/)
      .every((term) => haystack.toLowerCase().includes(term));
  });
  return result.sort((a, b) => {
    if (filters.sort === "rating") return b.bayesian_score - a.bayesian_score;
    if (filters.sort === "views") return b.views - a.views;
    if (filters.sort === "title") return a.title.localeCompare(b.title);
    return b.created_at.localeCompare(a.created_at);
  });
}

/**
 * Collect the distinct tags present in a list of writeups.
 *
 * @param writeups - The writeups to inspect.
 * @returns Sorted unique tags with their occurrence counts.
 */
export function tagFrequency(
  writeups: Writeup[],
): { tag: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const writeup of writeups) {
    for (const tag of writeup.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
}
