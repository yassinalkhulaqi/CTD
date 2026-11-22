import { useCallback, useState } from "react";
import { AlertTriangle, Accessibility, Keyboard, Route } from "lucide-react";
import {
  Card,
  CardContent,
  ErrorState,
  Skeleton,
  StatCard,
} from "../../components/ui";
import { accessibilityApi } from "./api";
import { ContrastChecker } from "./components/ContrastChecker";
import { FocusOrderMap } from "./components/FocusOrderMap";
import { IssueList } from "./components/IssueList";
import { MotionControls } from "./components/MotionControls";
import { ShortcutEditor } from "./components/ShortcutEditor";
import { SkipLinkDemo } from "./components/SkipLinkDemo";
import { useAccessibilityData } from "./hooks";
import type {
  A11yIssue,
  ContrastAudit,
  ContrastAuditPayload,
  FocusOrderEntry,
  MotionPreferences,
  Shortcut,
  ShortcutCreatePayload,
} from "./types";
import styles from "./AccessibilityPage.module.css";

export function AccessibilityPage() {
  const { issues, shortcuts, focusEntries, stats, loading, error, reload } =
    useAccessibilityData();
  const [motion, setMotion] = useState<MotionPreferences>({
    reducedMotion: false,
    highContrast: false,
  });
  const [status, setStatus] = useState("Accessibility workspace ready.");

  const handleAudit = useCallback(
    async (payload: ContrastAuditPayload): Promise<ContrastAudit> => {
      const result = await accessibilityApi.auditContrast(payload);
      setStatus(
        `Audited ${result.pairs.length} pair(s); ${result.failures} failure(s) found.`,
      );
      if (payload.record_issue) reload();
      return result;
    },
    [reload],
  );

  const handleResolve = useCallback(
    async (issueId: string): Promise<A11yIssue> => {
      const resolved = await accessibilityApi.resolveIssue(issueId);
      setStatus(`Resolved ${resolved.rule_id} on ${resolved.path}.`);
      return resolved;
    },
    [],
  );

  const handleRegister = useCallback(
    async (payload: ShortcutCreatePayload): Promise<Shortcut> => {
      const created = await accessibilityApi.registerShortcut(payload);
      setStatus(`Registered ${created.display_keys}.`);
      reload();
      return created;
    },
    [reload],
  );

  const handleDelete = useCallback(
    async (shortcutId: string): Promise<void> => {
      await accessibilityApi.deleteShortcut(shortcutId);
      setStatus("Shortcut removed.");
      reload();
    },
    [reload],
  );

  const handleReorder = useCallback(
    async (ids: string[]): Promise<FocusOrderEntry[]> => {
      const ordered = await accessibilityApi.reorderFocusEntries(ids);
      setStatus("Focus order saved.");
      return ordered;
    },
    [],
  );

  return (
    <div
      className={styles.page}
      data-reduced-motion={motion.reducedMotion}
      data-high-contrast={motion.highContrast}
    >
      <SkipLinkDemo />

      <header className={styles.header}>
        <div>
          <span className={styles.eyebrow}>Settings / Accessibility</span>
          <h1 id="accessibility-heading">Accessibility toolkit</h1>
          <p>
            Audit contrast, resolve barriers, rehearse keyboard paths and
            preview motion preferences without leaving this page.
          </p>
        </div>
        <div className={styles.risk}>
          <AlertTriangle aria-hidden="true" size={18} />
          <span>Risk score</span>
          <strong>{stats.risk_score}</strong>
        </div>
      </header>

      <section className={styles.stats} aria-label="Accessibility summary">
        <StatCard
          label="Open issues"
          value={stats.open_issues}
          meta={`${stats.critical_open} critical`}
          icon={<AlertTriangle size={18} />}
          accent="var(--danger-base)"
          loading={loading}
        />
        <StatCard
          label="Shortcut bindings"
          value={stats.shortcut_count}
          meta={`${stats.scopes.length} scope(s)`}
          icon={<Keyboard size={18} />}
          accent="var(--accent-base)"
          loading={loading}
        />
        <StatCard
          label="Focus stops"
          value={stats.focus_entry_count}
          meta="Traversable with Tab"
          icon={<Route size={18} />}
          accent="var(--info-base)"
          loading={loading}
        />
        <StatCard
          label="Resolved"
          value={stats.resolved_issues}
          meta={`${Math.round(stats.resolution_rate * 100)}% resolution rate`}
          icon={<Accessibility size={18} />}
          accent="var(--success-base)"
          loading={loading}
        />
      </section>

      <main
        id="a11y-main-content"
        className={styles.main}
        tabIndex={-1}
        aria-labelledby="accessibility-heading"
      >
        {error ? (
          <Card>
            <CardContent>
              <ErrorState
                title="Accessibility data unavailable"
                message={error}
                onRetry={reload}
              />
            </CardContent>
          </Card>
        ) : loading ? (
          <div
            className={styles.loadingGrid}
            role="status"
            aria-label="Loading accessibility data"
          >
            <Skeleton lines={6} />
            <Skeleton lines={6} />
            <Skeleton lines={8} />
          </div>
        ) : (
          <div className={styles.content}>
            <ContrastChecker onAudit={handleAudit} />
            <div className={styles.twoColumn}>
              <ShortcutEditor
                shortcuts={shortcuts}
                onRegister={handleRegister}
                onDelete={handleDelete}
              />
              <IssueList
                issues={issues}
                onResolve={handleResolve}
                onReload={reload}
              />
            </div>
            <div className={styles.twoColumn}>
              <FocusOrderMap entries={focusEntries} onReorder={handleReorder} />
              <MotionControls
                reducedMotion={motion.reducedMotion}
                highContrast={motion.highContrast}
                onReducedMotionChange={(value) =>
                  setMotion((current) => ({ ...current, reducedMotion: value }))
                }
                onHighContrastChange={(value) =>
                  setMotion((current) => ({ ...current, highContrast: value }))
                }
              />
            </div>
          </div>
        )}
      </main>

      <p className={styles.status} role="status" aria-live="polite">
        {status}
      </p>
    </div>
  );
}
