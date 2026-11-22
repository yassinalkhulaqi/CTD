/**
 * The team members page.
 */

import { useMemo, useState } from "react";
import { Activity, Radio, Trophy, Users } from "lucide-react";
import { useContributions, useMembers } from "../../api/resources";
import { useActiveTeamId } from "../../stores/dashboardStore";
import { formatNumber, formatRelativeTime } from "../../lib/utils";
import {
  Avatar,
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  SegmentedControl,
  Skeleton,
  StatCard,
  VirtualTable,
} from "../../components/ui";
import type { Presence } from "../../types";
import styles from "./MembersPage.module.css";

type SortMode = "points" | "solves" | "name";

const SORT_OPTIONS = [
  { value: "points" as const, label: "Points" },
  { value: "solves" as const, label: "Solves" },
  { value: "name" as const, label: "Name" },
];

const ROLE_TONES: Record<string, "neutral" | "accent" | "info" | "warning"> = {
  viewer: "neutral",
  analyst: "info",
  lead: "accent",
  admin: "warning",
};

/**
 * Render the team members page.
 *
 * @returns The page element.
 */
export default function MembersPage() {
  const teamId = useActiveTeamId();
  const [sort, setSort] = useState<SortMode>("points");

  const members = useMembers(teamId ? { teamId } : {}, { staleTime: 20_000 });
  const contributions = useContributions(teamId ? { teamId } : {}, {
    staleTime: 20_000,
  });

  const contributionById = useMemo(() => {
    const map = new Map<string, { solves: number; points: number }>();
    for (const contribution of contributions.data ?? []) {
      map.set(contribution.member_id, {
        solves: contribution.solves,
        points: contribution.points,
      });
    }
    return map;
  }, [contributions.data]);

  const rows = useMemo(() => {
    const list = [...(members.data ?? [])];
    list.sort((left, right) => {
      if (sort === "name")
        return left.display_name.localeCompare(right.display_name);
      const leftStats = contributionById.get(left.id);
      const rightStats = contributionById.get(right.id);
      if (sort === "solves") {
        return (rightStats?.solves ?? 0) - (leftStats?.solves ?? 0);
      }
      return (rightStats?.points ?? 0) - (leftStats?.points ?? 0);
    });
    return list;
  }, [members.data, contributionById, sort]);

  const online = rows.filter((member) => member.is_online).length;
  const totals = useMemo(() => {
    let solves = 0;
    let points = 0;
    for (const stats of contributionById.values()) {
      solves += stats.solves;
      points += stats.points;
    }
    return { solves, points };
  }, [contributionById]);

  if (members.error) {
    return (
      <ErrorState
        title="The member list could not be loaded"
        message={
          members.error instanceof Error
            ? members.error.message
            : "Unknown error"
        }
        onRetry={() => void members.refetch()}
      />
    );
  }

  return (
    <div className={styles.page}>
      <section className={styles.stats} aria-label="Roster summary">
        <StatCard
          label="Members"
          value={formatNumber(rows.length)}
          icon={<Users size={16} />}
          accent="#6366f1"
          meta="on the active roster"
          loading={!members.data}
        />
        <StatCard
          label="Online now"
          value={formatNumber(online)}
          icon={<Activity size={16} />}
          accent="#34d399"
          meta="available to pick up work"
          loading={!members.data}
        />
        <StatCard
          label="Solves"
          value={formatNumber(totals.solves)}
          icon={<Radio size={16} />}
          accent="#22d3ee"
          meta="recorded by this team"
          loading={!contributions.data}
        />
        <StatCard
          label="Points"
          value={formatNumber(totals.points)}
          icon={<Trophy size={16} />}
          accent="#f59e0b"
          meta="across every member"
          loading={!contributions.data}
        />
      </section>

      <Card>
        <CardHeader
          actions={
            <div className={styles.headerActions}>
              <Badge tone="success" dot>
                {online} online
              </Badge>
              <SegmentedControl
                options={SORT_OPTIONS}
                value={sort}
                onValueChange={setSort}
                label="Sort members"
              />
            </div>
          }
        >
          <CardTitle>Team members</CardTitle>
        </CardHeader>
        <CardContent>
          {!members.data ? (
            <div className={styles.skeletons}>
              <Skeleton height={36} />
              <Skeleton height={36} />
              <Skeleton height={36} />
            </div>
          ) : rows.length === 0 ? (
            <EmptyState
              icon={<Users size={22} />}
              title="No members yet"
              description="Invite the analysts of this team to see them here."
            />
          ) : (
            <VirtualTable
              rows={rows}
              rowKey={(member) => member.id}
              rowHeight={52}
              height={480}
              label="Team members and contributions"
              emptyMessage="No members to show."
              columns={[
                {
                  key: "rank",
                  header: "#",
                  render: (member) => (
                    <span className={styles.rank}>{rows.indexOf(member) + 1}</span>
                  ),
                },
                {
                  key: "member",
                  header: "Member",
                  render: (member) => (
                    <span className={styles.memberCell}>
                      <Avatar
                        name={member.display_name}
                        size="sm"
                        presence={member.presence as Presence}
                      />
                      <span className={styles.memberName}>
                        <span className={styles.memberLabel}>
                          {member.display_name}
                        </span>
                        <span className={styles.memberHandle}>
                          @{member.handle}
                        </span>
                      </span>
                    </span>
                  ),
                },
                {
                  key: "role",
                  header: "Role",
                  render: (member) => (
                    <Badge tone={ROLE_TONES[member.role] ?? "neutral"}>
                      {member.role}
                    </Badge>
                  ),
                },
                {
                  key: "presence",
                  header: "Presence",
                  render: (member) => (
                    <span
                      className={styles.presence}
                      data-presence={member.is_online ? "online" : "offline"}
                    >
                      <span className={styles.presenceDot} aria-hidden="true" />
                      {member.presence}
                    </span>
                  ),
                },
                {
                  key: "solves",
                  header: "Solves",
                  align: "right",
                  render: (member) =>
                    formatNumber(contributionById.get(member.id)?.solves ?? 0),
                },
                {
                  key: "points",
                  header: "Points",
                  align: "right",
                  render: (member) =>
                    formatNumber(contributionById.get(member.id)?.points ?? 0),
                },
                {
                  key: "joined",
                  header: "Joined",
                  align: "right",
                  render: (member) => formatRelativeTime(member.joined_at),
                },
              ]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
