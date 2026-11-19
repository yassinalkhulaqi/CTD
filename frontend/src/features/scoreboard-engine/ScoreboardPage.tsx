/**
 * Routed scoreboard page: podium, ranking, policy editor and history.
 */

import { useCallback, useState } from "react";
import { Camera, Trophy } from "lucide-react";
import {
  Button,
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  Select,
  Skeleton,
} from "../../components/ui";
import {
  useScoreboardActions,
  useScoreboardOverview,
  useTeamScoreboard,
} from "./hooks";
import { Podium } from "./components/Podium";
import { RankTable } from "./components/RankTable";
import { RuleEditor } from "./components/RuleEditor";
import { ScoreBreakdownChart } from "./components/ScoreBreakdown";
import { SnapshotHistory } from "./components/SnapshotHistory";
import styles from "./ScoreboardPage.module.css";

/**
 * Render the scoreboard feature page.
 *
 * @returns The page element.
 */
export function ScoreboardPage() {
  const overview = useScoreboardOverview();
  const { reload: reloadOverview } = overview;
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const activeTeamId = selectedTeamId ?? overview.teams[0]?.id ?? null;
  const team = useTeamScoreboard(activeTeamId, revision);

  const handleComplete = useCallback(() => {
    setRevision((value) => value + 1);
    reloadOverview();
  }, [reloadOverview]);

  const actions = useScoreboardActions(activeTeamId, handleComplete);

  const teamOptions = overview.teams.map((item) => ({
    value: item.id,
    label: item.name,
  }));

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}>
            <Trophy size={14} aria-hidden="true" /> Analysis
          </div>
          <h1 className={styles.heading}>Scoreboard</h1>
          <p className={styles.lede}>
            Live rankings, transparent scoring and a full history of every rank
            change.
          </p>
        </div>
        <div className={styles.headerActions}>
          <Select
            label="Team"
            hideLabel
            placeholder="Select a team"
            options={teamOptions}
            value={activeTeamId ?? ""}
            onChange={(event) => setSelectedTeamId(event.target.value)}
            className={styles.teamSelect}
          />
          <Button
            icon={<Camera size={15} />}
            onClick={() => void actions.captureSnapshot()}
            disabled={!activeTeamId}
            loading={actions.busy}
            loadingLabel="Capturing"
          >
            Capture snapshot
          </Button>
        </div>
      </header>

      {actions.notice ? (
        <p className={styles.notice} role="status">
          {actions.notice}
        </p>
      ) : null}
      {actions.error ? (
        <p className={styles.actionError} role="alert">
          {actions.error}
        </p>
      ) : null}

      {overview.loading ? (
        <div className={styles.loadingGrid} aria-label="Loading scoreboard">
          <Skeleton height={220} />
          <Skeleton height={320} />
          <Skeleton height={320} />
        </div>
      ) : overview.error ? (
        <ErrorState
          title="The scoreboard could not be loaded"
          message={overview.error}
          onRetry={overview.reload}
        />
      ) : overview.teams.length === 0 ? (
        <EmptyState
          title="No teams available"
          description="Create a team before computing a scoreboard ranking."
          icon={<Trophy size={22} />}
        />
      ) : (
        <div className={styles.content}>
          <section
            className={styles.podiumSection}
            aria-labelledby="podium-heading"
          >
            <h2 id="podium-heading" className={styles.sectionTitle}>
              The podium
            </h2>
            <Podium
              entries={overview.ranking?.entries ?? []}
              selectedTeamId={activeTeamId}
              onSelect={setSelectedTeamId}
            />
          </section>

          <div className={styles.columns}>
            <div className={styles.primary}>
              <Card as="section" className={styles.rankingCard}>
                <CardHeader
                  actions={
                    <span className={styles.cardMeta}>
                      {overview.ranking?.team_count ?? 0} teams · live
                    </span>
                  }
                >
                  <CardTitle>Live ranking</CardTitle>
                  <CardDescription>
                    Sorted by points, then solves, then earliest last solve.
                  </CardDescription>
                </CardHeader>
                <RankTable
                  entries={overview.ranking?.entries ?? []}
                  selectedTeamId={activeTeamId}
                  onSelect={setSelectedTeamId}
                />
              </Card>

              <ScoreBreakdownChart
                breakdown={team.breakdown}
                loading={team.loading}
              />
            </div>

            <aside
              className={styles.secondary}
              aria-label="Scoring controls and history"
            >
              {team.error ? (
                <ErrorState
                  title="Team data unavailable"
                  message={team.error}
                  onRetry={team.reload}
                />
              ) : (
                <>
                  <RuleEditor
                    rule={team.rule}
                    onSave={actions.saveRule}
                    saving={actions.busy}
                  />
                  <SnapshotHistory
                    snapshots={team.snapshots}
                    loading={team.loading}
                  />
                </>
              )}
            </aside>
          </div>
        </div>
      )}
    </div>
  );
}
