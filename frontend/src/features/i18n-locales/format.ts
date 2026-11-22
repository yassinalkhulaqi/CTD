/**
 * Pure locale utilities shared by the languages screens.
 *
 * These helpers mirror the backend rules so the formatting playground can
 * render an instant preview without waiting for a round trip.
 */

import type {
  CompletenessTone,
  InterpolationPreview,
  LocaleCodeInfo,
  PluralCategory,
  PluralRule,
  TextDirection,
} from "./types";

const RTL_LANGUAGES = new Set([
  "ar",
  "arc",
  "ckb",
  "dv",
  "fa",
  "he",
  "ku",
  "ps",
  "sd",
  "ug",
  "ur",
  "yi",
]);

const MONTHS: Record<string, string[]> = {
  en: [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ],
  fr: [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
  ],
  de: [
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
  ],
};

const DEFAULT_FORMATS: Record<string, [string, string]> = {
  en: ["#,##0.00", "MM/DD/YYYY"],
  fr: ["#,##0.00", "DD/MM/YYYY"],
  de: ["#,##0.00", "DD.MM.YYYY"],
  ar: ["#,##0.00", "DD/MM/YYYY"],
  ja: ["#,##0", "YYYY/MM/DD"],
  zh: ["#,##0", "YYYY/MM/DD"],
};

const DEFAULT_NUMBER_PATTERN = "#,##0.00";
const DEFAULT_DATE_PATTERN = "YYYY-MM-DD";

/**
 * Parse a locale identifier into its components.
 *
 * @param code - A BCP-47 style identifier such as `zh-Hant-TW`.
 * @returns The parsed components.
 * @throws Error when the identifier is malformed.
 */
export function parseLocaleCode(code: string): LocaleCodeInfo {
  const raw = code.trim();
  if (!/^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$/.test(raw)) {
    throw new Error(`Invalid locale code: ${code}`);
  }
  const parts = raw.split("-");
  let script = "";
  let region = "";
  for (const part of parts.slice(1)) {
    if (/^[A-Za-z]{4}$/.test(part)) {
      script = part.toLowerCase();
    } else if (/^[A-Za-z]{2}$/.test(part)) {
      region = part.toLowerCase();
    } else if (/^[0-9]{3}$/.test(part)) {
      region = part;
    } else {
      throw new Error(`Invalid locale subtag: ${part}`);
    }
  }
  const language = parts[0].toLowerCase();
  const canonicalParts = [language];
  if (script)
    canonicalParts.push(script.charAt(0).toUpperCase() + script.slice(1));
  if (region)
    canonicalParts.push(region.length === 2 ? region.toUpperCase() : region);
  return {
    raw,
    canonical: canonicalParts.join("-"),
    base_language: language,
    script,
    region,
  };
}

/**
 * Return whether a locale identifier is syntactically valid.
 *
 * @param code - The candidate identifier.
 * @returns `true` when the identifier can be parsed.
 */
export function isValidLocaleCode(code: string): boolean {
  try {
    parseLocaleCode(code);
    return true;
  } catch {
    return false;
  }
}

/**
 * Return the primary language subtag of a locale.
 *
 * @param code - The locale identifier.
 * @returns The lowercase language subtag.
 */
export function baseLanguage(code: string): string {
  return parseLocaleCode(code).base_language;
}

/**
 * Return whether a locale is written right to left.
 *
 * @param code - The locale identifier.
 * @returns `true` for RTL languages.
 */
export function isRtlLocale(code: string): boolean {
  return RTL_LANGUAGES.has(baseLanguage(code));
}

/**
 * Return the writing direction of a locale.
 *
 * @param code - The locale identifier.
 * @returns `ltr` or `rtl`.
 */
export function directionFor(code: string): TextDirection {
  return isRtlLocale(code) ? "rtl" : "ltr";
}

/**
 * Build the fallback chain of a locale.
 *
 * @param code - The requested locale.
 * @param fallback - The final fallback locale.
 * @returns The ordered, de-duplicated chain.
 */
export function fallbackChain(code: string, fallback = "en"): string[] {
  const parsed = parseLocaleCode(code);
  const candidates = [
    parsed.raw,
    parsed.base_language,
    fallback.trim().toLowerCase(),
  ];
  const seen = new Set<string>();
  const result: string[] = [];
  for (const candidate of candidates) {
    const key = candidate.toLowerCase();
    if (candidate && !seen.has(key)) {
      seen.add(key);
      result.push(candidate);
    }
  }
  return result;
}

/**
 * Return the plural category selected by a rule for a count.
 *
 * @param rule - The plural rule family.
 * @param count - The item count.
 * @returns The selected category.
 */
export function pluralCategory(
  rule: PluralRule,
  count: number,
): PluralCategory {
  const value = Math.abs(Math.trunc(count));
  if (rule === "none") return "other";
  if (rule === "simple") return value === 1 ? "one" : "other";
  if (rule === "arabic") {
    const lastTwo = value % 100;
    if (value === 0) return "zero";
    if (lastTwo === 1) return "one";
    if (lastTwo === 2) return "two";
    if (lastTwo >= 3 && lastTwo <= 10) return "few";
    if (lastTwo >= 11 && lastTwo <= 99) return "many";
    return "other";
  }
  const lastDigit = value % 10;
  const lastTwo = value % 100;
  if (lastDigit === 1 && lastTwo !== 11) return "one";
  if (lastDigit >= 2 && lastDigit <= 4 && (lastTwo < 12 || lastTwo > 14))
    return "few";
  return "many";
}

/**
 * Return the message key of a plural variant.
 *
 * @param key - The base key.
 * @param category - The plural category.
 * @returns The suffixed key.
 */
export function pluralKey(key: string, category: PluralCategory): string {
  return `${key}.${category}`;
}

/**
 * Extract placeholder names from a template.
 *
 * @param template - The message template.
 * @returns Unique names in first-seen order.
 */
export function extractPlaceholders(template: string): string[] {
  const names: string[] = [];
  const pattern = /(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})/g;
  let match = pattern.exec(template);
  while (match !== null) {
    if (!names.includes(match[1])) names.push(match[1]);
    match = pattern.exec(template);
  }
  return names;
}

/**
 * Render a message template with placeholder values.
 *
 * @param template - The message template.
 * @param values - The values keyed by placeholder name.
 * @returns The rendered text and substitution details.
 */
export function interpolate(
  template: string,
  values: Record<string, string | number> = {},
): InterpolationPreview {
  const applied: string[] = [];
  const missing: string[] = [];
  const rendered = template.replace(
    /(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})/g,
    (token, name: string) => {
      if (Object.prototype.hasOwnProperty.call(values, name)) {
        if (!applied.includes(name)) applied.push(name);
        return String(values[name]);
      }
      if (!missing.includes(name)) missing.push(name);
      return token;
    },
  );
  return {
    value: rendered.replace(/\{\{|\}\}/g, (token) =>
      token === "{{" ? "{" : "}",
    ),
    applied,
    missing,
    complete: missing.length === 0,
  };
}

/**
 * Validate a `#,##0.00` style number pattern.
 *
 * @param pattern - The candidate pattern.
 * @returns The trimmed pattern.
 * @throws Error when the pattern is invalid.
 */
export function validateNumberPattern(pattern: string): string {
  const candidate = pattern.trim();
  if (!/^[#,0]+(?:\.0+)?$/.test(candidate) || !candidate.includes("0")) {
    throw new Error(`Invalid number pattern: ${pattern}`);
  }
  return candidate;
}

/**
 * Format a number using half-away-from-zero rounding.
 *
 * @param value - The number to format.
 * @param pattern - The number pattern.
 * @returns The formatted string.
 */
export function formatNumber(value: number, pattern: string): string {
  const validated = validateNumberPattern(pattern);
  const decimals = validated.includes(".") ? validated.split(".")[1].length : 0;
  const factor = 10 ** decimals;
  const absolute = Math.abs(value) * factor;
  const rounded = Math.floor(absolute + 0.5) / factor;
  const signed = value < 0 ? -rounded : rounded;
  const fixed = Math.abs(signed).toFixed(decimals);
  const grouped = validated.includes(",");
  const body = grouped ? fixed.replace(/\B(?=(\d{3})+(?!\d))/g, ",") : fixed;
  return signed < 0 ? `-${body}` : body;
}

/**
 * Validate a date pattern.
 *
 * @param pattern - The candidate pattern.
 * @returns The trimmed pattern.
 * @throws Error when the pattern contains unsupported tokens.
 */
export function validateDatePattern(pattern: string): string {
  const candidate = pattern.trim();
  if (!candidate) throw new Error("Date pattern must not be empty");
  const remainder = candidate.replace(/YYYY|YY|MMMM|MMM|MM|DD|[^A-Za-z]/g, "");
  if (remainder) throw new Error(`Unsupported date token: ${remainder}`);
  return candidate;
}

/**
 * Return a localised month name.
 *
 * @param locale - The locale used for month names.
 * @param month - The month number from 1 to 12.
 * @param abbreviated - Whether to abbreviate the name.
 * @returns The month name.
 */
export function monthName(
  locale: string,
  month: number,
  abbreviated = false,
): string {
  const names = MONTHS[baseLanguage(locale)] ?? MONTHS.en;
  const name = names[Math.min(11, Math.max(0, month - 1))];
  return abbreviated ? name.slice(0, 3) : name;
}

/**
 * Format an ISO date string using pattern tokens.
 *
 * @param value - An ISO date such as `2026-11-20`.
 * @param pattern - The date pattern.
 * @param locale - The locale used for month names.
 * @returns The formatted date.
 * @throws Error when the input date or pattern is invalid.
 */
export function formatDate(
  value: string,
  pattern: string,
  locale = "en",
): string {
  const validated = validateDatePattern(pattern);
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value.trim());
  if (!match) throw new Error(`Invalid date: ${value}`);
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    throw new Error(`Invalid date: ${value}`);
  }
  return validated.replace(/YYYY|YY|MMMM|MMM|MM|DD/g, (token) => {
    switch (token) {
      case "YYYY":
        return String(year).padStart(4, "0");
      case "YY":
        return String(year % 100).padStart(2, "0");
      case "MMMM":
        return monthName(locale, month);
      case "MMM":
        return monthName(locale, month, true);
      case "MM":
        return String(month).padStart(2, "0");
      default:
        return String(day).padStart(2, "0");
    }
  });
}

/**
 * Return the default formatting patterns of a locale.
 *
 * @param locale - The locale identifier.
 * @returns A tuple of number and date patterns.
 */
export function defaultFormatRule(locale: string): [string, string] {
  const language = baseLanguage(locale);
  return (
    DEFAULT_FORMATS[language] ?? [DEFAULT_NUMBER_PATTERN, DEFAULT_DATE_PATTERN]
  );
}

/**
 * Return the completeness percentage rounded to one decimal.
 *
 * @param translated - The number of translated keys.
 * @param total - The number of reference keys.
 * @returns A percentage between 0 and 100.
 */
export function completenessPercent(translated: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((translated / total) * 1000) / 10;
}

/**
 * Map a completeness percentage onto a semantic tone.
 *
 * @param percent - The completeness percentage.
 * @returns The tone used by the completeness badge.
 */
export function completenessTone(percent: number): CompletenessTone {
  if (percent >= 90) return "success";
  if (percent >= 50) return "warning";
  return "danger";
}

/**
 * Build the options shown by the language switcher.
 *
 * @param locales - Registered locale objects.
 * @returns Sorted selector options.
 */
export function toLocaleOptions(
  locales: Array<{ code: string; name: string }>,
): Array<{
  code: string;
  label: string;
  direction: TextDirection;
  isRtl: boolean;
}> {
  return locales
    .map((locale) => ({
      code: locale.code,
      label: `${locale.name} (${locale.code})`,
      direction: directionFor(locale.code),
      isRtl: isRtlLocale(locale.code),
    }))
    .sort((a, b) => a.code.localeCompare(b.code));
}

/**
 * Normalise a user supplied message key.
 *
 * @param raw - The raw key text.
 * @returns The trimmed key with spaces replaced by hyphens.
 */
export function normalizeKey(raw: string): string {
  return raw.trim().replace(/\s+/g, "-");
}
