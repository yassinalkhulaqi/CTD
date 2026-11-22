import styles from "../PreferencesPage.module.css";

interface Props {
  tokens: Record<string, string>;
  contrastPass: boolean;
}

export function ThemePreview({ tokens, contrastPass }: Props) {
  return (
    <div
      className={styles.themePreview}
      style={{
        background: tokens.surface,
        color: tokens.textPrimary,
        borderColor: tokens.surfaceMuted,
      }}
    >
      <div
        className={styles.previewHeader}
        style={{ background: tokens.surfaceMuted }}
      >
        <span>Theme preview</span>
        <span className={contrastPass ? styles.pass : styles.fail}>
          {contrastPass ? "AA pass" : "AA fail"}
        </span>
      </div>
      <div className={styles.previewBody}>
        <p style={{ color: tokens.textPrimary }}>Primary text sample</p>
        <p style={{ color: tokens.textMuted }}>
          Muted text sample for readability checks.
        </p>
        <button
          type="button"
          className={styles.previewButton}
          style={{ background: tokens.accent, color: tokens.accentText }}
        >
          Accent action
        </button>
      </div>
    </div>
  );
}
