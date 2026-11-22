export type Density = "compact" | "comfortable";
export type SidebarPosition = "left" | "right";
export type ThemeMode = "system" | "light" | "dark";

export interface PreferenceSchemaField {
  key: string;
  value_type: "boolean" | "string" | "integer" | "enum";
  default: unknown;
  label: string;
  description: string;
  choices: string[];
  min_value: number | null;
  max_value: number | null;
}

export interface PreferencesResponse {
  user_id: string;
  values: Record<string, unknown>;
  defaults: Record<string, unknown>;
  schema_fields: PreferenceSchemaField[];
}

export interface ThemeContrast {
  foreground: string;
  background: string;
  ratio: number;
  passes_aa: boolean;
}

export interface ThemeResponse {
  tokens: Record<string, string>;
  contrast: ThemeContrast[];
  passes: boolean;
}

export interface LayoutResponse {
  user_id: string;
  density: Density;
  sidebar_position: SidebarPosition;
  show_activity: boolean;
  timezone: string;
  date_format: string;
  updated_at: string;
}

export interface ImportExportResponse {
  version: number;
  user_id: string;
  preferences: Record<string, unknown>;
  theme: Record<string, string>;
  layout: LayoutResponse;
}

export interface ResetResponse {
  preferences: Record<string, unknown>;
  layout: LayoutResponse;
  theme: ThemeResponse;
}

export interface SaveState {
  status: "idle" | "saving" | "saved" | "error";
  message: string;
}
