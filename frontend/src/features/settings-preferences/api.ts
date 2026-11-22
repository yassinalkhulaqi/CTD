import { del as _del, get, post, put } from "../../api/client";
import type {
  ImportExportResponse,
  LayoutResponse,
  PreferencesResponse,
  ResetResponse,
  ThemeResponse,
} from "./types";

void _del;

export function getPreferences(
  userId = "default",
): Promise<PreferencesResponse> {
  return get<PreferencesResponse>(
    `/api/preferences?user_id=${encodeURIComponent(userId)}`,
  );
}

export function updatePreferences(
  userId: string,
  values: Record<string, unknown>,
): Promise<PreferencesResponse> {
  return put<PreferencesResponse>("/api/preferences", {
    user_id: userId,
    values,
  });
}

export function getTheme(): Promise<ThemeResponse> {
  return get<ThemeResponse>("/api/preferences/theme");
}

export function updateTheme(
  tokens: Record<string, string>,
): Promise<ThemeResponse> {
  return put<ThemeResponse>("/api/preferences/theme", { tokens });
}

export function getLayout(userId = "default"): Promise<LayoutResponse> {
  return get<LayoutResponse>(
    `/api/preferences/layout?user_id=${encodeURIComponent(userId)}`,
  );
}

export function updateLayout(
  userId: string,
  patch: Partial<Omit<LayoutResponse, "user_id" | "updated_at">>,
): Promise<LayoutResponse> {
  return put<LayoutResponse>("/api/preferences/layout", {
    user_id: userId,
    ...patch,
  });
}

export function resetPreferences(userId = "default"): Promise<ResetResponse> {
  return post<ResetResponse>("/api/preferences/reset", { user_id: userId });
}

export function exportConfig(
  userId = "default",
): Promise<ImportExportResponse> {
  return get<ImportExportResponse>(
    `/api/preferences/import?user_id=${encodeURIComponent(userId)}`,
  );
}

export function importConfig(
  userId: string,
  config: Record<string, unknown>,
): Promise<ImportExportResponse> {
  return post<ImportExportResponse>("/api/preferences/import", {
    user_id: userId,
    config,
  });
}
