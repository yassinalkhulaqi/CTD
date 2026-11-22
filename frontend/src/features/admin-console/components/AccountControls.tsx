import { useState } from "react";
import { LockKeyhole, ShieldOff, UserCheck } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  Modal,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  Textarea,
} from "../../../components/ui";
import { formatRelativeTime } from "../../../lib/utils";
import { canSuspend, summarizeAccounts } from "../logic";
import type { AccountControl, AccountStatusPayload } from "../types";
import styles from "./AccountControls.module.css";

export interface AccountControlsProps {
  accounts: AccountControl[];
  operatorId: string;
  busyUser?: string | null;
  loading?: boolean;
  onSetStatus: (payload: AccountStatusPayload) => void;
}

export function AccountControls({
  accounts,
  operatorId,
  busyUser,
  loading = false,
  onSetStatus,
}: AccountControlsProps) {
  const [pending, setPending] = useState<AccountControl | null>(null);
  const [reason, setReason] = useState("");
  const [flags, setFlags] = useState("");
  const [error, setError] = useState<string | null>(null);
  const summary = summarizeAccounts(accounts);

  function openSuspend(account: AccountControl): void {
    setPending(account);
    setReason("");
    setFlags(account.flags.filter((flag) => flag !== "suspended").join(", "));
    setError(null);
  }

  function confirmSuspend(): void {
    if (!pending) return;
    if (!reason.trim()) {
      setError("A reason is required before suspending an account.");
      return;
    }
    const parsedFlags = flags
      .split(",")
      .map((flag) => flag.trim())
      .filter(Boolean);
    onSetStatus({
      user_id: pending.user_id,
      status: "suspended",
      reason: reason.trim(),
      flags: parsedFlags,
    });
    setPending(null);
  }

  function activate(account: AccountControl): void {
    onSetStatus({
      user_id: account.user_id,
      status: "active",
      reason: "Reactivated from the administration console",
      flags: account.flags.filter((flag) => flag !== "suspended"),
    });
  }

  return (
    <Card
      className={styles.card}
      as="section"
      aria-labelledby="admin-accounts-title"
    >
      <CardHeader
        actions={
          <div className={styles.summary}>
            <Badge tone="success" outline>
              {summary.active} active
            </Badge>
            <Badge tone="danger" outline>
              {summary.suspended} suspended
            </Badge>
            <Badge tone="warning" outline>
              {summary.flagged} flagged
            </Badge>
          </div>
        }
      >
        <CardTitle id="admin-accounts-title" level={3}>
          Account controls
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className={styles.loading} aria-busy="true">
            <Skeleton lines={4} />
          </div>
        ) : accounts.length === 0 ? (
          <EmptyState
            icon={<ShieldOff size={22} />}
            title="No accounts"
            description="Accounts become available here once users are registered."
          />
        ) : (
          <Table sticky aria-label="Account controls">
            <TableHead>
              <TableRow>
                <TableHeaderCell>Account</TableHeaderCell>
                <TableHeaderCell>Role</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell>Flags</TableHeaderCell>
                <TableHeaderCell>Updated</TableHeaderCell>
                <TableHeaderCell>Control</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {accounts.map((account) => {
                const allowed = canSuspend(account, operatorId);
                return (
                  <TableRow key={account.user_id}>
                    <TableCell>
                      <strong>{account.username}</strong>
                      <span className={styles.userId}>{account.user_id}</span>
                    </TableCell>
                    <TableCell>
                      <Badge
                        tone={account.role === "admin" ? "accent" : "neutral"}
                        outline
                      >
                        {account.role}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        tone={account.is_suspended ? "danger" : "success"}
                        dot
                      >
                        {account.status}
                      </Badge>
                      {!account.is_consistent ? (
                        <span className={styles.warning}>control mismatch</span>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <div className={styles.flags}>
                        {account.flags.length === 0 ? (
                          <span className={styles.muted}>none</span>
                        ) : (
                          account.flags.map((flag) => (
                            <span className={styles.flag} key={flag}>
                              {flag}
                            </span>
                          ))
                        )}
                      </div>
                    </TableCell>
                    <TableCell className={styles.updated}>
                      {formatRelativeTime(account.updated_at)}
                    </TableCell>
                    <TableCell>
                      {account.is_suspended ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          icon={<UserCheck size={14} />}
                          loading={busyUser === account.user_id}
                          onClick={() => activate(account)}
                        >
                          Activate
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="danger"
                          icon={<ShieldOff size={14} />}
                          disabled={!allowed}
                          title={
                            allowed
                              ? undefined
                              : "Self and administrator accounts are protected"
                          }
                          onClick={() => openSuspend(account)}
                        >
                          Suspend
                        </Button>
                      )}
                      {!allowed && !account.is_suspended ? (
                        <span className={styles.protected}>
                          <LockKeyhole size={11} aria-hidden="true" /> protected
                        </span>
                      ) : null}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Modal
        open={pending !== null}
        onClose={() => setPending(null)}
        title={pending ? `Suspend ${pending.username}` : "Suspend account"}
        description="The account loses access immediately and the reason is written to the audit trail."
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setPending(null)}>
              Cancel
            </Button>
            <Button variant="danger" size="sm" onClick={confirmSuspend}>
              Confirm suspension
            </Button>
          </>
        }
      >
        <div className={styles.dialogFields}>
          <Textarea
            label="Reason"
            rows={3}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            error={error ?? undefined}
          />
          <Input
            label="Flags"
            hint="Comma separated labels kept on the account control."
            value={flags}
            onChange={(event) => setFlags(event.target.value)}
          />
        </div>
      </Modal>
    </Card>
  );
}
