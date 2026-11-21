import { History, Search } from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  Select,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../../components/ui";
import { formatRelativeTime, formatTime } from "../../../lib/utils";
import { ACTION_TONES, describeAction, titleCase } from "../logic";
import type {
  ActionFilterState,
  AdminAction,
  AdminActionKind,
  TargetType,
} from "../types";
import styles from "./AuditTable.module.css";

export interface AuditTableProps {
  actions: AdminAction[];
  total: number;
  filter: ActionFilterState;
  loading?: boolean;
  onFilterChange: (filter: ActionFilterState) => void;
}

const TARGET_OPTIONS = [
  { value: "all", label: "All targets" },
  { value: "case", label: "Cases" },
  { value: "account", label: "Accounts" },
  { value: "system", label: "System" },
];

const ACTION_OPTIONS: Array<{ value: AdminActionKind | "all"; label: string }> =
  [
    { value: "all", label: "All actions" },
    { value: "case_opened", label: "Case opened" },
    { value: "case_assigned", label: "Case assigned" },
    { value: "case_resolved", label: "Case resolved" },
    { value: "case_dismissed", label: "Case dismissed" },
    { value: "account_suspended", label: "Account suspended" },
    { value: "account_activated", label: "Account activated" },
    { value: "health_recorded", label: "Health recorded" },
  ];

export function AuditTable({
  actions,
  total,
  filter,
  loading = false,
  onFilterChange,
}: AuditTableProps) {
  return (
    <Card
      className={styles.card}
      as="section"
      aria-labelledby="admin-audit-title"
    >
      <CardHeader
        actions={
          <Badge tone="accent" outline>
            {total} events
          </Badge>
        }
      >
        <CardTitle id="admin-audit-title" level={3}>
          Audit trail
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className={styles.filters}>
          <Select
            label="Target type"
            hideLabel
            value={filter.targetType}
            options={TARGET_OPTIONS}
            onChange={(event) =>
              onFilterChange({
                ...filter,
                targetType: event.target.value as TargetType | "all",
              })
            }
          />
          <Select
            label="Action"
            hideLabel
            value={filter.action}
            options={ACTION_OPTIONS}
            onChange={(event) =>
              onFilterChange({
                ...filter,
                action: event.target.value as AdminActionKind | "all",
              })
            }
          />
          <Input
            label="Actor"
            hideLabel
            placeholder="Filter by actor"
            value={filter.actorId}
            onChange={(event) =>
              onFilterChange({ ...filter, actorId: event.target.value })
            }
          />
          <Input
            label="Search audit trail"
            hideLabel
            icon={<Search size={14} />}
            placeholder="Search reason or target"
            value={filter.search}
            onChange={(event) =>
              onFilterChange({ ...filter, search: event.target.value })
            }
          />
        </div>

        {loading ? (
          <div className={styles.loading} aria-busy="true">
            <Skeleton lines={4} />
          </div>
        ) : actions.length === 0 ? (
          <EmptyState
            icon={<History size={22} />}
            title="No audit events"
            description="Administrative actions will appear here as they happen."
          />
        ) : (
          <Table sticky aria-label="Administration audit trail">
            <TableHead>
              <TableRow>
                <TableHeaderCell>When</TableHeaderCell>
                <TableHeaderCell>Action</TableHeaderCell>
                <TableHeaderCell>Target</TableHeaderCell>
                <TableHeaderCell>Actor</TableHeaderCell>
                <TableHeaderCell>Detail</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {actions.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell>
                    <span className={styles.time}>
                      {formatTime(entry.created_at)}
                    </span>
                    <span className={styles.relative}>
                      {formatRelativeTime(entry.created_at)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge tone={ACTION_TONES[entry.action]} dot>
                      {titleCase(entry.action)}
                    </Badge>
                  </TableCell>
                  <TableCell className={styles.target}>
                    <span>{entry.target_type}</span>
                    <span className={styles.mono}>{entry.target_id}</span>
                  </TableCell>
                  <TableCell className={styles.mono}>
                    {entry.actor_id}
                  </TableCell>
                  <TableCell className={styles.reason}>
                    {describeAction(entry)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
