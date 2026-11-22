import {
  Clock3,
  Flag,
  Plus,
  RotateCcw,
  Search,
  ShieldCheck,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Checkbox,
  EmptyState,
  Input,
  Select,
  Skeleton,
} from "../../../components/ui";
import { cn, formatRelativeTime } from "../../../lib/utils";
import {
  CASE_STATUS_LABELS,
  PRIORITY_LABELS,
  PRIORITY_TONES,
  REPORT_LABELS,
  STATUS_TONES,
  formatSla,
} from "../logic";
import {
  DEFAULT_CASE_FILTER,
  type CaseFilterState,
  type CasePriority,
  type CaseSort,
  type CaseStatus,
  type ModerationCase,
  type ReportType,
} from "../types";
import styles from "./ModerationQueue.module.css";

export interface ModerationQueueProps {
  cases: ModerationCase[];
  total: number;
  filter: CaseFilterState;
  loading?: boolean;
  selectedId?: string | null;
  onFilterChange: (filter: CaseFilterState) => void;
  onSelect: (item: ModerationCase) => void;
  onOpenNew?: () => void;
}

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  ...Object.entries(CASE_STATUS_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

const PRIORITY_OPTIONS = [
  { value: "all", label: "All priorities" },
  ...Object.entries(PRIORITY_LABELS).map(([value, label]) => ({
    value,
    label,
  })),
];

const REPORT_OPTIONS = [
  { value: "all", label: "All report types" },
  ...Object.entries(REPORT_LABELS).map(([value, label]) => ({ value, label })),
];

const SORT_OPTIONS: Array<{ value: CaseSort; label: string }> = [
  { value: "created_desc", label: "Newest first" },
  { value: "created_asc", label: "Oldest first" },
  { value: "priority_desc", label: "Highest priority" },
  { value: "due_asc", label: "SLA deadline" },
];

export function ModerationQueue({
  cases,
  total,
  filter,
  loading = false,
  selectedId,
  onFilterChange,
  onSelect,
  onOpenNew,
}: ModerationQueueProps) {
  const reset = () => onFilterChange(DEFAULT_CASE_FILTER);
  const activeFilters =
    filter.status !== "all" ||
    filter.priority !== "all" ||
    filter.reportType !== "all" ||
    filter.search !== "" ||
    filter.overdueOnly ||
    filter.unassigned;

  return (
    <Card
      className={styles.card}
      as="section"
      aria-labelledby="admin-queue-title"
    >
      <CardHeader
        actions={
          onOpenNew ? (
            <Button size="sm" icon={<Plus size={14} />} onClick={onOpenNew}>
              New case
            </Button>
          ) : undefined
        }
      >
        <CardTitle id="admin-queue-title" level={3}>
          Moderation queue
        </CardTitle>
        <span className={styles.total}>{total} reports</span>
      </CardHeader>
      <CardContent>
        <div className={styles.filters}>
          <Select
            label="Status"
            hideLabel
            value={filter.status}
            options={STATUS_OPTIONS}
            onChange={(event) =>
              onFilterChange({
                ...filter,
                status: event.target.value as CaseStatus | "all",
              })
            }
          />
          <Select
            label="Priority"
            hideLabel
            value={filter.priority}
            options={PRIORITY_OPTIONS}
            onChange={(event) =>
              onFilterChange({
                ...filter,
                priority: event.target.value as CasePriority | "all",
              })
            }
          />
          <Select
            label="Report type"
            hideLabel
            value={filter.reportType}
            options={REPORT_OPTIONS}
            onChange={(event) =>
              onFilterChange({
                ...filter,
                reportType: event.target.value as ReportType | "all",
              })
            }
          />
          <Select
            label="Sort cases"
            hideLabel
            value={filter.sort}
            options={SORT_OPTIONS}
            onChange={(event) =>
              onFilterChange({
                ...filter,
                sort: event.target.value as CaseSort,
              })
            }
          />
          <Input
            label="Search reports"
            hideLabel
            icon={<Search size={14} />}
            placeholder="Search target or reporter"
            value={filter.search}
            onChange={(event) =>
              onFilterChange({ ...filter, search: event.target.value })
            }
          />
          <Checkbox
            label="Overdue only"
            checked={filter.overdueOnly}
            onChange={(event) =>
              onFilterChange({ ...filter, overdueOnly: event.target.checked })
            }
          />
          <Button
            variant="ghost"
            size="sm"
            icon={<RotateCcw size={14} />}
            onClick={reset}
            disabled={!activeFilters}
          >
            Reset
          </Button>
        </div>

        {loading ? (
          <div className={styles.list} aria-busy="true">
            {[0, 1, 2].map((index) => (
              <div className={styles.row} key={index}>
                <Skeleton lines={2} />
              </div>
            ))}
          </div>
        ) : cases.length === 0 ? (
          <EmptyState
            icon={<ShieldCheck size={22} />}
            title="Queue is clear"
            description="No reports match the current filters."
          />
        ) : (
          <ul className={styles.list}>
            {cases.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={cn(
                    styles.row,
                    item.id === selectedId && styles.selected,
                  )}
                  aria-label={`Review case ${item.id}`}
                  aria-pressed={item.id === selectedId}
                  onClick={() => onSelect(item)}
                >
                  <span className={styles.rowTop}>
                    <span className={styles.caseId}>{item.id}</span>
                    <Badge tone={PRIORITY_TONES[item.priority]} dot>
                      {PRIORITY_LABELS[item.priority]}
                    </Badge>
                    <Badge tone={STATUS_TONES[item.status]} outline>
                      {CASE_STATUS_LABELS[item.status]}
                    </Badge>
                  </span>
                  <span className={styles.caseType}>
                    <Flag size={13} aria-hidden="true" />
                    {REPORT_LABELS[item.report_type]}
                  </span>
                  <span className={styles.rowMeta}>
                    <span>Target {item.target_id}</span>
                    <span>Reporter {item.reporter_id}</span>
                    <span>{formatRelativeTime(item.created_at)}</span>
                  </span>
                  <span className={styles.rowBottom}>
                    <span
                      className={cn(
                        styles.sla,
                        item.is_overdue && styles.overdue,
                      )}
                    >
                      <Clock3 size={12} aria-hidden="true" />
                      {formatSla(item)}
                    </span>
                    <span className={styles.assignee}>
                      {item.assignee_id
                        ? `Assigned to ${item.assignee_id}`
                        : "Unassigned"}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
