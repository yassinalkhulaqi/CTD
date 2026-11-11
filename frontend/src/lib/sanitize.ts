/**
 * Input sanitisation helpers shared by the dashboard forms.
 */

/** The maximum length accepted by the note editor. */
export const MAX_NOTE_LENGTH = 4_000;

/** The maximum length accepted by a flag. */
export const MAX_FLAG_LENGTH = 256;

/**
 * Remove the control characters that could break the rendering.
 *
 * @param value - The raw text.
 * @returns The cleaned text.
 */
export function stripControlCharacters(value: string): string {
  // eslint-disable-next-line no-control-regex
  return value.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");
}

/**
 * Normalise a note before it is sent to the API.
 *
 * @param value - The raw note.
 * @returns The normalised note.
 * @throws {Error} When the note is empty or too long.
 */
export function normaliseNote(value: string): string {
  const cleaned = stripControlCharacters(value).trim();
  if (!cleaned) {
    throw new Error("A note must not be empty");
  }
  if (cleaned.length > MAX_NOTE_LENGTH) {
    throw new Error(`A note must not exceed ${MAX_NOTE_LENGTH} characters`);
  }
  return cleaned;
}

/**
 * Normalise a flag before it is sent to the API.
 *
 * @param value - The raw flag.
 * @returns The normalised flag.
 * @throws {Error} When the flag is empty, too long or malformed.
 */
export function normaliseFlag(value: string): string {
  const cleaned = stripControlCharacters(value).trim();
  if (!cleaned) {
    throw new Error("A flag must not be empty");
  }
  if (cleaned.length > MAX_FLAG_LENGTH) {
    throw new Error(`A flag must not exceed ${MAX_FLAG_LENGTH} characters`);
  }
  if (!/^[A-Za-z0-9_]{1,32}\{[^{}]{1,200}\}$/.test(cleaned)) {
    throw new Error("A flag must look like prefix{content}");
  }
  return cleaned;
}

/**
 * Redact a flag so it can be displayed safely.
 *
 * @param value - The flag to redact.
 * @returns The redacted flag.
 */
export function redactFlag(value: string): string {
  const cleaned = value.trim();
  const separator = cleaned.indexOf("{");
  if (separator >= 0) {
    return `${cleaned.slice(0, separator)}{****}`;
  }
  if (cleaned.length <= 8) return "*".repeat(cleaned.length);
  return `${cleaned.slice(0, 4)}${"*".repeat(cleaned.length - 6)}${cleaned.slice(-2)}`;
}

/**
 * Escape the characters that carry a meaning inside a URL.
 *
 * @param value - The raw value.
 * @returns The encoded value.
 */
export function encodePathSegment(value: string): string {
  return encodeURIComponent(value);
}
