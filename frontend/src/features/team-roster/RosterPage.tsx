/**
 * The routed roster page: statistics, filters, roster views and invitations.
 */

import { useMemo, useState } from "react";
import { ClipboardList, MailPlus, RefreshCw, Trash2 } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  CardTitle,
  ErrorState,
  IconButton,
  Input,
  SegmentedControl,
  Select,
} from "../../components/ui";
import {
  assignedHoursByMember,
  effectiveInvitationStatus,
  filterMembers,
  formatHours,
  isValidHandle,
  sortMembers,
  summariseRoster,
} from "./domain";
import { InviteDialog } from "./components/InviteDialog";
import { MemberCard } from "./components/MemberCard";
import { RoleChip } from "./components/RoleChip";
import { RosterStatsView } from "./components/RosterStats";
import { RosterTable } from "./components/RosterTable";
import { useRoster } from "./hooks";
import type {
  Invitation,
  InvitationInput,
  MemberFilters,
  MemberSortKey,
  RosterRole,
  RosterView,
} from "./types";
import styles from "./RosterPage.module.css";

const INITIAL_FILTERS: MemberFilters = {
  teamId: "all",
  role: "all",
  availability: "all",
  query: "",
};

/** The roster plugin page. */
export function RosterPage() {
  const roster = useRoster();
  const [filters, setFilters] = useState<MemberFilters>(INITIAL_FILTERS);
  const [sortKey, setSortKey] = useState<MemberSortKey>("name");
  const [view, setView] = useState<RosterView>("table");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [handles, setHandles] = useState<Record<string, string>>({});
  const [assignment, setAssignment] = useState({
    memberId: "",
    challengeId: "",
    hours: "2",
  });
  const [assignmentError, setAssignmentError] = useState("");

  const teams = useMemo(() => {
    const ids = Array.from(
      new Set(roster.members.map((member) => member.team_id)),
    ).sort();
    return ids.length > 0 ? ids : ["team-1"];
  }, [roster.members]);

  const hoursByMember = useMemo(
    () => assignedHoursByMember(roster.assignments),
    [roster.assignments],
  );

  const visibleMembers = useMemo(
    () => sortMembers(filterMembers(roster.members, filters), sortKey),
    [roster.members, filters, sortKey],
  );

  const summary = useMemo(
    () =>
      summariseRoster(
        roster.members,
        roster.assignments,
        roster.invitations.filter(
          (invite) => effectiveInvitationStatus(invite) === "pending",
        ).length,
      ),
    [roster.members, roster.assignments, roster.invitations],
  );

  async function act(action: () => Promise<unknown>, message: string) {
    try {
      await action();
      setNotice(message);
    } catch {
      setNotice(null);
    }
  }

  function handleRoleChange(
    member: { id: string; handle: string },
    role: RosterRole,
  ) {
    const current = roster.members.find((item) => item.id === member.id);
    if (!current || current.role === role) return;
    void act(
      () => roster.changeRole(member.id, role),
      `${current.handle} is now a ${role}.`,
    );
  }

  function handleRemove(member: { id: string; handle: string }) {
    void act(
      () => roster.removeMember(member.id),
      `${member.handle} was removed.`,
    );
  }

  function handleInvite(payload: InvitationInput) {
    void act(async () => {
      await roster.invite(payload);
      setInviteOpen(false);
    }, `Invitation sent to ${payload.email}.`);
  }

  function handleAccept(invite: Invitation, handle: string) {
    void act(
      () => roster.accept(invite.id, handle),
      `${handle} joined the roster.`,
    );
  }

  function handleAssign() {
    const hours = Number(assignment.hours);
    if (
      !assignment.memberId ||
      !assignment.challengeId.trim() ||
      !(hours > 0)
    ) {
      setAssignmentError(
        "Choose a member, a challenge and a positive hour count.",
      );
      return;
    }
    const member = roster.members.find(
      (item) => item.id === assignment.memberId,
    );
    const used = hoursByMember[assignment.memberId] ?? 0;
    if (member && used + hours > member.capacity_hours) {
      setAssignmentError(
        "That reservation exceeds the member's remaining capacity.",
      );
      return;
    }
    setAssignmentError("");
    void act(async () => {
      await roster.assign({
        member_id: assignment.memberId,
        challenge_id: assignment.challengeId.trim(),
        hours,
      });
      setAssignment((current) => ({ ...current, challengeId: "" }));
    }, "Work assigned.");
  }

  const memberOptions = roster.members.map((member) => ({
    value: member.id,
    label: `${member.display_name} (@${member.handle})`,
  }));

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Operations</p>
          <h1 className={styles.title}>Team roster</h1>
          <p className={styles.intro}>
            Manage the people behind the solves: roles, availability, capacity
            and invitations in one place.
          </p>
        </div>
        <div className={styles.headerActions}>
          <Button
            variant="secondary"
            icon={<RefreshCw size={15} />}
            onClick={() => void roster.refresh()}
          >
            Refresh
          </Button>
          <Button
            icon={<MailPlus size={15} />}
            onClick={() => setInviteOpen(true)}
          >
            Invite member
          </Button>
        </div>
      </header>

      {roster.error ? (
        <ErrorState
          title="The roster could not be loaded"
          message={roster.error}
          onRetry={() => void roster.refresh()}
        />
      ) : null}
      {notice ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}

      <RosterStatsView
        stats={roster.stats}
        summary={summary}
        loading={roster.loading}
      />

      <div className={styles.layoutControl}>
        <SegmentedControl<RosterView>
          label="Roster layout"
          value={view}
          onValueChange={setView}
          options={[
            { value: "table", label: "Table" },
            { value: "cards", label: "Cards" },
          ]}
        />
      </div>

      {view === "table" ? (
        <RosterTable
          members={visibleMembers}
          assignedHours={hoursByMember}
          filters={filters}
          onFiltersChange={setFilters}
          sortKey={sortKey}
          onSortChange={setSortKey}
          onRoleChange={handleRoleChange}
          onRemove={handleRemove}
          loading={roster.loading}
          busy={roster.busy}
        />
      ) : (
        <section className={styles.cards} aria-label="Roster member cards">
          {visibleMembers.length === 0 ? (
            <p className={styles.emptyText}>
              No member matches the current filters.
            </p>
          ) : (
            visibleMembers.map((member) => (
              <MemberCard
                key={member.id}
                member={member}
                assignedHours={hoursByMember[member.id] ?? 0}
                onRoleChange={(item, role) => handleRoleChange(item, role)}
                onRemove={handleRemove}
                busy={roster.busy}
              />
            ))
          )}
        </section>
      )}

      <div className={styles.lower}>
        <Card as="section" className={styles.panel}>
          <CardHeader
            actions={<Badge tone="warning">{summary.pending} pending</Badge>}
          >
            <CardTitle level={3}>Invitations</CardTitle>
          </CardHeader>
          {roster.invitations.length === 0 ? (
            <p className={styles.emptyText}>
              No invitations yet. Use the invite button to add someone to a
              team.
            </p>
          ) : (
            <ul className={styles.inviteList}>
              {roster.invitations.map((invite) => {
                const status = effectiveInvitationStatus(invite);
                const handle = handles[invite.id] ?? invite.email.split("@")[0];
                return (
                  <li key={invite.id} className={styles.inviteRow}>
                    <div className={styles.inviteInfo}>
                      <span className={styles.email}>{invite.email}</span>
                      <div className={styles.inviteBadges}>
                        <RoleChip role={invite.role} compact />
                        <Badge
                          tone={
                            status === "accepted"
                              ? "success"
                              : status === "revoked"
                                ? "danger"
                                : status === "expired"
                                  ? "neutral"
                                  : "warning"
                          }
                        >
                          {status}
                        </Badge>
                      </div>
                      <span className={styles.meta}>
                        {invite.masked_token} · team {invite.team_id}
                      </span>
                    </div>
                    {status === "pending" ? (
                      <div className={styles.inviteActions}>
                        <Input
                          label={`Handle for ${invite.email}`}
                          hideLabel
                          className={styles.handleInput}
                          value={handle}
                          onChange={(event) =>
                            setHandles((current) => ({
                              ...current,
                              [invite.id]: event.target.value,
                            }))
                          }
                        />
                        <Button
                          size="sm"
                          disabled={roster.busy || !isValidHandle(handle)}
                          onClick={() => handleAccept(invite, handle)}
                        >
                          Accept
                        </Button>
                        <IconButton
                          icon={<Trash2 size={15} />}
                          label={`Revoke invitation for ${invite.email}`}
                          disabled={roster.busy}
                          onClick={() =>
                            void act(
                              () => roster.revoke(invite.id),
                              `Invitation for ${invite.email} revoked.`,
                            )
                          }
                        />
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card as="section" className={styles.panel}>
          <CardHeader>
            <CardTitle level={3}>Work assignments</CardTitle>
          </CardHeader>
          <div className={styles.assignmentForm}>
            <Select
              label="Member"
              options={memberOptions}
              placeholder={memberOptions.length ? undefined : "No members yet"}
              value={assignment.memberId}
              onChange={(event) =>
                setAssignment((current) => ({
                  ...current,
                  memberId: event.target.value,
                }))
              }
            />
            <Input
              label="Challenge"
              placeholder="challenge-id"
              value={assignment.challengeId}
              onChange={(event) =>
                setAssignment((current) => ({
                  ...current,
                  challengeId: event.target.value,
                }))
              }
            />
            <Input
              label="Hours"
              type="number"
              min={0.5}
              max={24}
              step={0.5}
              value={assignment.hours}
              onChange={(event) =>
                setAssignment((current) => ({
                  ...current,
                  hours: event.target.value,
                }))
              }
            />
            <Button
              variant="secondary"
              icon={<ClipboardList size={15} />}
              onClick={handleAssign}
            >
              Assign
            </Button>
          </div>
          {assignmentError ? (
            <p className={styles.assignmentError} role="alert">
              {assignmentError}
            </p>
          ) : null}
          {roster.assignments.length === 0 ? (
            <p className={styles.emptyText}>No hours reserved yet.</p>
          ) : (
            <ul className={styles.assignmentList}>
              {roster.assignments.map((item) => (
                <li key={item.id} className={styles.assignmentRow}>
                  <span>
                    <strong>{item.challenge_id}</strong>
                    <span className={styles.meta}>
                      {roster.members.find(
                        (member) => member.id === item.member_id,
                      )?.handle ?? item.member_id}
                    </span>
                  </span>
                  <span className={styles.assignmentHours}>
                    {formatHours(item.hours)}
                  </span>
                  <IconButton
                    icon={<Trash2 size={14} />}
                    label={`Remove assignment for ${item.challenge_id}`}
                    disabled={roster.busy}
                    onClick={() =>
                      void act(
                        () => roster.release(item.id),
                        "Assignment released.",
                      )
                    }
                  />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <InviteDialog
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        onInvite={handleInvite}
        teams={teams}
        busy={roster.busy}
        error={roster.error}
      />
    </div>
  );
}
