/** Types shared by the languages feature. */

export type TextDirection = "ltr" | "rtl";

export type PluralRule = "none" | "simple" | "slavic" | "arabic";

export type PluralCategory = "zero" | "one" | "two" | "few" | "many" | "other";

export type TranslationSource =
  "exact" | "plural" | "base" | "default" | "missing";

export type FormatKind = "number" | "date";

export type CompletenessTone = "success" | "warning" | "danger";

/** A registered locale returned by the API. */
export interface Locale {
  code: string;
  name: string;
  direction: TextDirection;
  plural_rules: PluralRule;
  base_language: string;
  canonical_code: string;
  is_rtl: boolean;
  chain: string[];
}

/** A catalogue message returned by the API. */
export interface Message {
  id: string;
  locale: string;
  namespace: string;
  key: string;
  value: string;
  qualified_key: string;
  placeholders: string[];
  is_empty: boolean;
}

/** The resolved value of a translation request. */
export interface TranslationResult {
  key: string;
  locale: string;
  resolved_locale: string;
  value: string;
  display_value: string;
  source: TranslationSource;
  variant: string;
  found: boolean;
  used_fallback: boolean;
  interpolated: boolean;
  complete: boolean;
  missing: string[];
  applied: string[];
  plural_category: PluralCategory | null;
}

/** A formatted number or date. */
export interface FormatResult {
  locale: string;
  kind: FormatKind;
  input: string;
  output: string;
  pattern: string;
  changed: boolean;
}

/** Translation completeness of one locale and namespace. */
export interface CompletenessStat {
  locale: string;
  namespace: string;
  reference: string;
  total: number;
  translated: number;
  missing: number;
  missing_keys: string[];
  percent: number;
  is_complete: boolean;
}

/** A reference key that has not been translated. */
export interface MissingKey {
  locale: string;
  namespace: string;
  key: string;
  qualified_key: string;
  reference_value: string;
  resolved_locale: string | null;
  has_fallback: boolean;
}

/** Formatting patterns attached to a locale. */
export interface FormatRule {
  locale: string;
  number_pattern: string;
  date_pattern: string;
  number_example: string;
  date_example: string;
}

/** Writing direction information. */
export interface DirectionInfo {
  locale: string;
  base_language: string;
  direction: TextDirection;
  is_rtl: boolean;
  chain: string[];
}

/** A compact catalogue overview. */
export interface CatalogInfo {
  locale_count: number;
  message_count: number;
  rtl_codes: string[];
  namespaces: string[];
  default_locale: string;
}

/** A locale prepared for rendering in a selector. */
export interface LocaleOption {
  code: string;
  label: string;
  direction: TextDirection;
  isRtl: boolean;
}

/** The parsed representation of a locale identifier. */
export interface LocaleCodeInfo {
  raw: string;
  canonical: string;
  base_language: string;
  script: string;
  region: string;
}

/** The result of rendering a message template. */
export interface InterpolationPreview {
  value: string;
  applied: string[];
  missing: string[];
  complete: boolean;
}

/** An editable message draft shown by the editor. */
export interface MessageDraft {
  locale: string;
  namespace: string;
  key: string;
  value: string;
}

/** A row of the completeness table with presentation helpers. */
export interface CompletenessRow extends CompletenessStat {
  tone: CompletenessTone;
  percentLabel: string;
}

/** Payload used to register a locale. */
export interface LocaleCreateInput {
  code: string;
  name: string;
  direction?: TextDirection;
  plural_rules?: PluralRule;
}

/** Payload used to replace messages of one namespace. */
export interface MessagesUpsertInput {
  locale: string;
  namespace: string;
  messages: Record<string, string>;
}

/** Query parameters of a translation request. */
export interface TranslateQuery {
  locale: string;
  namespace: string;
  key: string;
  count?: number;
  values?: Record<string, string | number>;
}

/** Query parameters of a formatting request. */
export interface FormatQuery {
  locale: string;
  kind: FormatKind;
  value: string;
  pattern?: string;
}

/** Payload used to store formatting rules. */
export interface FormatRuleInput {
  locale: string;
  number_pattern: string;
  date_pattern: string;
}

/** Filters accepted by the message list endpoint. */
export interface MessageFilters {
  locale?: string;
  namespace?: string;
}
