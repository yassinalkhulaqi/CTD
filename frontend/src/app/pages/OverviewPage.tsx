/**
 * The competition overview page.
 */

import { useMemo } from "react";
import { ArrowUpRight, Flag, RefreshCw, ShieldCheck, Target, Trophy, Users } from "lucide-react";
import { useChallenges, useDashboardSnapshot, useMembers } from "../../api/resources";
import { Link } from "react-router-dom";
import { useActiveTeamId } from "../../stores/dashboardStore";
import { formatNumber, formatPercent } from "../../lib/utils";
import {
  Avatar,
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  Button,
  Progress,
  ScoreRing,
  Skeleton,
  StatCard,
} from "../../components/ui";
import styles from "./OverviewPage.module.css";

/**
 * Render the competition overview.
 *
 * @returns The page element.
 */
export default function OverviewPage() {
  const teamId = useActiveTeamId();
  const snapshot = useDashboardSnapshot(teamId ?? undefined, { staleTime: 10_000 });
  const members = useMembers(teamId ? { teamId } : {}, { staleTime: 30_000 });
  const challenges = useChallenges(
    teamId ? { teamId } : {},
    { staleTime: 15_000 },
  );

  const overview = snapshot.data?.overview;
  const categories = useMemo(() => snapshot.data?.categories ?? [], [snapshot.data]);
  const contributions = useMemo(
    () => snapshot.data?.contributions ?? [],
    [snapshot.data],
  );

  const maxChallenges = useMemo(
    () => Math.max(1, ...categories.map((entry) => entry.challenges)),
    [categories],
  );

  if (snapshot.error) {
    return (
      <ErrorState
        title="The dashboard could not be loaded"
        message={snapshot.error instanceof Error ? snapshot.error.message : "Unknown error"}
        onRetry={() => void snapshot.refetch()}
      />
    );
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero} aria-label="Competition summary">
        <div className={styles.heroBody}>
          <span className={styles.heroEyebrow}>
            <span className={styles.heroPulse} aria-hidden="true" />
            Live competition
          </span>
          <h2 className={styles.heroTitle}>
            {overview
              ? `${formatPercent(overview.completion_rate, 0)} of the board cleared`
              : "Reading the scoreboard?"}
          </h2>
          <p className={styles.heroText}>
            {overview
              ? `${formatNumber(overview.solved_challenges)} of ${formatNumber(overview.challenges)} challenges solved for ${formatNumber(overview.total_points)} points across ${formatNumber(overview.teams)} teams.`
              : "The headline numbers appear as soon as the event feed responds."}
          </p>
          <div className={styles.heroActions}>
            <Link to="/challenges" className={styles.heroCta}>
              Open challenge board
              <ArrowUpRight size={14} aria-hidden="true" />
            </Link>
            <Button
              variant="ghost"
              size="sm"
              icon={<RefreshCw size={14} />}
              onClick={() => void snapshot.refetch()}
              loading={snapshot.isFetching}
              loadingLabel="Refreshing"
            >
              Refresh
            </Button>
          </div>
        </div>
        <div className={styles.heroSide}>
          <div className={styles.heroMeter}>
            <span className={styles.heroMeterLabel}>Completion</span>
            <span className={styles.heroMeterValue}>
              {formatPercent(overview?.completion_rate ?? 0, 0)}
            </span>
            <Progress
              value={overview?.completion_rate ?? 0}
              max={1}
              tone="accent"
              label="Overall completion"
            />
          </div>
          <dl className={styles.heroStats}>
            <div>
              <dt>Solved</dt>
              <dd>{formatNumber(overview?.solved_challenges ?? 0)}</dd>
            </div>
            <div>
              <dt>Online</dt>
              <dd>{formatNumber(overview?.active_members ?? 0)}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className={styles.stats} aria-label="Headline statistics">
        <StatCard
          label="Teams"
          value={overview ? formatNumber(overview.teams) : <Skeleton width={48} height={30} />}
          icon={<ShieldCheck size={16} />}
          accent="#6366f1"
          loading={!overview}
          meta="competing in this event"
        />
        <StatCard
          label="Solves"
          value={overview ? formatNumber(overview.solves) : <Skeleton width={48} height={30} />}
          icon={<Flag size={16} />}
          accent="#22d3ee"
          loading={!overview}
          meta={`${formatNumber(overview?.solved_challenges ?? 0)} challenges cleared`}
        />
        <StatCard
          label="Members online"
          value={overview ? formatNumber(overview.active_members) : <Skeleton width={48} height={30} />}
          icon={<Users size={16} />}
          accent="#34d399"
          loading={!overview}
          meta={`of ${formatNumber(overview?.members ?? 0)} members`}
        />
        <StatCard
          label="Points scored"
          value={overview ? formatNumber(overview.total_points) : <Skeleton width={48} height={30} />}
          icon={<Trophy size={16} />}
          accent="#f59e0b"
          loading={!overview}
          meta="across every team"
        />
      </section>

      <div className={styles.grid}>
        <Card className={styles.spanTwo}>
          <CardHeader>
            <CardTitle>Category progress</CardTitle>
          </CardHeader>
          <CardContent>
            {categories.length === 0 ? (
              <EmptyState
                icon={<Target size={22} />}
                title="No challenges yet"
                description="Create the first challenge to see the category breakdown."
              />
            ) : (
              <ul className={styles.categories}>
                {categories.map((entry) => (
                  <li key={entry.category} className={styles.category}>
                    <span
                      className={styles.categoryDot}
                      style={{ background: entry.accent }}
                      aria-hidden="true"
                    />
                    <span className={styles.categoryLabel}>{entry.label}</span>
                    <Progress
                      value={entry.challenges}
                      max={maxChallenges}
                      tone="accent"
                      label={`${entry.label} challenges`}
                      className={styles.categoryProgress}
                    />
                    <span className={styles.categoryValue}>
                      {entry.solves}/{entry.challenges}
                    </span>
                    <Badge tone={entry.solve_rate >= 0.6 ? "success" : "neutral"}>
                      {formatPercent(entry.solve_rate, 0)}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Completion</CardTitle>
          </CardHeader>
          <CardContent className={styles.completion}>
            <ScoreRing value={overview?.completion_rate ?? 0} size={92} strokeWidth={8} />
            <p className={styles.completionMeta}>
              {overview
                ? `${formatNumber(overview.solved_challenges)} of ${formatNumber(overview.challenges)} challenges solved`
                : "Loading the competition progress…"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top contributors</CardTitle>
          </CardHeader>
          <CardContent>
            {contributions.length === 0 ? (
              <EmptyState
                icon={<Users size={22} />}
                title="No contributions yet"
                description="The leaderboard appears once the first flag is recorded."
              />
            ) : (
              <ul className={styles.contributions}>
                {contributions.slice(0, 6).map((row, index) => (
                  <li key={row.member_id} className={styles.contribution}>
                    <span className={styles.contributionRank}>{index + 1}</span>
                    <Avatar name={row.display_name} size="sm" />
                    <span className={styles.contributionName}>{row.display_name}</span>
                    <span className={styles.contributionPoints}>{formatNumber(row.points)}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className={styles.spanTwo}>
          <CardHeader>
            <CardTitle>Open challenges</CardTitle>
          </CardHeader>
          <CardContent>
            {challenges.data && challenges.data.length > 0 ? (
              <ul className={styles.challenges}>
                {challenges.data
                  .filter((challenge) => challenge.status !== "solved")
                  .slice(0, 6)
                  .map((challenge) => (
                    <li key={challenge.id} className={styles.challengeItem}>
                      <Link to={`/challenges/${challenge.id}`} className={styles.challenge}>
                        <div className={styles.challengeMain}>
                          <span className={styles.challengeTitle}>{challenge.title}</span>
                          <span className={styles.challengeMeta}>
                            {challenge.category} · {challenge.difficulty}
                          </span>
                        </div>
                        <Badge
                          tone={
                            challenge.status === "active"
                              ? "accent"
                              : challenge.status === "locked"
                                ? "danger"
                                : "neutral"
                          }
                        >
                          {challenge.status}
                        </Badge>
                        <span className={styles.challengePoints}>
                          {formatNumber(challenge.points)} pts
                        </span>
                        <ArrowUpRight size={14} className={styles.challengeArrow} aria-hidden="true" />
                      </Link>
                    </li>
                  ))}
              </ul>
            ) : (
              <EmptyState
                icon={<Flag size={22} />}
                title="Nothing left to solve"
                description="Every challenge of this team has been cleared."
              />
            )}
          </CardContent>
        </Card>
      </div>

      {members.data ? (
        <p className={styles.footer}>
          {members.data.length} members loaded from the competition API.
        </p>
      ) : null}
    </div>
  );
}
