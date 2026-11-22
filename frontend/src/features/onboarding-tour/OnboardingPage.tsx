/**
 * The routed onboarding page: setup wizard, guided tour and checklist.
 */

import { useCallback, useMemo, useState } from "react";
import { Info, Map } from "lucide-react";
import { Badge, ErrorState, Kbd, Skeleton } from "../../components/ui";
import {
  ChecklistPanel,
  EmptyState,
  ProgressBanner,
  StepCard,
  TourOverlay,
  WizardStepper,
} from "./components";
import {
  useCompleteStep,
  useOnboarding,
  useResetOnboarding,
  useSkipStep,
  useToggleChecklistItem,
} from "./hooks";
import { buildTourFrame, isResolved, orderedSteps } from "./tour";
import type { OnboardingStep } from "./types";
import styles from "./OnboardingPage.module.css";

/** The open-mode user whose onboarding state is edited by this screen. */
const USER_ID = "demo-user";

/**
 * Render the onboarding wizard screen.
 *
 * @returns The page element.
 */
export default function OnboardingPage() {
  const { steps, progress, isLoading, error, refetch } = useOnboarding(USER_ID);
  const complete = useCompleteStep(USER_ID);
  const skip = useSkipStep(USER_ID);
  const toggle = useToggleChecklistItem(USER_ID);
  const reset = useResetOnboarding(USER_ID);
  const [tourStepId, setTourStepId] = useState<string | null>(null);
  const [pendingItem, setPendingItem] = useState<string | null>(null);

  const ordered = useMemo(() => orderedSteps(steps), [steps]);
  const frame = useMemo(
    () => buildTourFrame(ordered, tourStepId),
    [ordered, tourStepId],
  );
  const unresolvedIndex = ordered.findIndex((step) => !isResolved(step));
  const activeIndex =
    frame?.index ??
    (unresolvedIndex >= 0 ? unresolvedIndex : Math.max(0, ordered.length - 1));

  const handleStart = useCallback(() => {
    const next = ordered.find((step) => !isResolved(step));
    setTourStepId(next?.id ?? ordered[0]?.id ?? null);
  }, [ordered]);

  const handleResume = useCallback(() => {
    const slug = progress?.resume.next_step_slug;
    const next =
      ordered.find((step) => step.slug === slug) ??
      ordered.find((step) => !isResolved(step));
    setTourStepId(next?.id ?? null);
  }, [ordered, progress]);

  const handleRestart = useCallback(() => {
    const perform = async () => {
      await reset.mutate();
      setTourStepId(null);
    };
    void perform();
  }, [reset]);

  const handleSelect = useCallback(
    (index: number) => {
      const step = ordered[index];
      if (step) setTourStepId(step.id);
    },
    [ordered],
  );

  const handleSpotlight = useCallback((step: OnboardingStep) => {
    setTourStepId(step.id);
  }, []);

  const handleComplete = useCallback(
    (step: OnboardingStep) => {
      const perform = async () => {
        await complete.mutate({ stepId: step.id });
      };
      void perform();
    },
    [complete],
  );

  const handleSkip = useCallback(
    (step: OnboardingStep) => {
      const perform = async () => {
        await skip.mutate({ stepId: step.id });
      };
      void perform();
    },
    [skip],
  );

  const handleToggle = useCallback(
    (itemId: string, done: boolean) => {
      setPendingItem(itemId);
      const perform = async () => {
        await toggle.mutate({ itemId, done });
        setPendingItem(null);
      };
      void perform();
    },
    [toggle],
  );

  const handleNext = useCallback(() => {
    if (!frame) return;
    if (frame.isLast) {
      setTourStepId(null);
      return;
    }
    const next = ordered[frame.index + 1];
    if (next) setTourStepId(next.id);
  }, [frame, ordered]);

  const handleBack = useCallback(() => {
    if (!frame) return;
    const previous = ordered[frame.index - 1];
    if (previous) setTourStepId(previous.id);
  }, [frame, ordered]);

  const handleClose = useCallback(() => setTourStepId(null), []);
  const handleRetry = useCallback(() => {
    void refetch();
  }, [refetch]);

  const mutationError =
    complete.error ?? skip.error ?? toggle.error ?? reset.error;
  const errorMessage =
    error instanceof Error
      ? error.message
      : mutationError instanceof Error
        ? mutationError.message
        : error || mutationError
          ? "The onboarding service could not be reached."
          : null;

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.kicker}>Settings / Onboarding</p>
          <h2 className={styles.heading}>A guided start for every teammate</h2>
          <p className={styles.subheading}>
            Follow the wizard, spotlight each surface and tick off the setup
            checklist at your own pace.
          </p>
        </div>
        <div className={styles.headerMeta}>
          <Badge tone="accent" outline dot>
            {ordered.length} steps
          </Badge>
          <span className={styles.shortcut}>
            <Kbd>→</Kbd> next <Kbd>←</Kbd> back
          </span>
        </div>
      </header>

      {errorMessage ? (
        <ErrorState
          title="The tour could not be loaded"
          message={errorMessage}
          onRetry={handleRetry}
        />
      ) : null}

      {isLoading && steps.length === 0 ? (
        <div className={styles.loading} aria-label="Loading onboarding">
          <Skeleton lines={6} />
        </div>
      ) : ordered.length === 0 ? (
        <EmptyState
          variant="compass"
          title="No tour steps available"
          description="The onboarding catalogue is empty. Reload to try again."
          actionLabel="Reload steps"
          onAction={handleRetry}
        />
      ) : (
        <>
          <ProgressBanner
            percent={progress?.percent ?? 0}
            completed={progress?.completed ?? 0}
            total={progress?.total ?? ordered.length}
            status={progress?.status ?? "not-started"}
            resume={progress?.resume ?? null}
            checklist={progress?.checklist ?? null}
            onStart={handleStart}
            onResume={handleResume}
            onRestart={handleRestart}
            busy={reset.isPending}
          />

          {progress?.welcome_note ? (
            <aside className={styles.note} aria-label="Welcome note">
              <Info size={17} aria-hidden="true" />
              <div>
                <strong>{progress.welcome_note.title}</strong>
                <p>{progress.welcome_note.body}</p>
              </div>
              <Badge
                tone={
                  progress.welcome_note.tone === "tip" ? "warning" : "accent"
                }
              >
                {progress.welcome_note.tone}
              </Badge>
            </aside>
          ) : null}

          <div className={styles.layout}>
            <div className={styles.primary}>
              <section className={styles.stepperCard} aria-label="Wizard steps">
                <WizardStepper
                  steps={ordered}
                  activeIndex={activeIndex}
                  onSelect={handleSelect}
                />
              </section>
              <div className={styles.cards}>
                {ordered.map((step) => (
                  <StepCard
                    key={step.id}
                    step={step}
                    state={step.state ?? "available"}
                    isCurrent={activeIndex === ordered.indexOf(step)}
                    onComplete={handleComplete}
                    onSkip={handleSkip}
                    onSpotlight={handleSpotlight}
                    busy={complete.isPending || skip.isPending}
                  />
                ))}
              </div>
            </div>
            <aside className={styles.sidebar} aria-label="Setup progress">
              <ChecklistPanel
                checklist={progress?.checklist ?? null}
                onToggle={handleToggle}
                busyItemId={pendingItem}
                loading={isLoading}
              />
              <div className={styles.helpCard}>
                <Map size={18} aria-hidden="true" />
                <div>
                  <strong>Need a hand?</strong>
                  <p>
                    Replay any step from the stepper. Skipping is always
                    reversible by resetting your progress.
                  </p>
                </div>
              </div>
            </aside>
          </div>
        </>
      )}

      {frame ? (
        <TourOverlay
          step={frame.step}
          index={frame.index}
          total={frame.total}
          isFirst={frame.isFirst}
          isLast={frame.isLast}
          onNext={handleNext}
          onBack={handleBack}
          onClose={handleClose}
        />
      ) : null}
    </div>
  );
}
