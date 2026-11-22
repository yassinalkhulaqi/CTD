/** The routed hint workspace page. */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Coins, Lightbulb, Layers3 } from "lucide-react";
import {
  EmptyState,
  ErrorState,
  Select,
  Skeleton,
  Spinner,
} from "../../components/ui";
import {
  BudgetMeter,
  CostCurve,
  HintCard,
  HintLedgerView,
  UnlockDialog,
} from "./components";
import { useHintCatalog, useHintWorkspace } from "./hooks";
import { formatCredits } from "./hints";
import type { HintSelection, HintView } from "./types";
import styles from "./HintsPage.module.css";

/**
 * Render the hint ladder, budget meter and reveal ledger.
 *
 * @returns The hint workspace page.
 */
export function HintsPage() {
  const catalog = useHintCatalog();
  const [teamId, setTeamId] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [memberId, setMemberId] = useState("");
  const [selection, setSelection] = useState<HintSelection | null>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const workspace = useHintWorkspace(teamId, challengeId, memberId);
  const { unlock, resetBudget, refresh } = workspace;

  useEffect(() => {
    if (!teamId && catalog.teams.length > 0) setTeamId(catalog.teams[0].id);
  }, [catalog.teams, teamId]);

  const teamChallenges = useMemo(
    () =>
      catalog.challenges.filter((challenge) => challenge.team_id === teamId),
    [catalog.challenges, teamId],
  );
  const teamMembers = useMemo(
    () => catalog.members.filter((member) => member.team_id === teamId),
    [catalog.members, teamId],
  );

  useEffect(() => {
    if (!teamChallenges.some((challenge) => challenge.id === challengeId)) {
      setChallengeId(teamChallenges[0]?.id ?? "");
    }
  }, [teamChallenges, challengeId]);

  useEffect(() => {
    if (!teamMembers.some((member) => member.id === memberId)) {
      setMemberId(teamMembers[0]?.id ?? "");
    }
  }, [teamMembers, memberId]);

  const openUnlock = useCallback(
    (hint: HintView, origin: HTMLElement | null) => {
      setDialogError(null);
      setSelection({ hint, origin });
    },
    [],
  );

  const closeDialog = useCallback(() => setSelection(null), []);

  const confirmUnlock = useCallback(async () => {
    if (!selection) return;
    try {
      await unlock(selection.hint.hint_id, memberId, teamId);
      setSelection(null);
      setActionError(null);
    } catch (reason) {
      setDialogError(
        reason instanceof Error ? reason.message : "Unlock failed",
      );
    }
  }, [selection, unlock, memberId, teamId]);

  const handleReset = useCallback(async () => {
    try {
      await resetBudget(teamId);
      setActionError(null);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Reset failed");
    }
  }, [resetBudget, teamId]);

  const budget = workspace.view?.budget ?? null;
  const teamLabel = catalog.teams.find((team) => team.id === teamId)?.name;
  const challengeLabel = teamChallenges.find(
    (item) => item.id === challengeId,
  )?.title;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <span className={styles.kicker}>Workspace / Hints</span>
          <h1 className={styles.title}>Tiered hints</h1>
          <p className={styles.subtitle}>
            Spend a shared budget to reveal progressive nudges. Each tier builds
            on the previous one and gets more expensive.
          </p>
        </div>
        <div className={styles.headline} aria-label="Hint summary">
          <span className={styles.headlineIcon} aria-hidden="true">
            <Lightbulb size={18} />
          </span>
          <span>
            <strong>{workspace.view?.unlocked_count ?? 0}</strong>
            <small>revealed</small>
          </span>
        </div>
      </header>

      {catalog.error ? (
        <ErrorState
          title="The hint catalogue could not be loaded"
          message={catalog.error}
          onRetry={catalog.reload}
        />
      ) : null}

      {catalog.loading ? (
        <div className={styles.loading}>
          <Skeleton height={40} lines={2} />
          <Skeleton height={220} />
        </div>
      ) : catalog.teams.length === 0 || teamChallenges.length === 0 ? (
        <EmptyState
          icon={<Layers3 size={22} />}
          title="No challenge available"
          description="Hints need at least one team with a challenge in the competition."
        />
      ) : (
        <>
          <section className={styles.selectors} aria-label="Hint filters">
            <Select
              label="Team"
              value={teamId}
              onChange={(event) => setTeamId(event.target.value)}
              options={catalog.teams.map((team) => ({
                value: team.id,
                label: team.name,
              }))}
            />
            <Select
              label="Challenge"
              value={challengeId}
              onChange={(event) => setChallengeId(event.target.value)}
              options={teamChallenges.map((challenge) => ({
                value: challenge.id,
                label: challenge.title,
              }))}
            />
            <Select
              label="Unlocking member"
              value={memberId}
              onChange={(event) => setMemberId(event.target.value)}
              options={teamMembers.map((member) => ({
                value: member.id,
                label: member.display_name || member.handle,
              }))}
            />
          </section>

          {actionError ? (
            <ErrorState
              title="Budget action failed"
              message={actionError}
              onRetry={() => void handleReset()}
              retryLabel="Retry reset"
            />
          ) : null}

          {workspace.error ? (
            <ErrorState
              title="The hint ladder could not be loaded"
              message={workspace.error}
              onRetry={refresh}
            />
          ) : null}

          <div className={styles.layout}>
            <aside className={styles.side}>
              <BudgetMeter
                budget={budget}
                teamLabel={teamLabel}
                resetting={workspace.working}
                onReset={() => void handleReset()}
              />
              <CostCurve points={workspace.view?.curve ?? []} compact />
            </aside>

            <section className={styles.hints} aria-label="Hint ladder">
              <div className={styles.sectionHead}>
                <h2>{challengeLabel ?? "Challenge"}</h2>
                <span className={styles.budgetNote}>
                  <Coins size={14} aria-hidden="true" />
                  {formatCredits(budget?.remaining ?? 0)} credits available
                </span>
              </div>
              {workspace.loading && !workspace.view ? (
                <div className={styles.loading} role="status">
                  <Spinner label="Loading hints" />
                </div>
              ) : workspace.view && workspace.view.hints.length > 0 ? (
                <div className={styles.cards}>
                  {workspace.view.hints.map((hint) => (
                    <HintCard
                      key={hint.hint_id}
                      hint={hint}
                      budget={budget}
                      busy={
                        workspace.working &&
                        selection?.hint.hint_id === hint.hint_id
                      }
                      onUnlock={openUnlock}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={<Lightbulb size={22} />}
                  title="No hints authored"
                  description="This challenge does not have a hint ladder yet."
                />
              )}
              <HintLedgerView
                ledger={workspace.ledger}
                loading={workspace.loading}
              />
            </section>
          </div>
        </>
      )}

      <UnlockDialog
        open={selection !== null}
        hint={selection?.hint ?? null}
        budget={budget}
        busy={workspace.working}
        error={dialogError}
        onClose={closeDialog}
        onConfirm={() => void confirmUnlock()}
      />
    </div>
  );
}
