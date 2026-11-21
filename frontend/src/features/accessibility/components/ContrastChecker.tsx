import { useState, type FormEvent } from "react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Switch,
} from "../../../components/ui";
import { accessibilityApi } from "../api";
import { evaluateContrast, formatRatio } from "../a11y";
import type { ContrastAudit, ContrastAuditPayload } from "../types";
import styles from "./ContrastChecker.module.css";

export interface ContrastCheckerProps {
  onAudit?: (payload: ContrastAuditPayload) => Promise<ContrastAudit>;
  onAudited?: (audit: ContrastAudit) => void;
}

export function ContrastChecker({ onAudit, onAudited }: ContrastCheckerProps) {
  const [foreground, setForeground] = useState("#4f46e5");
  const [background, setBackground] = useState("#ffffff");
  const [label, setLabel] = useState("Call to action");
  const [largeText, setLargeText] = useState(false);
  const [audit, setAudit] = useState<ContrastAudit | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const evaluation = evaluateContrast(foreground, background, largeText);

  async function submit(record: boolean): Promise<void> {
    if (!evaluation.valid) {
      setError(evaluation.error ?? "Enter a valid colour pair");
      return;
    }
    setBusy(true);
    setError(null);
    const payload: ContrastAuditPayload = {
      foreground: evaluation.foreground,
      background: evaluation.background,
      label: label.trim() || "Text sample",
      large_text: largeText,
      record_issue: record,
    };
    try {
      const request = onAudit ?? accessibilityApi.auditContrast;
      const result = await request(payload);
      setAudit(result);
      onAudited?.(result);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Contrast audit failed",
      );
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    void submit(false);
  }

  const previewStyle = evaluation.valid
    ? { color: evaluation.foreground, backgroundColor: evaluation.background }
    : undefined;

  return (
    <Card as="section" className={styles.card} aria-labelledby="contrast-title">
      <CardHeader>
        <CardTitle id="contrast-title">Contrast checker</CardTitle>
        <CardDescription>
          Evaluate foreground and background colours against WCAG AA and AAA.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.fields}>
            <Input
              label="Foreground"
              value={foreground}
              onChange={(event) => setForeground(event.target.value)}
              hint="Hex, rgb() or a colour name"
            />
            <label className={styles.swatchLabel}>
              <span className={styles.visuallyHidden}>
                Pick foreground colour
              </span>
              <input
                type="color"
                className={styles.swatch}
                value={evaluation.valid ? evaluation.foreground : "#000000"}
                onChange={(event) => setForeground(event.target.value)}
              />
            </label>
            <Input
              label="Background"
              value={background}
              onChange={(event) => setBackground(event.target.value)}
              hint="Hex, rgb() or a colour name"
            />
            <label className={styles.swatchLabel}>
              <span className={styles.visuallyHidden}>
                Pick background colour
              </span>
              <input
                type="color"
                className={styles.swatch}
                value={evaluation.valid ? evaluation.background : "#ffffff"}
                onChange={(event) => setBackground(event.target.value)}
              />
            </label>
          </div>
          <Input
            label="Element label"
            value={label}
            maxLength={120}
            onChange={(event) => setLabel(event.target.value)}
            hint="Used in recorded issues and announcements"
          />
          <Switch
            checked={largeText}
            onChange={(event) => setLargeText(event.target.checked)}
            hint="Large text uses the relaxed 3:1 AA threshold"
          >
            Large text (18pt or 14pt bold)
          </Switch>

          <div
            className={styles.preview}
            style={previewStyle}
            aria-label="Contrast preview"
          >
            <span className={styles.previewEyebrow}>Live preview</span>
            <strong>{label || "Text sample"}</strong>
            <span>Aa Bb Cc 123</span>
          </div>

          <div className={styles.result} role="status" aria-live="polite">
            <div className={styles.metric}>
              <span className={styles.metricLabel}>Contrast ratio</span>
              <strong>
                {evaluation.valid ? formatRatio(evaluation.ratio) : "—"}
              </strong>
            </div>
            <div className={styles.badges}>
              <Badge tone={evaluation.passesAa ? "success" : "danger"}>
                AA {evaluation.passesAa ? "pass" : "fail"}
              </Badge>
              <Badge
                tone={evaluation.passesAaa ? "success" : "warning"}
                outline
              >
                AAA {evaluation.passesAaa ? "pass" : "fail"}
              </Badge>
              <Badge tone={evaluation.valid ? "info" : "danger"} outline>
                {evaluation.level.toUpperCase()}
              </Badge>
            </div>
            <p className={styles.suggestion}>{evaluation.suggestion}</p>
          </div>

          {error ? (
            <p className={styles.error} role="alert">
              {error}
            </p>
          ) : null}

          <div className={styles.actions}>
            <Button type="submit" loading={busy} loadingLabel="Auditing…">
              Audit pair
            </Button>
            <Button
              variant="secondary"
              loading={busy}
              disabled={!evaluation.valid || evaluation.passesAa}
              onClick={() => void submit(true)}
            >
              Record issue
            </Button>
          </div>
        </form>

        {audit ? (
          <p className={styles.lastAudit}>
            Last server audit: {audit.pairs.length} pair(s), {audit.failures}{" "}
            failure(s), {Math.round(audit.pass_rate * 100)}% pass rate.
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
