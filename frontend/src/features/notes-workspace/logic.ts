/**
 * Pure helpers shared by the notes workspace UI.
 *
 * The preview renderer deliberately escapes all user text before it applies a
 * small Markdown-like formatting pass, so note content can never inject HTML.
 */

import type { NoteDraft, NoteEntry, SaveState } from "./types";

/** Maximum title length accepted by the editor. */
export const MAX_TITLE_LENGTH = 200;

/** Maximum body length accepted by the editor. */
export const MAX_BODY_LENGTH = 20_000;

/** Maximum number of tags accepted by the editor. */
export const MAX_TAGS = 12;

/** Reading speed used for the estimate. */
export const WORDS_PER_MINUTE = 200;

/** Default excerpt length. */
export const EXCERPT_LENGTH = 160;

const WORD_PATTERN = /[\w'-]+/g;
const VARIABLE_PATTERN = /\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}/g;
const SAFE_URL_PATTERN = /^(https?:\/\/|#|\/)/i;
const FENCE_PATTERN = /^\s{0,3}(```|~~~)(.*)$/;
const HEADING_PATTERN = /^(#{1,6})\s+(.+?)\s*#*\s*$/;
const LIST_PATTERN = /^\s*([-*+]|\d+\.)\s+/;

/**
 * Count the words in a body of text.
 *
 * @param text - The raw text.
 * @returns The number of word tokens.
 */
export function countWords(text: string): number {
  const matches = text.match(WORD_PATTERN);
  return matches ? matches.length : 0;
}

/**
 * Estimate the reading time in minutes.
 *
 * @param text - The raw text.
 * @param wordsPerMinute - Reading speed used for the estimate.
 * @returns The duration rounded to one decimal place.
 */
export function readingMinutes(
  text: string,
  wordsPerMinute: number = WORDS_PER_MINUTE,
): number {
  if (wordsPerMinute <= 0) return 0;
  return Math.round((countWords(text) / wordsPerMinute) * 10) / 10;
}

/**
 * Build a single line excerpt from a Markdown body.
 *
 * @param text - The raw body.
 * @param limit - Maximum length of the excerpt.
 * @returns The excerpt, with an ellipsis when truncated.
 */
export function makeExcerpt(
  text: string,
  limit: number = EXCERPT_LENGTH,
): string {
  const collapsed = text.replace(/\s+/g, " ").trim();
  const cleaned = collapsed
    .replace(/[#*_`>[\]]/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
  if (limit <= 0) return "";
  if (cleaned.length <= limit) return cleaned;
  return `${cleaned.slice(0, limit - 1).trimEnd()}…`;
}

/**
 * Normalise a single tag to its canonical form.
 *
 * @param tag - The raw tag.
 * @returns A lower-case slug.
 */
export function normaliseTag(tag: string): string {
  const lowered = tag.trim().toLowerCase().replace(/\s+/g, "-");
  return lowered
    .replace(/[^a-z0-9_-]/g, "")
    .slice(0, 32)
    .replace(/^[-_]+|[-_]+$/g, "");
}

/**
 * Normalise, deduplicate and bound a list of tags.
 *
 * @param tags - The raw tags.
 * @returns Up to twelve canonical tags in first appearance order.
 */
export function normaliseTags(tags: string[]): string[] {
  const result: string[] = [];
  for (const tag of tags) {
    const cleaned = normaliseTag(tag);
    if (cleaned && !result.includes(cleaned)) result.push(cleaned);
    if (result.length === MAX_TAGS) break;
  }
  return result;
}

/**
 * Convert text into a URL friendly anchor.
 *
 * @param text - The raw text.
 * @returns The slug, or `section` for an empty value.
 */
export function slugify(text: string): string {
  const slug = text
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return slug || "section";
}

/**
 * Discover the distinct template variables in a body.
 *
 * @param body - The template source.
 * @returns Variable names in first appearance order.
 */
export function extractTemplateVariables(body: string): string[] {
  const names: string[] = [];
  for (const match of body.matchAll(VARIABLE_PATTERN)) {
    if (!names.includes(match[1])) names.push(match[1]);
  }
  return names;
}

/**
 * Substitute template variables with user supplied values.
 *
 * Unknown placeholders are left intact so the user can see them.
 *
 * @param body - The template source.
 * @param variables - Values keyed by variable name.
 * @returns The rendered body.
 */
export function renderTemplate(
  body: string,
  variables: Record<string, string>,
): string {
  return body.replace(VARIABLE_PATTERN, (match, name: string) =>
    Object.prototype.hasOwnProperty.call(variables, name)
      ? variables[name]
      : match,
  );
}

/**
 * Escape every character that could introduce markup.
 *
 * @param value - The raw text.
 * @returns HTML-safe text.
 */
export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Apply inline formatting to an already escaped line.
 *
 * @param escaped - An HTML-escaped line of text.
 * @returns The formatted line.
 */
function renderInline(escaped: string): string {
  let text = escaped;
  text = text.replace(
    /`([^`]+)`/g,
    (_match, code: string) => `<code>${code}</code>`,
  );
  text = text.replace(
    /\*\*([^*]+)\*\*/g,
    (_match, bold: string) => `<strong>${bold}</strong>`,
  );
  text = text.replace(
    /\*([^*]+)\*/g,
    (_match, emphasis: string) => `<em>${emphasis}</em>`,
  );
  text = text.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    (_match, label: string, rawUrl: string) => {
      const url = rawUrl.replace(/&amp;/g, "&");
      if (!SAFE_URL_PATTERN.test(url)) return `${label} (${rawUrl})`;
      return `<a href="${escapeHtml(url)}" rel="noopener noreferrer">${label}</a>`;
    },
  );
  return text;
}

/**
 * Render a note body as HTML-safe preview markup.
 *
 * The input is escaped before any formatting is applied. Only the tags
 * generated by this function are emitted verbatim.
 *
 * @param markdown - The note body.
 * @returns The preview HTML string.
 */
export function renderMarkdownish(markdown: string): string {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
  const blocks: string[] = [];
  let paragraph: string[] = [];
  let code: string[] = [];
  let inFence = false;
  let language = "";

  const flush = (): void => {
    if (paragraph.length === 0) return;
    blocks.push(`<p>${paragraph.map(renderInline).join("<br />")}</p>`);
    paragraph = [];
  };

  for (const line of lines) {
    const fence = FENCE_PATTERN.exec(line);
    if (fence) {
      if (inFence) {
        const attribute = language ? ` class="language-${language}"` : "";
        blocks.push(
          `<pre><code${attribute}>${escapeHtml(code.join("\n"))}</code></pre>`,
        );
        code = [];
        language = "";
        inFence = false;
      } else {
        flush();
        language = fence[2]
          .trim()
          .toLowerCase()
          .replace(/[^a-z0-9+-]/g, "");
        inFence = true;
      }
      continue;
    }
    if (inFence) {
      code.push(line);
      continue;
    }
    const heading = HEADING_PATTERN.exec(line);
    if (heading) {
      flush();
      const level = heading[1].length;
      const anchor = slugify(heading[2].replace(/[#*_`]/g, ""));
      blocks.push(
        `<h${level} id="${anchor}">${renderInline(heading[2].trim())}</h${level}>`,
      );
      continue;
    }
    if (/^>\s?/.test(line)) {
      flush();
      blocks.push(
        `<blockquote>${renderInline(line.replace(/^>\s?/, ""))}</blockquote>`,
      );
      continue;
    }
    if (LIST_PATTERN.test(line)) {
      flush();
      blocks.push(`<li>${renderInline(line.replace(LIST_PATTERN, ""))}</li>`);
      continue;
    }
    if (/^\s*$/.test(line)) {
      flush();
      continue;
    }
    paragraph.push(escapeHtml(line));
  }
  if (inFence) {
    blocks.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`);
  }
  flush();
  return blocks.join("\n");
}

/**
 * Apply the search and tag filters to a list of notes locally.
 *
 * @param notes - The notes to filter.
 * @param query - A case-insensitive text query.
 * @param tags - Tags that must all be present.
 * @returns The matching notes.
 */
export function filterNotes(
  notes: NoteEntry[],
  query: string,
  tags: string[],
): NoteEntry[] {
  const needle = query.trim().toLowerCase();
  const wanted = normaliseTags(tags);
  return notes.filter((note) => {
    if (needle) {
      const haystack =
        `${note.title} ${note.body} ${note.tags.join(" ")}`.toLowerCase();
      if (!haystack.includes(needle)) return false;
    }
    return wanted.every((tag) =>
      note.tags.some((item) => normaliseTag(item) === tag),
    );
  });
}

/**
 * Collect every distinct tag used by a set of notes.
 *
 * @param notes - The notes to inspect.
 * @returns The sorted tags.
 */
export function collectTags(notes: NoteEntry[]): string[] {
  const tags = new Set<string>();
  for (const note of notes) {
    for (const tag of note.tags) tags.add(normaliseTag(tag));
  }
  return [...tags].filter(Boolean).sort((a, b) => a.localeCompare(b));
}

/**
 * Build an empty note draft.
 *
 * @returns The blank draft.
 */
export function emptyDraft(): NoteDraft {
  return { title: "", body: "", format: "markdown", tags: [], pinned: false };
}

/**
 * Build a draft from an existing note.
 *
 * @param note - The note to edit.
 * @returns The initialised draft.
 */
export function draftFromNote(note: NoteEntry): NoteDraft {
  return {
    title: note.title,
    body: note.body,
    format: note.format,
    tags: [...note.tags],
    pinned: note.pinned,
  };
}

/**
 * Validate a draft before it is saved.
 *
 * @param draft - The draft to validate.
 * @returns An error message, or `null` when the draft is valid.
 */
export function validateDraft(draft: NoteDraft): string | null {
  if (!draft.title.trim()) return "A title is required";
  if (!draft.body.trim()) return "A body is required";
  if (draft.title.trim().length > MAX_TITLE_LENGTH)
    return "The title is too long";
  if (draft.body.trim().length > MAX_BODY_LENGTH) return "The body is too long";
  return null;
}

/**
 * Translate a save state into its visible label.
 *
 * @param state - The current save state.
 * @returns The label shown in the meta bar.
 */
export function saveStateLabel(state: SaveState): string {
  switch (state) {
    case "saved":
      return "Saved";
    case "unsaved":
      return "Unsaved";
    case "saving":
      return "Saving";
    case "error":
      return "Save failed";
  }
}

/**
 * Format a word-level change summary.
 *
 * @param added - The number of inserted words.
 * @param removed - The number of deleted words.
 * @returns A compact diff label.
 */
export function formatChangeSummary(added: number, removed: number): string {
  if (added === 0 && removed === 0) return "No content change";
  const parts: string[] = [];
  if (added > 0) parts.push(`+${added}`);
  if (removed > 0) parts.push(`-${removed}`);
  return parts.join(" ");
}
