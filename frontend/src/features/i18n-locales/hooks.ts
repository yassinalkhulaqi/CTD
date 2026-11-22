/** Data loading hooks for the languages feature. */

import { useCallback } from "react";
import { queryKey } from "../../api/cache";
import { useMutation, useQuery } from "../../api";
import { i18nApi } from "./api";
import type {
  CompletenessStat,
  FormatRule,
  FormatRuleInput,
  Locale,
  LocaleCreateInput,
  Message,
  MessagesUpsertInput,
  MissingKey,
} from "./types";

const I18N_PREFIX = "i18n";

/**
 * Load the registered locales.
 *
 * @returns The locale query state.
 */
export function useLocales() {
  const fetcher = useCallback(
    (signal: AbortSignal) => i18nApi.listLocales({ signal }),
    [],
  );
  return useQuery<Locale[]>({
    key: queryKey("i18n:locales"),
    fetcher,
    staleTime: 30_000,
  });
}

/**
 * Load messages with optional filters.
 *
 * @param locale - Optional locale filter.
 * @param namespace - Optional namespace filter.
 * @returns The message query state.
 */
export function useMessages(locale?: string, namespace?: string) {
  const fetcher = useCallback(
    (signal: AbortSignal) =>
      i18nApi.listMessages({ locale, namespace }, { signal }),
    [locale, namespace],
  );
  return useQuery<Message[]>({
    key: queryKey("i18n:messages", {
      locale: locale ?? null,
      namespace: namespace ?? null,
    }),
    fetcher,
    staleTime: 15_000,
  });
}

/**
 * Load the completeness report.
 *
 * @param reference - The reference locale.
 * @returns The completeness query state.
 */
export function useCompleteness(reference = "en") {
  const fetcher = useCallback(
    (signal: AbortSignal) => i18nApi.completeness(reference, { signal }),
    [reference],
  );
  return useQuery<CompletenessStat[]>({
    key: queryKey("i18n:completeness", { reference }),
    fetcher,
    staleTime: 30_000,
  });
}

/**
 * Load the missing keys of a locale.
 *
 * @param locale - The target locale, or `null` to disable the query.
 * @param namespace - An optional namespace filter.
 * @returns The missing key query state.
 */
export function useMissingKeys(locale: string | null, namespace?: string) {
  const fetcher = useCallback(
    (signal: AbortSignal) =>
      i18nApi.missingKeys(locale ?? "", namespace, { signal }),
    [locale, namespace],
  );
  return useQuery<MissingKey[]>({
    key: locale
      ? queryKey("i18n:missing", { locale, namespace: namespace ?? null })
      : null,
    fetcher,
    staleTime: 30_000,
  });
}

/**
 * Load the stored formatting rules.
 *
 * @returns The format rule query state.
 */
export function useFormatRules() {
  const fetcher = useCallback(
    (signal: AbortSignal) => i18nApi.listFormatRules({ signal }),
    [],
  );
  return useQuery<FormatRule[]>({
    key: queryKey("i18n:format-rules"),
    fetcher,
    staleTime: 30_000,
  });
}

/**
 * Return the mutation used to register a locale.
 *
 * @returns The create locale mutation.
 */
export function useCreateLocale() {
  return useMutation<LocaleCreateInput, Locale>({
    mutationFn: (input) => i18nApi.createLocale(input),
    invalidatesPrefixes: [I18N_PREFIX],
  });
}

/**
 * Return the mutation used to upsert messages.
 *
 * @returns The upsert mutation.
 */
export function useUpsertMessages() {
  return useMutation<MessagesUpsertInput, Message[]>({
    mutationFn: (input) => i18nApi.upsertMessages(input),
    invalidatesPrefixes: [I18N_PREFIX],
  });
}

/**
 * Return the mutation used to store formatting rules.
 *
 * @returns The format rule mutation.
 */
export function useUpdateFormatRule() {
  return useMutation<FormatRuleInput, FormatRule>({
    mutationFn: (input) => i18nApi.upsertFormatRule(input),
    invalidatesPrefixes: [I18N_PREFIX],
  });
}
