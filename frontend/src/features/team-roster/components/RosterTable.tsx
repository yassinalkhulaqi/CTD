/**
 * The responsive roster table with filters, sorting and inline role controls.
 */

import { Search, Trash2 } from "lucide-react";
import {
  Avatar,
  EmptyState,
  IconButton,
  Input,
  Select,
  Skeleton,
  StatusDot,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../../components/ui";
import {
  AVAILABILITY_OPTIONS,
  ROLE_OPTIONS,
  availabilityLabel,
  availabilityTone,
} from "../domain";
import type {
  Availability,
  MemberFilters,
  MemberSortKey,
  RosterMember,
  RosterRole,
} from "../types";
import { CapacityBar } from "./CapacityBar";
import { RoleChip } from "./RoleChip";
import styles from "./RosterTable.module.css";

/** Props accepted by {@link RosterTable}. */
export interface RosterTableProps {
  /** The members to render, already filtered and sorted. */
  members: RosterMember[];
  /** Reserved hours keyed by member identifier. */
  assignedHours: Record<string, number>;
  /** The active filter values. */
  filters: MemberFilters;
  /** Called when a filter changes. */
  onFiltersChange: (filters: MemberFilters) => void;
  /** The active sort column. */
  sortKey: MemberSortKey;
  /** Called when a sortable header is pressed. */
  onSortChange: (key: MemberSortKey) => void;
  /** Called when a row's role changes. */
  onRoleChange: (member: RosterMember, role: RosterRole) => void;
  /** Called when a row's member is removed. */
  onRemove: (member: RosterMember) => void;
  /** Show loading placeholders instead of rows. */
  loading?: boolean;
  /** Disable row controls while a mutation is running. */
  busy?: boolean;
}

/**
 * Render the roster table and its filter toolbar.
 *
 * @param props - The component props.
 * @returns The table section element.
 */
export function RosterTable({
  members,
  assignedHours,
  filters,
  onFiltersChange,
  sortKey,
  onSortChange,
  onRoleChange,
  onRemove,
  loading = false,
  busy = false,
}: RosterTableProps) {
  const teams = Array.from(
    new Set(members.map((member) => member.team_id)),
  ).sort();
  const teamOptions = [
    { value: "all", label: "All teams" },
    ...teams.map((team) => ({ value: team, label: team })),
  ];
  const roleOptions = [
    { value: "all", label: "All roles" },
    ...ROLE_OPTIONS.map((option) => ({
      value: option.value,
      label: option.label,
    })),
  ];
  const availabilityOptions = [
    { value: "all", label: "Any availability" },
    ...AVAILABILITY_OPTIONS.map((option) => ({
      value: option.value,
      label: option.label,
    })),
  ];

  function update(patch: Partial<MemberFilters>) {
    onFiltersChange({ ...filters, ...patch });
  }

  function sortDirection(key: MemberSortKey): "asc" | "desc" | null {
    if (sortKey !== key) return null;
    return "asc";
  }

  return (
    <section className={styles.section} aria-labelledby="roster-table-title">
      <div className={styles.toolbar}>
        <div>
          <h2 id="roster-table-title" className={styles.title}>
            Team roster
          </h2>
          <p className={styles.subtitle}>
            {members.length} {members.length === 1 ? "member" : "members"} in
            view
          </p>
        </div>
        <div className={styles.filters}>
          <Select
            label="Filter by team"
            hideLabel
            className={styles.filter}
            options={teamOptions}
            value={filters.teamId}
            onChange={(event) => update({ teamId: event.target.value })}
          />
          <Select
            label="Filter by role"
            hideLabel
            className={styles.filter}
            options={roleOptions}
            value={filters.role}
            onChange={(event) =>
              update({ role: event.target.value as MemberFilters["role"] })
            }
          />
          <Select
            label="Filter by availability"
            hideLabel
            className={styles.filter}
            options={availabilityOptions}
            value={filters.availability}
            onChange={(event) =>
              update({
                availability: event.target.value as Availability | "all",
              })
            }
          />
          <Input
            label="Search roster"
            hideLabel
            className={styles.search}
            icon={<Search size={14} />}
            placeholder="Search members…"
            value={filters.query}
            onChange={(event) => update({ query: event.target.value })}
          />
        </div>
      </div>

      {loading ? (
        <Table sticky aria-label="Loading roster">
          <TableHead>
            <TableRow>
              {[
                "Member",
                "Role",
                "Availability",
                "Focus",
                "Capacity",
                "Actions",
              ].map((label) => (
                <TableHeaderCell key={label}>{label}</TableHeaderCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {Array.from({ length: 4 }, (_, index) => (
              <TableRow key={index}>
                {Array.from({ length: 6 }, (__, cell) => (
                  <TableCell key={cell}>
                    <Skeleton height={18} width={cell === 0 ? "80%" : "60%"} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : members.length === 0 ? (
        <EmptyState
          icon={<Search size={20} />}
          title="No roster members"
          description="Adjust the filters or invite someone to fill the roster."
        />
      ) : (
        <Table sticky aria-label="Team roster">
          <TableHead>
            <TableRow>
              <TableHeaderCell
                sortKey="name"
                sortDirection={sortDirection("name")}
                onSort={(key) => onSortChange(key as MemberSortKey)}
              >
                Member
              </TableHeaderCell>
              <TableHeaderCell
                sortKey="role"
                sortDirection={sortDirection("role")}
                onSort={(key) => onSortChange(key as MemberSortKey)}
              >
                Role
              </TableHeaderCell>
              <TableHeaderCell
                sortKey="availability"
                sortDirection={sortDirection("availability")}
                onSort={(key) => onSortChange(key as MemberSortKey)}
              >
                Availability
              </TableHeaderCell>
              <TableHeaderCell>Focus</TableHeaderCell>
              <TableHeaderCell
                sortKey="capacity"
                sortDirection={sortDirection("capacity")}
                onSort={(key) => onSortChange(key as MemberSortKey)}
              >
                Capacity
              </TableHeaderCell>
              <TableHeaderCell align="right">Actions</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {members.map((member) => (
              <TableRow key={member.id} className={styles.row}>
                <TableCell>
                  <div className={styles.memberCell}>
                    <Avatar
                      name={member.display_name || member.handle}
                      size="sm"
                    />
                    <div>
                      <span className={styles.name}>{member.display_name}</span>
                      <span className={styles.handle}>@{member.handle}</span>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <div className={styles.roleCell}>
                    <RoleChip role={member.role} compact />
                    <select
                      className={styles.roleSelect}
                      aria-label={`Change role for ${member.handle}`}
                      value={member.role}
                      disabled={busy}
                      onChange={(event) =>
                        onRoleChange(member, event.target.value as RosterRole)
                      }
                    >
                      {ROLE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </TableCell>
                <TableCell>
                  <span className={styles.availability}>
                    <StatusDot
                      tone={availabilityTone(member.availability)}
                      pulse={member.availability === "available"}
                    />
                    {availabilityLabel(member.availability)}
                  </span>
                </TableCell>
                <TableCell>
                  <span className={styles.specialty}>
                    {member.specialty || "Generalist"}
                  </span>
                  <span className={styles.timezone}>{member.timezone}</span>
                </TableCell>
                <TableCell className={styles.capacityCell}>
                  <CapacityBar
                    assignedHours={assignedHours[member.id] ?? 0}
                    capacityHours={member.capacity_hours}
                    label={`Capacity for ${member.handle}`}
                  />
                </TableCell>
                <TableCell align="right">
                  <div className={styles.actions}>
                    <IconButton
                      icon={<Trash2 size={15} />}
                      label={`Remove ${member.handle}`}
                      variant="ghost"
                      disabled={busy}
                      onClick={() => onRemove(member)}
                    />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
