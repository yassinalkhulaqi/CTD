/** Typed HTTP adapter for the languages feature. */

import {
  buildQuery,
  get,
  post,
  put,
  type RequestOptions,
} from "../../api/client";
import type {
  CatalogInfo,
  CompletenessStat,
  DirectionInfo,
  FormatQuery,
  FormatResult,
  FormatRule,
  FormatRuleInput,
  Locale,
  LocaleCodeInfo,
  LocaleCreateInput,
  Message,
  MessageFilters,
  MessagesUpsertInput,
  MissingKey,
  TranslateQuery,
  TranslationResult,
} from "./types";

const BASE = "/api/i18n";

/**
 * Encode translation values for the query string.
 *
 * @param values - The placeholder values.
 * @returns A JSON string or `undefined` when there are no values.
 */
function encodeValues(
  values: Record<string, string | number> | undefined,
): string | undefined {
  if (!values || Object.keys(values).length === 0) return undefined;
  return JSON.stringify(values);
}

/** Endpoints exposed by the i18n API. */
export const i18nApi = {
  /**
   * List registered locales.
   *
   * @param options - Request options.
   * @returns The locales ordered by code.
   */
  listLocales(options?: RequestOptions): Promise<Locale[]> {
    return get<Locale[]>(`${BASE}/locales`, options);
  },

  /**
   * Register a locale.
   *
   * @param input - The locale details.
   * @param options - Request options.
   * @returns The registered locale.
   */
  createLocale(
    input: LocaleCreateInput,
    options?: RequestOptions,
  ): Promise<Locale> {
    return post<Locale>(`${BASE}/locales`, input, options);
  },

  /**
   * List catalogue messages with optional filters.
   *
   * @param filters - Locale and namespace filters.
   * @param options - Request options.
   * @returns The matching messages.
   */
  listMessages(
    filters?: MessageFilters,
    options?: RequestOptions,
  ): Promise<Message[]> {
    const query = buildQuery({
      locale: filters?.locale,
      namespace: filters?.namespace,
    });
    return get<Message[]>(`${BASE}/messages${query}`, options);
  },

  /**
   * Insert or replace messages in one namespace.
   *
   * @param input - The batch to store.
   * @param options - Request options.
   * @returns The stored messages.
   */
  upsertMessages(
    input: MessagesUpsertInput,
    options?: RequestOptions,
  ): Promise<Message[]> {
    return put<Message[]>(`${BASE}/messages`, input, options);
  },

  /**
   * Translate a key with fallback and interpolation.
   *
   * @param query - The translation query.
   * @param options - Request options.
   * @returns The resolved translation.
   */
  translate(
    query: TranslateQuery,
    options?: RequestOptions,
  ): Promise<TranslationResult> {
    const search = buildQuery({
      locale: query.locale,
      namespace: query.namespace,
      key: query.key,
      count: query.count,
      values: encodeValues(query.values),
    });
    return get<TranslationResult>(`${BASE}/translate${search}`, options);
  },

  /**
   * Format a number or a date.
   *
   * @param query - The formatting query.
   * @param options - Request options.
   * @returns The formatted value.
   */
  format(query: FormatQuery, options?: RequestOptions): Promise<FormatResult> {
    const search = buildQuery({
      locale: query.locale,
      kind: query.kind,
      value: query.value,
      pattern: query.pattern,
    });
    return get<FormatResult>(`${BASE}/format${search}`, options);
  },

  /**
   * Return translation completeness.
   *
   * @param reference - The reference locale code.
   * @param options - Request options.
   * @returns One stat per locale and namespace.
   */
  completeness(
    reference?: string,
    options?: RequestOptions,
  ): Promise<CompletenessStat[]> {
    return get<CompletenessStat[]>(
      `${BASE}/completeness${buildQuery({ reference })}`,
      options,
    );
  },

  /**
   * List untranslated reference keys.
   *
   * @param locale - The target locale.
   * @param namespace - An optional namespace filter.
   * @param options - Request options.
   * @returns The missing keys.
   */
  missingKeys(
    locale: string,
    namespace?: string,
    options?: RequestOptions,
  ): Promise<MissingKey[]> {
    const search = buildQuery({ locale, namespace });
    return get<MissingKey[]>(`${BASE}/missing-keys${search}`, options);
  },

  /**
   * Return writing direction information.
   *
   * @param locale - The locale identifier.
   * @param options - Request options.
   * @returns The direction details.
   */
  direction(locale: string, options?: RequestOptions): Promise<DirectionInfo> {
    return get<DirectionInfo>(
      `${BASE}/direction${buildQuery({ locale })}`,
      options,
    );
  },

  /**
   * Parse a locale identifier on the server.
   *
   * @param locale - The locale identifier.
   * @param options - Request options.
   * @returns The parsed components.
   */
  parse(locale: string, options?: RequestOptions): Promise<LocaleCodeInfo> {
    return get<LocaleCodeInfo>(
      `${BASE}/parse${buildQuery({ locale })}`,
      options,
    );
  },

  /**
   * List stored formatting rules.
   *
   * @param options - Request options.
   * @returns The stored rules.
   */
  listFormatRules(options?: RequestOptions): Promise<FormatRule[]> {
    return get<FormatRule[]>(`${BASE}/format-rules`, options);
  },

  /**
   * Store formatting rules for a locale.
   *
   * @param input - The patterns to store.
   * @param options - Request options.
   * @returns The stored rule.
   */
  upsertFormatRule(
    input: FormatRuleInput,
    options?: RequestOptions,
  ): Promise<FormatRule> {
    return put<FormatRule>(`${BASE}/format-rules`, input, options);
  },

  /**
   * Return the catalogue overview.
   *
   * @param options - Request options.
   * @returns The catalogue summary.
   */
  catalog(options?: RequestOptions): Promise<CatalogInfo> {
    return get<CatalogInfo>(`${BASE}/catalog`, options);
  },
};
