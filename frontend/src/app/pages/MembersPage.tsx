/**
 * The team members page.
 */

import { useMemo, useState } from "react";
import { Radio, Users } from "lucide-react";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
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
  const contributions = useContributions(teamId ? { teamId } : {}, { staleTime: 20_000 });

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
      if (sort === "name") return left.display_name.localeCompare(right.display_name);
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

  if (members.error) {
    return (
      <ErrorState
        title="The member list could not be loaded"
        message={members.error instanceof Error ? members.error.message : "Unknown error"}
        onRetry={() => void members.refetch()}
      />
    );
  }

  return (
    <div className={styles.page}>
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
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Member</TableHeaderCell>
                  <TableHeaderCell>Role</TableHeaderCell>
                  <TableHeaderCell>Presence</TableHeaderCell>
                  <TableHeaderCell align="right">Solves</TableHeaderCell>
                  <TableHeaderCell align="right">Points</TableHeaderCell>
                  <TableHeaderCell align="right">Joined</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((member) => {
                  const stats = contributionById.get(member.id);
                  return (
                    <TableRow key={member.id}>
                      <TableCell>
                        <span className={styles.memberCell}>
                          <Avatar
                            name={member.display_name}
                            size="sm"
                            presence={member.presence as Presence}
                          />
                          <span className={styles.memberName}>
                            <span className={styles.memberLabel}>{member.display_name}</span>
                            <span className={styles.memberHandle}>@{member.handle}</span>
                          </span>
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge tone={ROLE_TONES[member.role] ?? "neutral"}>{member.role}</Badge>
                      </TableCell>
                      <TableCell>
                        <span className={styles.presence}>
                          <Radio size={12} aria-hidden="true" />
                          {member.presence}
                        </span>
                      </TableCell>
                      <TableCell align="right">{formatNumber(stats?.solves ?? 0)}</TableCell>
                      <TableCell align="right">{formatNumber(stats?.points ?? 0)}</TableCell>
                      <TableCell align="right">
                        {formatRelativeTime(member.joined_at)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
