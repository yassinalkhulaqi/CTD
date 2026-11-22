/**
 * Editor for the configurable scoring policy with live validation feedback.
 */

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { RotateCcw, Save, SlidersHorizontal } from "lucide-react";
import { Button, Card, Input, Switch } from "../../../components/ui";
import { cn, formatNumber } from "../../../lib/utils";
import {
  RULE_LIMITS,
  formatScore,
  projectStreak,
  validateRule,
} from "../scoring";
import type { ScoreRule, ScoreRuleDraft } from "../types";
import styles from "./RuleEditor.module.css";

/** Props accepted by {@link RuleEditor}. */
export interface RuleEditorProps {
  /** The rule currently stored for the team. */
  rule: ScoreRule | null;
  /** Called with the edited values when the form is submitted. */
  onSave: (draft: ScoreRuleDraft) => Promise<boolean> | void;
  /** Show a busy state on the save button. */
  saving?: boolean;
  /** Additional class applied to the container. */
  className?: string;
}

const DEFAULT_DRAFT: ScoreRuleDraft = {
  name: "Balanced",
  base_points: 100,
  difficulty_multiplier: 1,
  first_blood_bonus: 50,
  hint_penalty: 10,
  decay_factor: 0.9,
  decay_enabled: true,
};

const SAMPLE_STREAK = ["easy", "medium", "hard", "insane"] as const;

type NumericField =
  | "base_points"
  | "difficulty_multiplier"
  | "first_blood_bonus"
  | "hint_penalty"
  | "decay_factor";

/** Declarative description of a numeric slider field. */
interface NumericFieldConfig {
  key: NumericField;
  label: string;
  hint: string;
  suffix?: string;
}

const FIELDS: NumericFieldConfig[] = [
  {
    key: "base_points",
    label: "Base points",
    hint: "Awarded before difficulty weighting.",
  },
  {
    key: "difficulty_multiplier",
    label: "Difficulty multiplier",
    hint: "Scales every difficulty weight.",
    suffix: "×",
  },
  {
    key: "first_blood_bonus",
    label: "First blood bonus",
    hint: "Extra points for the earliest solve.",
  },
  {
    key: "hint_penalty",
    label: "Hint penalty",
    hint: "Subtracted for each hint used.",
  },
  {
    key: "decay_factor",
    label: "Decay factor",
    hint: "Applied as factor^solve index.",
    suffix: "×",
  },
];

/**
 * Render the scoring policy editor.
 *
 * @param props - The component props.
 * @returns The editor card.
 */
export function RuleEditor({
  rule,
  onSave,
  saving = false,
  className,
}: RuleEditorProps) {
  const initial = useMemo<ScoreRuleDraft>(() => {
    if (!rule) return DEFAULT_DRAFT;
    return {
      name: rule.name,
      base_points: rule.base_points,
      difficulty_multiplier: rule.difficulty_multiplier,
      first_blood_bonus: rule.first_blood_bonus,
      hint_penalty: rule.hint_penalty,
      decay_factor: rule.decay_factor,
      decay_enabled: rule.decay_enabled,
    };
  }, [rule]);

  const [draft, setDraft] = useState<ScoreRuleDraft>(initial);
  useEffect(() => setDraft(initial), [initial]);

  const errors = validateRule(draft);
  const valid = Object.keys(errors).length === 0;
  const preview = projectStreak(draft, [...SAMPLE_STREAK]);
  const previewTotal = preview.reduce((sum, value) => sum + value, 0);

  const setField = <K extends keyof ScoreRuleDraft>(
    key: K,
    value: ScoreRuleDraft[K],
  ) => setDraft((current) => ({ ...current, [key]: value }));

  const setNumber = (key: NumericField, raw: string) => {
    const parsed = Number(raw);
    setField(key, Number.isFinite(parsed) ? parsed : 0);
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (valid && !saving) void onSave(draft);
  };

  return (
    <Card as="section" className={cn(styles.editor, className)}>
      <div className={styles.header}>
        <div className={styles.titleBlock}>
          <span className={styles.icon} aria-hidden="true">
            <SlidersHorizontal size={18} />
          </span>
          <div>
            <h2 className={styles.title}>Scoring policy</h2>
            <p className={styles.subtitle}>
              Tune how each solve contributes points.
            </p>
          </div>
        </div>
        {rule ? (
          <span className={styles.updated}>
            Updated {new Date(rule.updated_at).toLocaleDateString()}
          </span>
        ) : null}
      </div>

      <form onSubmit={submit} noValidate>
        <Input
          label="Policy name"
          value={draft.name}
          error={errors.name}
          maxLength={64}
          onChange={(event) => setField("name", event.target.value)}
          hint="Shown on every snapshot taken with this policy."
        />

        <div className={styles.fields}>
          {FIELDS.map((field) => {
            const limits = RULE_LIMITS[field.key];
            const value = draft[field.key];
            return (
              <div key={field.key} className={styles.fieldRow}>
                <div className={styles.fieldTop}>
                  <Input
                    label={field.label}
                    type="number"
                    min={limits.min}
                    max={limits.max}
                    step={limits.step}
                    value={value}
                    error={errors[field.key]}
                    onChange={(event) =>
                      setNumber(field.key, event.target.value)
                    }
                    className={styles.numberInput}
                  />
                  <span className={styles.decoration} aria-hidden="true">
                    {field.suffix ?? "pts"}
                  </span>
                </div>
                <input
                  type="range"
                  className={styles.slider}
                  min={limits.min}
                  max={limits.max}
                  step={limits.step}
                  value={Number.isFinite(value) ? value : limits.min}
                  aria-label={`${field.label} slider`}
                  onChange={(event) => setNumber(field.key, event.target.value)}
                />
                <p className={styles.hint}>{field.hint}</p>
              </div>
            );
          })}
        </div>

        <Switch
          label="Enable decay"
          checked={draft.decay_enabled}
          onChange={(event) => setField("decay_enabled", event.target.checked)}
          hint="Later solves are worth progressively fewer points."
        >
          Enable decay
        </Switch>

        <div className={styles.preview} aria-live="polite">
          <div className={styles.previewHeading}>
            <span>Preview streak</span>
            <strong>{formatScore(previewTotal)} pts</strong>
          </div>
          <ol className={styles.previewList}>
            {preview.map((points, index) => (
              <li key={index} className={styles.previewItem}>
                <span>{SAMPLE_STREAK[index]}</span>
                <span className={styles.previewValue}>
                  {formatNumber(points)}
                </span>
              </li>
            ))}
          </ol>
        </div>

        <div className={styles.actions}>
          <Button
            type="submit"
            icon={<Save size={15} />}
            disabled={!valid}
            loading={saving}
          >
            Save policy
          </Button>
          <Button
            type="button"
            variant="ghost"
            icon={<RotateCcw size={15} />}
            onClick={() => setDraft(initial)}
            disabled={saving}
          >
            Reset
          </Button>
          {!valid ? (
            <span className={styles.invalid} role="status">
              Fix the highlighted values to save.
            </span>
          ) : null}
        </div>
      </form>
    </Card>
  );
}
