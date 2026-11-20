/** Tests for the typed i18n API adapter. */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { get, post, put } from "../../api/client";
import { i18nApi } from "./api";

vi.mock("../../api/client", async () => {
  const actual = (await vi.importActual("../../api/client")) as Record<
    string,
    unknown
  >;
  return { ...actual, get: vi.fn(), post: vi.fn(), put: vi.fn() };
});

const mockedGet = vi.mocked(get);
const mockedPost = vi.mocked(post);
const mockedPut = vi.mocked(put);

describe("i18nApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists locales and registers new ones", async () => {
    mockedGet.mockResolvedValue([]);
    await expect(i18nApi.listLocales()).resolves.toEqual([]);
    expect(mockedGet).toHaveBeenCalledWith("/api/i18n/locales", undefined);

    const locale = { code: "fr", name: "French" };
    mockedPost.mockResolvedValue(locale);
    await expect(
      i18nApi.createLocale({ code: "fr", name: "French" }),
    ).resolves.toBe(locale);
    expect(mockedPost).toHaveBeenCalledWith(
      "/api/i18n/locales",
      { code: "fr", name: "French" },
      undefined,
    );
  });

  it("encodes message filters and batches", async () => {
    mockedGet.mockResolvedValue([]);
    await i18nApi.listMessages({ locale: "fr", namespace: "ui" });
    expect(mockedGet).toHaveBeenCalledWith(
      "/api/i18n/messages?locale=fr&namespace=ui",
      undefined,
    );

    mockedPut.mockResolvedValue([]);
    await i18nApi.upsertMessages({
      locale: "fr",
      namespace: "ui",
      messages: { greeting: "Bonjour" },
    });
    expect(mockedPut).toHaveBeenCalledWith(
      "/api/i18n/messages",
      { locale: "fr", namespace: "ui", messages: { greeting: "Bonjour" } },
      undefined,
    );
  });

  it("encodes translation values as JSON", async () => {
    mockedGet.mockResolvedValue({ value: "Hi Ada" });
    const result = await i18nApi.translate({
      locale: "en",
      namespace: "ui",
      key: "greeting",
      count: 1,
      values: { name: "Ada" },
    });
    expect(result.value).toBe("Hi Ada");
    const url = mockedGet.mock.calls[0][0];
    expect(url).toContain("/api/i18n/translate?");
    expect(url).toContain("count=1");
    expect(url).toContain("values=");
    expect(decodeURIComponent(url)).toContain('{"name":"Ada"}');
  });

  it("builds format, completeness and missing key queries", async () => {
    mockedGet.mockResolvedValue([]);
    await i18nApi.format({
      locale: "en",
      kind: "date",
      value: "2026-11-20",
      pattern: "YYYY",
    });
    expect(mockedGet.mock.calls[0][0]).toContain("kind=date");

    await i18nApi.completeness("fr");
    expect(mockedGet.mock.calls[1][0]).toBe(
      "/api/i18n/completeness?reference=fr",
    );

    await i18nApi.missingKeys("ar", "ui");
    expect(mockedGet.mock.calls[2][0]).toBe(
      "/api/i18n/missing-keys?locale=ar&namespace=ui",
    );
  });

  it("exposes direction, parse, rule and catalog endpoints", async () => {
    mockedGet.mockResolvedValue({});
    await i18nApi.direction("ar");
    expect(mockedGet.mock.calls[0][0]).toBe("/api/i18n/direction?locale=ar");
    await i18nApi.parse("zh-Hant-TW");
    expect(mockedGet.mock.calls[1][0]).toBe(
      "/api/i18n/parse?locale=zh-Hant-TW",
    );
    await i18nApi.listFormatRules();
    expect(mockedGet.mock.calls[2][0]).toBe("/api/i18n/format-rules");
    await i18nApi.catalog();
    expect(mockedGet.mock.calls[3][0]).toBe("/api/i18n/catalog");

    mockedPut.mockResolvedValue({ locale: "en" });
    await i18nApi.upsertFormatRule({
      locale: "en",
      number_pattern: "#,##0",
      date_pattern: "YYYY-MM-DD",
    });
    expect(mockedPut).toHaveBeenCalled();
  });
});
