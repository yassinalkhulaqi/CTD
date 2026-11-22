/** Registration dialog with team selection and accessible focus handling. */

import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { Button, Modal, Select } from "../../../components/ui";
import type { CtfEvent, TeamOption } from "../types";
import styles from "./RegistrationDialog.module.css";

/** Props accepted by {@link RegistrationDialog}. */
export interface RegistrationDialogProps {
  event: CtfEvent | null;
  teams: TeamOption[];
  open: boolean;
  busy?: boolean;
  error?: string | null;
  onClose: () => void;
  onSubmit: (teamId: string) => void;
}

/**
 * Render the registration dialog for one event.
 *
 * The shared modal primitive traps focus, closes on Escape and restores focus
 * to the trigger when the dialog closes.
 *
 * @param props - The component props.
 * @returns The dialog, or `null` when closed.
 */
export function RegistrationDialog({
  event,
  teams,
  open,
  busy = false,
  error = null,
  onClose,
  onSubmit,
}: RegistrationDialogProps) {
  const [teamId, setTeamId] = useState("");

  useEffect(() => {
    if (open) setTeamId("");
  }, [open, event?.id]);

  const options = teams.map((team) => ({ value: team.id, label: team.name }));

  return (
    <Modal
      open={open && event !== null}
      onClose={onClose}
      title={event ? `Register for ${event.name}` : "Register"}
      description="Pick the team that will take part in this event."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            onClick={() => teamId && onSubmit(teamId)}
            disabled={!teamId || teams.length === 0}
            loading={busy}
            loadingLabel="Registering"
            icon={<Users size={15} />}
          >
            Confirm registration
          </Button>
        </>
      }
    >
      {teams.length === 0 ? (
        <p className={styles.hint} role="status">
          No teams are available yet. Create a team before registering for an
          event.
        </p>
      ) : (
        <Select
          label="Team"
          hint="You can register one team per event. Full events place new teams on a waitlist."
          options={options}
          placeholder="Choose a team"
          value={teamId}
          onChange={(change) => setTeamId(change.target.value)}
        />
      )}
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
    </Modal>
  );
}
