import {
  Button,
  ErrorState,
  Select,
  Skeleton,
  Switch,
} from "../../components/ui";
import { ImportExport } from "./components/ImportExport";
import { LayoutControls } from "./components/LayoutControls";
import { PreferenceSection } from "./components/PreferenceSection";
import { SaveBar } from "./components/SaveBar";
import { ThemePreview } from "./components/ThemePreview";
import { usePreferences } from "./hooks";
import styles from "./PreferencesPage.module.css";

function boolValue(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}
function strValue(value: unknown, fallback: string): string {
  return typeof value === "string" ? value : fallback;
}

export function PreferencesPage() {
  const state = usePreferences("default");
  const { preferences, theme, layout, draftValues, draftLayout } = state;

  if (state.loading) {
    return (
      <div className={styles.page}>
        <Skeleton width="100%" height={48} />
        <Skeleton width="100%" height={240} />
        <Skeleton width="100%" height={240} />
      </div>
    );
  }
  if (state.error && !preferences) {
    return (
      <div className={styles.page}>
        <ErrorState
          title="Failed to load preferences"
          message={state.error}
          onRetry={() => void state.reload()}
        />
      </div>
    );
  }
  if (!preferences || !theme || !layout) return null;

  const appearanceFields = preferences.schema_fields.filter((f) =>
    f.key.startsWith("appearance."),
  );
  const notificationFields = preferences.schema_fields.filter((f) =>
    f.key.startsWith("notifications."),
  );
  const workspaceFields = preferences.schema_fields.filter((f) =>
    f.key.startsWith("workspace."),
  );

  const renderField = (field: (typeof preferences.schema_fields)[number]) => {
    const value = draftValues[field.key] ?? field.default;
    if (field.value_type === "boolean") {
      return (
        <div key={field.key} className={styles.switchRow}>
          <Switch
            label={field.label}
            checked={boolValue(value, Boolean(field.default))}
            onChange={(e) => state.setDraftValue(field.key, e.target.checked)}
            aria-label={field.label}
          />
          <span className={styles.fieldHint}>{field.description}</span>
        </div>
      );
    }
    if (field.value_type === "enum") {
      return (
        <Select
          key={field.key}
          label={field.label}
          hint={field.description}
          id={`pref-${field.key}`}
          value={strValue(value, String(field.default))}
          options={field.choices.map((c) => ({ value: c, label: c }))}
          onChange={(e) => state.setDraftValue(field.key, e.target.value)}
        />
      );
    }
    return (
      <label
        key={field.key}
        className={styles.fieldBlock}
        htmlFor={`pref-${field.key}`}
      >
        <span className={styles.fieldLabel}>{field.label}</span>
        <input
          id={`pref-${field.key}`}
          className={styles.numberInput}
          type="number"
          min={field.min_value ?? undefined}
          max={field.max_value ?? undefined}
          value={typeof value === "number" ? value : Number(field.default)}
          onChange={(e) =>
            state.setDraftValue(field.key, Number(e.target.value))
          }
        />
        <span className={styles.fieldHint}>{field.description}</span>
      </label>
    );
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Preferences</h1>
          <p className={styles.subtitle}>
            Personalize appearance, workspace behavior, and notifications.
          </p>
        </div>
        <Button variant="secondary" onClick={() => void state.reset()}>
          Reset defaults
        </Button>
      </header>

      {state.error ? (
        <p className={styles.errorBanner} role="alert">
          {state.error}
        </p>
      ) : null}

      <div className={styles.grid}>
        <PreferenceSection
          title="Appearance"
          description="Theme mode, accent, and contrast preview."
        >
          <div className={styles.fields}>
            {appearanceFields.map(renderField)}
          </div>
          <ThemePreview tokens={theme.tokens} contrastPass={theme.passes} />
        </PreferenceSection>

        <PreferenceSection
          title="Workspace"
          description="Layout density, sidebar, timezone, and date format."
        >
          <LayoutControls
            layout={draftLayout}
            onChange={state.setDraftLayout}
          />
          <div className={styles.fields}>
            {workspaceFields.map(renderField)}
          </div>
        </PreferenceSection>

        <PreferenceSection
          title="Notifications"
          description="Control how and when updates reach you."
        >
          <div className={styles.fields}>
            {notificationFields.map(renderField)}
          </div>
        </PreferenceSection>

        <PreferenceSection
          title="Import / Export"
          description="Move your settings between environments."
        >
          <ImportExport
            onExport={state.exportJson}
            onImport={state.importJson}
          />
        </PreferenceSection>
      </div>

      <SaveBar
        dirty={state.dirty}
        saveState={state.saveState}
        onSave={state.save}
        onReset={state.reset}
      />
    </div>
  );
}

export default PreferencesPage;
