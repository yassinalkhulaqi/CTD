/**
 * Dialog used to invite a new member to a team.
 */

import { useEffect, useId, useState, type FormEvent } from "react";
import { MailPlus } from "lucide-react";
import { Button, Input, Modal, Select } from "../../../components/ui";
import { isValidInviteEmail, ROLE_OPTIONS } from "../domain";
import type { InvitationInput, RosterRole } from "../types";
import styles from "./InviteDialog.module.css";

/** Props accepted by {@link InviteDialog}. */
export interface InviteDialogProps {
  /** Whether the dialog is visible. */
  open: boolean;
  /** Called when the dialog requests to close. */
  onClose: () => void;
  /** Called with the invitation details when the form is submitted. */
  onInvite: (payload: InvitationInput) => void | Promise<void>;
  /** Team identifiers available for invitation. */
  teams: string[];
  /** Disable the submit button while a request is running. */
  busy?: boolean;
  /** Error message returned by the API. */
  error?: string | null;
}

/**
 * Render the invite dialog with email, team and role selection.
 *
 * @param props - The component props.
 * @returns The modal element.
 */
export function InviteDialog({
  open,
  onClose,
  onInvite,
  teams,
  busy = false,
  error = null,
}: InviteDialogProps) {
  const formId = useId();
  const [email, setEmail] = useState("");
  const [teamId, setTeamId] = useState(teams[0] ?? "");
  const [role, setRole] = useState<RosterRole>("member");
  const [validation, setValidation] = useState("");

  useEffect(() => {
    if (!open) return;
    setEmail("");
    setTeamId(teams[0] ?? "");
    setRole("member");
    setValidation("");
  }, [open, teams]);

  function submitNow() {
    if (!isValidInviteEmail(email)) {
      setValidation("Enter a valid email address.");
      return;
    }
    if (!teamId) {
      setValidation("Choose a team for the invitation.");
      return;
    }
    setValidation("");
    void onInvite({ team_id: teamId, email: email.trim(), role });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitNow();
  }

  const teamOptions = teams.map((team) => ({ value: team, label: team }));

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Invite a team member"
      description="Send an email invitation with a preselected roster role."
      size="sm"
      footer={
        <div className={styles.footer}>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={submitNow}
            icon={<MailPlus size={15} />}
            loading={busy}
            loadingLabel="Sending…"
          >
            Send invitation
          </Button>
        </div>
      }
    >
      <form id={formId} onSubmit={submit} className={styles.form}>
        <Input
          label="Email address"
          type="email"
          autoComplete="email"
          placeholder="teammate@example.com"
          value={email}
          error={validation}
          hint="The invitee receives a single-use link valid for seven days."
          onChange={(event) => setEmail(event.target.value)}
        />
        <Select
          label="Team"
          options={teamOptions}
          value={teamId}
          placeholder={teams.length ? undefined : "No teams available"}
          onChange={(event) => setTeamId(event.target.value)}
        />
        <Select
          label="Role"
          value={role}
          options={ROLE_OPTIONS.map((option) => ({
            value: option.value,
            label: `${option.label} — ${option.description}`,
          }))}
          onChange={(event) => setRole(event.target.value as RosterRole)}
        />
        {error ? (
          <p className={styles.apiError} role="alert">
            {error}
          </p>
        ) : null}
      </form>
    </Modal>
  );
}
