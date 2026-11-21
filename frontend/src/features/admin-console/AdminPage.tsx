import { useMemo, useState, type FormEvent } from "react";
import { AlertCircle, RefreshCw, Shield } from "lucide-react";
import {
  Badge,
  Button,
  ErrorState,
  Input,
  Modal,
  Select,
} from "../../components/ui";
import { useAdminConsole } from "./hooks";
import {
  AccountControls,
  AdminStats,
  AuditTable,
  CaseDetail,
  HealthGauge,
  ModerationQueue,
} from "./components";
import { filterActions } from "./logic";
import {
  DEFAULT_ACTION_FILTER,
  DEFAULT_CASE_FILTER,
  type CaseFilterState,
  type CreateCasePayload,
  type ModerationCase,
  type ReportType,
} from "./types";
import styles from "./AdminPage.module.css";

const REPORT_OPTIONS = [
  { value: "harassment", label: "Harassment" },
  { value: "cheating", label: "Cheating" },
  { value: "spam", label: "Spam" },
  { value: "inappropriate_content", label: "Inappropriate content" },
  { value: "security_issue", label: "Security issue" },
  { value: "other", label: "Other" },
];

const PRIORITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

const EMPTY_CASE: CreateCasePayload = {
  report_type: "other",
  target_id: "",
  reporter_id: "",
  priority: "normal",
};

export function AdminPage() {
  const admin = useAdminConsole();
  const [caseFilter, setCaseFilter] = useState<CaseFilterState>({
    ...DEFAULT_CASE_FILTER,
  });
  const [actionFilter, setActionFilter] = useState(DEFAULT_ACTION_FILTER);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [newCase, setNewCase] = useState<CreateCasePayload>(EMPTY_CASE);
  const [newCaseOpen, setNewCaseOpen] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const operatorId = "admin";

  function changeCaseFilter(next: CaseFilterState): void {
    setCaseFilter(next);
    void admin.loadCases(next);
  }

  const selected = useMemo<ModerationCase | null>(() => {
    if (!admin.data) return null;
    return (
      admin.data.cases.items.find((item) => item.id === selectedId) ?? null
    );
  }, [admin.data, selectedId]);

  const visibleActions = useMemo(
    () =>
      admin.data ? filterActions(admin.data.actions.items, actionFilter) : [],
    [admin.data, actionFilter],
  );

  function notify(success: boolean, text: string): void {
    if (success) setMessage(text);
  }

  async function handleNewCase(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    const success = await admin.openCase({
      ...newCase,
      target_id: newCase.target_id.trim(),
      reporter_id: newCase.reporter_id.trim(),
    });
    if (success) {
      setNewCase(EMPTY_CASE);
      setNewCaseOpen(false);
      setMessage("Moderation case opened.");
    }
  }

  if (!admin.data && admin.loading) {
    return (
      <main
        className={styles.page}
        data-feature="admin-console"
        aria-busy="true"
      >
        <div className={styles.header}>
          <div>
            <h1>Administration console</h1>
            <p>Loading moderation, audit and health data…</p>
          </div>
        </div>
        <AdminStats stats={null} loading />
      </main>
    );
  }

  if (!admin.data) {
    return (
      <main className={styles.page} data-feature="admin-console">
        <ErrorState
          title="Administration console unavailable"
          message={admin.error ?? "The console could not load its data."}
          onRetry={() => void admin.refresh()}
        />
      </main>
    );
  }

  const { cases, accounts, health, stats } = admin.data;

  return (
    <main className={styles.page} data-feature="admin-console">
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}>
            <Shield size={14} aria-hidden="true" />
            Settings / Administration
          </div>
          <h1>Administration console</h1>
          <p>
            Triage reports, manage account access and watch platform health from
            a single control room.
          </p>
        </div>
        <div className={styles.headerActions}>
          <Badge tone="accent" outline>
            Operator {operatorId}
          </Badge>
          <Button
            variant="secondary"
            size="sm"
            icon={<RefreshCw size={14} />}
            loading={admin.loading}
            onClick={() => void admin.refresh()}
          >
            Refresh
          </Button>
        </div>
      </header>

      {admin.error ? (
        <div className={styles.error} role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          <span>{admin.error}</span>
          <Button variant="ghost" size="sm" onClick={admin.clearError}>
            Dismiss
          </Button>
        </div>
      ) : null}
      {message ? (
        <div className={styles.success} role="status">
          {message}
        </div>
      ) : null}

      <AdminStats stats={stats} loading={admin.loading} />

      <div className={styles.grid}>
        <div className={styles.primary}>
          <ModerationQueue
            cases={cases.items}
            total={cases.total}
            filter={caseFilter}
            loading={admin.loading}
            selectedId={selectedId}
            onFilterChange={changeCaseFilter}
            onSelect={(item) => setSelectedId(item.id)}
            onOpenNew={() => setNewCaseOpen(true)}
          />
          <AuditTable
            actions={visibleActions}
            total={visibleActions.length}
            filter={actionFilter}
            loading={admin.loading}
            onFilterChange={setActionFilter}
          />
        </div>
        <div className={styles.sidebar}>
          <CaseDetail
            item={selected}
            operatorId={operatorId}
            busyAction={
              admin.busy?.startsWith("case:")
                ? (admin.busy.split(":").at(-1) as
                    "assign" | "resolve" | "dismiss")
                : null
            }
            onAssign={(item) => {
              void admin
                .updateCase(item.id, "assign", operatorId)
                .then((ok) => notify(ok, `Case ${item.id} assigned.`));
            }}
            onResolve={(item, resolution) => {
              void admin
                .updateCase(item.id, "resolve", resolution)
                .then((ok) => notify(ok, `Case ${item.id} resolved.`));
            }}
            onDismiss={(item, reason) => {
              void admin
                .updateCase(item.id, "dismiss", reason)
                .then((ok) => notify(ok, `Case ${item.id} dismissed.`));
            }}
          />
          <HealthGauge
            health={health.latest}
            loading={admin.loading}
            busy={admin.busy === "health:record"}
            onRecord={(payload) =>
              admin.recordHealth(payload).then((ok) => {
                notify(ok, "Health snapshot recorded.");
                return ok;
              })
            }
          />
        </div>
      </div>

      <AccountControls
        accounts={accounts.items}
        operatorId={operatorId}
        busyUser={
          admin.busy?.startsWith("account:") ? admin.busy.split(":")[1] : null
        }
        loading={admin.loading}
        onSetStatus={(payload) => {
          void admin
            .changeAccountStatus(payload)
            .then((ok) => notify(ok, `Account ${payload.user_id} updated.`));
        }}
      />

      <Modal
        open={newCaseOpen}
        onClose={() => setNewCaseOpen(false)}
        title="Open moderation case"
        description="Create a report that enters the queue with the priority SLA attached."
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setNewCaseOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" form="admin-new-case" size="sm">
              Open case
            </Button>
          </>
        }
      >
        <form
          id="admin-new-case"
          className={styles.newCaseForm}
          onSubmit={(event) => void handleNewCase(event)}
        >
          <Select
            label="Report type"
            value={newCase.report_type}
            options={REPORT_OPTIONS}
            onChange={(event) =>
              setNewCase({
                ...newCase,
                report_type: event.target.value as ReportType,
              })
            }
          />
          <Select
            label="Priority"
            value={newCase.priority}
            options={PRIORITY_OPTIONS}
            onChange={(event) =>
              setNewCase({
                ...newCase,
                priority: event.target.value as CreateCasePayload["priority"],
              })
            }
          />
          <Input
            label="Target ID"
            required
            value={newCase.target_id}
            onChange={(event) =>
              setNewCase({ ...newCase, target_id: event.target.value })
            }
          />
          <Input
            label="Reporter ID"
            required
            value={newCase.reporter_id}
            onChange={(event) =>
              setNewCase({ ...newCase, reporter_id: event.target.value })
            }
          />
        </form>
      </Modal>
    </main>
  );
}
