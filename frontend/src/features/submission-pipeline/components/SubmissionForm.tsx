/**
 * Console used to enter and submit a flag for validation.
 */

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Send } from "lucide-react";
import { Button, Input, Select } from "../../../components/ui";
import { normalizeFlag, validateFlag } from "../logic";
import type {
  ChallengeOption,
  MemberOption,
  SubmissionDraft,
  ValidationResult,
  ValidationRule,
} from "../types";
import { ValidationHint } from "./ValidationHint";
import styles from "./SubmissionForm.module.css";

/** Props accepted by {@link SubmissionForm}. */
export interface SubmissionFormProps {
  /** Challenges available in the selector. */
  challenges: ChallengeOption[];
  /** Members available in the selector. */
  members: MemberOption[];
  /** Validation rules used for immediate feedback. */
  rules: ValidationRule[];
  /** Disable the selectors while reference data loads. */
  loading?: boolean;
  /** Disable submission while a mutation is in flight. */
  busy?: boolean;
  /** Error returned by the API for the previous submission. */
  error?: string | null;
  /** Called with a validated submission draft. */
  onSubmit: (draft: SubmissionDraft) => void | Promise<void>;
}

/**
 * Render the flag submission form with inline validation.
 *
 * @param props - The component props.
 * @returns The submission form.
 */
export function SubmissionForm({
  challenges,
  members,
  rules,
  loading = false,
  busy = false,
  error = null,
  onSubmit,
}: SubmissionFormProps) {
  const [challengeId, setChallengeId] = useState("");
  const [memberId, setMemberId] = useState("");
  const [flag, setFlag] = useState("");
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const selectedChallenge = useMemo(
    () => challenges.find((challenge) => challenge.id === challengeId),
    [challenges, challengeId],
  );

  const teamMembers = useMemo(
    () =>
      selectedChallenge
        ? members.filter(
            (member) => member.team_id === selectedChallenge.team_id,
          )
        : members,
    [members, selectedChallenge],
  );

  useEffect(() => {
    if (!challengeId && challenges.length > 0) {
      const first = challenges[0];
      setChallengeId(first.id);
      const firstMember = members.find(
        (member) => member.team_id === first.team_id,
      );
      if (firstMember) setMemberId(firstMember.id);
    }
  }, [challengeId, challenges, members]);

  useEffect(() => {
    if (
      teamMembers.length > 0 &&
      !teamMembers.some((member) => member.id === memberId)
    ) {
      setMemberId(teamMembers[0].id);
    }
  }, [memberId, teamMembers]);

  const hints = useMemo(
    () =>
      rules
        .filter((rule) => rule.enabled)
        .sort((a, b) => a.priority - b.priority)
        .map((rule) => rule.description || `Flag must satisfy ${rule.name}.`),
    [rules],
  );

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    const validation = validateFlag(flag, rules);
    setResult(validation);
    if (!validation.valid) return;
    if (!challengeId || !memberId) {
      setFormError("Select both a challenge and a member before submitting.");
      return;
    }
    void onSubmit({
      challenge_id: challengeId,
      member_id: memberId,
      flag: normalizeFlag(flag),
    });
    setFlag("");
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <div className={styles.selectors}>
        <Select
          label="Challenge"
          value={challengeId}
          disabled={loading || busy || challenges.length === 0}
          onChange={(event) => setChallengeId(event.target.value)}
          placeholder={
            challenges.length === 0
              ? "No challenges available"
              : "Select challenge"
          }
          options={challenges.map((challenge) => ({
            value: challenge.id,
            label: challenge.title,
          }))}
        />
        <Select
          label="Member"
          value={memberId}
          disabled={loading || busy || teamMembers.length === 0}
          onChange={(event) => setMemberId(event.target.value)}
          placeholder={
            teamMembers.length === 0 ? "No members available" : "Select member"
          }
          options={teamMembers.map((member) => ({
            value: member.id,
            label: member.display_name || member.handle,
          }))}
        />
      </div>

      <Input
        label="Flag"
        value={flag}
        disabled={busy}
        autoComplete="off"
        spellCheck={false}
        placeholder="flag{example_value}"
        className={styles.flagInput}
        onChange={(event) => {
          setFlag(event.target.value);
          setResult(null);
          setFormError(null);
        }}
        error={formError ?? undefined}
        hint="Trimmed and lower-cased before validation."
      />

      {error ? (
        <p className={styles.apiError} role="alert">
          {error}
        </p>
      ) : null}

      <div className={styles.actions}>
        <Button
          type="submit"
          icon={<Send size={15} />}
          loading={busy}
          disabled={loading}
        >
          Submit flag
        </Button>
        <span className={styles.helper}>
          Queued flags are validated by the pipeline.
        </span>
      </div>

      <ValidationHint result={result} rules={hints} />
    </form>
  );
}
