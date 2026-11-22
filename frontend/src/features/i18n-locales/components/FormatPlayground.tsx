/** Interactive number and date formatting playground. */

import { useEffect, useMemo, useState } from "react";
import { Calculator, Save } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  Input,
} from "../../../components/ui";
import { defaultFormatRule, formatDate, formatNumber } from "../format";
import type { FormatKind, FormatRule } from "../types";
import styles from "./FormatPlayground.module.css";

/** Props accepted by {@link FormatPlayground}. */
export interface FormatPlaygroundProps {
  /** The locale whose patterns are previewed. */
  locale: string;
  /** The stored rule, when one exists. */
  rule?: FormatRule;
  /** Called when the edited patterns are saved. */
  onSaveRule?: (numberPattern: string, datePattern: string) => void;
}

const NUMBER_PRESETS = ["#,##0.00", "#,##0", "0.000"];
const DATE_PRESETS = ["YYYY-MM-DD", "DD/MM/YYYY", "MMM DD, YYYY"];

/**
 * Render the formatting playground with instant local previews.
 *
 * @param props - The playground props.
 * @returns The playground element.
 */
export function FormatPlayground({
  locale,
  rule,
  onSaveRule,
}: FormatPlaygroundProps) {
  const defaults = defaultFormatRule(locale);
  const [kind, setKind] = useState<FormatKind>("number");
  const [numberValue, setNumberValue] = useState("1234567.891");
  const [dateValue, setDateValue] = useState("2026-11-20");
  const [numberPattern, setNumberPattern] = useState(
    rule?.number_pattern ?? defaults[0],
  );
  const [datePattern, setDatePattern] = useState(
    rule?.date_pattern ?? defaults[1],
  );

  useEffect(() => {
    setNumberPattern(rule?.number_pattern ?? defaultFormatRule(locale)[0]);
    setDatePattern(rule?.date_pattern ?? defaultFormatRule(locale)[1]);
  }, [locale, rule?.number_pattern, rule?.date_pattern]);

  const output = useMemo(() => {
    try {
      if (kind === "number") {
        if (!numberValue.trim()) return { text: "\u2014", error: "" };
        return {
          text: formatNumber(Number(numberValue), numberPattern),
          error: "",
        };
      }
      return { text: formatDate(dateValue, datePattern, locale), error: "" };
    } catch (error) {
      return {
        text: "\u2014",
        error: error instanceof Error ? error.message : "Invalid pattern",
      };
    }
  }, [datePattern, dateValue, kind, locale, numberPattern, numberValue]);

  const dirty =
    numberPattern !== (rule?.number_pattern ?? defaults[0]) ||
    datePattern !== (rule?.date_pattern ?? defaults[1]);

  return (
    <div className={styles.playground}>
      <div className={styles.modes} role="group" aria-label="Format kind">
        <Button
          variant={kind === "number" ? "primary" : "secondary"}
          size="sm"
          aria-pressed={kind === "number"}
          onClick={() => setKind("number")}
        >
          Number
        </Button>
        <Button
          variant={kind === "date" ? "primary" : "secondary"}
          size="sm"
          aria-pressed={kind === "date"}
          onClick={() => setKind("date")}
        >
          Date
        </Button>
      </div>

      <Card bare className={styles.stage}>
        <CardContent className={styles.stageContent}>
          <div className={styles.inputs}>
            {kind === "number" ? (
              <Input
                label="Number"
                inputMode="decimal"
                value={numberValue}
                onChange={(event) => setNumberValue(event.target.value)}
                hint="Try a large value to see grouping and rounding."
              />
            ) : (
              <Input
                label="ISO date"
                value={dateValue}
                onChange={(event) => setDateValue(event.target.value)}
                hint="Dates use YYYY-MM-DD as their input format."
              />
            )}
            <Input
              label={kind === "number" ? "Number pattern" : "Date pattern"}
              value={kind === "number" ? numberPattern : datePattern}
              onChange={(event) =>
                kind === "number"
                  ? setNumberPattern(event.target.value)
                  : setDatePattern(event.target.value)
              }
              error={output.error || undefined}
            />
          </div>

          <div className={styles.result} role="status" aria-live="polite">
            <span className={styles.resultLabel}>{kind} output</span>
            <strong className={styles.resultValue} data-testid="format-output">
              {output.text}
            </strong>
            <Badge tone={output.error ? "danger" : "success"}>
              {output.error ? "Invalid" : "Preview"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <div className={styles.presets}>
        <span className={styles.presetLabel}>Quick patterns</span>
        {(kind === "number" ? NUMBER_PRESETS : DATE_PRESETS).map((preset) => (
          <Button
            key={preset}
            size="sm"
            variant="subtle"
            onClick={() =>
              kind === "number"
                ? setNumberPattern(preset)
                : setDatePattern(preset)
            }
          >
            {preset}
          </Button>
        ))}
      </div>

      <div className={styles.patternSummary}>
        <span>
          <Calculator size={13} aria-hidden="true" /> {numberPattern}
        </span>
        <span>{datePattern}</span>
      </div>

      {onSaveRule ? (
        <Button
          icon={<Save size={14} />}
          disabled={!dirty || Boolean(output.error)}
          onClick={() => onSaveRule(numberPattern, datePattern)}
        >
          Save patterns for {locale}
        </Button>
      ) : null}
    </div>
  );
}
