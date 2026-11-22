import { useEffect, useState } from "react";
import { CheckCircle2, Clock3, ShieldX, UserRoundCheck } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Modal,
  Textarea,
} from "../../../components/ui";
import { formatRelativeTime } from "../../../lib/utils";
import {
  CASE_STATUS_LABELS,
  PRIORITY_LABELS,
  PRIORITY_TONES,
  REPORT_LABELS,
  STATUS_TONES,
  formatSla,
} from "../logic";
import type { ModerationCase } from "../types";
import styles from "./CaseDetail.module.css";

export interface CaseDetailProps {
  item: ModerationCase | null;
  operatorId: string;
  busyAction?: "assign" | "resolve" | "dismiss" | null;
  onAssign: (item: ModerationCase) => void;
  onResolve: (item: ModerationCase, resolution: string) => void;
  onDismiss: (item: ModerationCase, reason: string) => void;
}

export function CaseDetail({
  item,
  operatorId,
  busyAction,
  onAssign,
  onResolve,
  onDismiss,
}: CaseDetailProps) {
  const [dialog, setDialog] = useState<"resolve" | "dismiss" | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDialog(null);
    setText("");
    setError(null);
  }, [item?.id]);

  function openDialog(kind: "resolve" | "dismiss"): void {
    setDialog(kind);
    setText("");
    setError(null);
  }

  function confirm(): void {
    if (!item || !dialog) return;
    if (!text.trim()) {
      setError(
        dialog === "resolve"
          ? "Describe the resolution."
          : "Explain why this report is being dismissed.",
      );
      return;
    }
    if (dialog === "resolve") {
      onResolve(item, text.trim());
    } else {
      onDismiss(item, text.trim());
    }
    setDialog(null);
    setText("");
  }

  if (!item) {
    return (
      <Card
        className={styles.card}
        as="section"
        aria-labelledby="admin-detail-title"
      >
        <CardHeader>
          <CardTitle id="admin-detail-title" level={3}>
            Case detail
          </CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Select a report"
            description="Choose a case from the queue to inspect its SLA and history."
          />
        </CardContent>
      </Card>
    );
  }

  const isClosed = item.is_terminal;

  return (
    <Card
      className={styles.card}
      as="section"
      aria-labelledby="admin-detail-title"
    >
      <CardHeader
        actions={
          <Badge tone={STATUS_TONES[item.status]} dot>
            {CASE_STATUS_LABELS[item.status]}
          </Badge>
        }
      >
        <CardTitle id="admin-detail-title" level={3}>
          Case detail
        </CardTitle>
        <span className={styles.caseId}>{item.id}</span>
      </CardHeader>
      <CardContent>
        <div className={styles.tags}>
          <Badge tone={PRIORITY_TONES[item.priority]}>
            {PRIORITY_LABELS[item.priority]}
          </Badge>
          <Badge outline>{REPORT_LABELS[item.report_type]}</Badge>
          <span className={cnSla(item)}>
            <Clock3 size={12} aria-hidden="true" />
            {formatSla(item)}
          </span>
        </div>

        <dl className={styles.details}>
          <div>
            <dt>Target</dt>
            <dd>{item.target_id}</dd>
          </div>
          <div>
            <dt>Reporter</dt>
            <dd>{item.reporter_id}</dd>
          </div>
          <div>
            <dt>Assignee</dt>
            <dd>{item.assignee_id ?? "Unassigned"}</dd>
          </div>
          <div>
            <dt>Opened</dt>
            <dd>{formatRelativeTime(item.created_at)}</dd>
          </div>
          <div>
            <dt>SLA target</dt>
            <dd>{item.sla_hours} hours</dd>
          </div>
          <div>
            <dt>State</dt>
            <dd>{isClosed ? "Closed" : "Active"}</dd>
          </div>
        </dl>

        {item.resolution ? (
          <div className={styles.resolution}>
            <span>Resolution</span>
            <p>{item.resolution}</p>
          </div>
        ) : null}

        <div className={styles.actions}>
          <Button
            variant="secondary"
            size="sm"
            icon={<UserRoundCheck size={14} />}
            disabled={isClosed || item.assignee_id === operatorId}
            loading={busyAction === "assign"}
            onClick={() => onAssign(item)}
          >
            Assign to me
          </Button>
          <Button
            size="sm"
            icon={<CheckCircle2 size={14} />}
            disabled={isClosed}
            onClick={() => openDialog("resolve")}
          >
            Resolve
          </Button>
          <Button
            variant="danger"
            size="sm"
            icon={<ShieldX size={14} />}
            disabled={isClosed}
            onClick={() => openDialog("dismiss")}
          >
            Dismiss
          </Button>
        </div>
      </CardContent>

      <Modal
        open={dialog !== null}
        onClose={() => setDialog(null)}
        title={dialog === "resolve" ? "Resolve case" : "Dismiss case"}
        description={
          dialog === "resolve"
            ? "The resolution is written to the audit trail and shown on the case."
            : "Dismissing closes the case. Provide a concise explanation."
        }
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button
              variant={dialog === "dismiss" ? "danger" : "primary"}
              size="sm"
              onClick={confirm}
            >
              {dialog === "resolve"
                ? "Confirm resolution"
                : "Confirm dismissal"}
            </Button>
          </>
        }
      >
        <Textarea
          label={dialog === "resolve" ? "Resolution" : "Reason"}
          value={text}
          rows={4}
          onChange={(event) => setText(event.target.value)}
          error={error ?? undefined}
          placeholder={
            dialog === "resolve"
              ? "What action was taken?"
              : "Why is this report not a violation?"
          }
        />
      </Modal>
    </Card>
  );
}

function cnSla(item: ModerationCase): string {
  return [styles.sla, item.is_overdue ? styles.overdue : ""]
    .filter(Boolean)
    .join(" ");
}
