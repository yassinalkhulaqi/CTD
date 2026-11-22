/**
 * The routed activity timeline screen.
 */

import { Activity, RefreshCw } from "lucide-react";
import { Button, EmptyState, ErrorState, Skeleton } from "../../components/ui";
import { FilterChips } from "./components/FilterChips";
import { LiveBanner } from "./components/LiveBanner";
import { TimelineList } from "./components/TimelineList";
import { TimelineStatsView } from "./components/TimelineStats";
import { useTimeline } from "./hooks";
import { IMPORTANCE_ORDER, activeFilterCount } from "./logic";
import styles from "./TimelinePage.module.css";

/**
 * Render the timeline page with filters, live updates and grouped events.
 *
 * @returns The page element.
 */
export function TimelinePage() {
  const timeline = useTimeline();
  const filterCount = activeFilterCount({
    kinds: timeline.activeKinds,
    actors: timeline.activeActors,
    importance: timeline.activeImportance,
    teamId: timeline.teamId ?? undefined,
  });

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Activity timeline</h1>
          <p className={styles.subtitle}>
            Follow every solve, submission and team milestone in one live feed.
          </p>
        </div>
        <div className={styles.actions}>
          {timeline.page ? (
            <span className={styles.total}>
              {timeline.page.total} recorded events
            </span>
          ) : null}
          <Button
            variant="secondary"
            icon={<RefreshCw size={14} />}
            onClick={timeline.refresh}
          >
            Refresh
          </Button>
        </div>
      </header>

      <TimelineStatsView stats={timeline.stats} />

      <FilterChips
        kinds={timeline.kinds}
        activeKinds={timeline.activeKinds}
        importance={IMPORTANCE_ORDER}
        activeImportance={timeline.activeImportance}
        actors={timeline.actors}
        activeActors={timeline.activeActors}
        teams={timeline.teams}
        teamId={timeline.teamId}
        activeCount={filterCount}
        onToggleKind={timeline.toggleKind}
        onToggleImportance={timeline.toggleImportance}
        onToggleActor={timeline.toggleActor}
        onSelectTeam={timeline.setTeamId}
        onClear={timeline.clearFilters}
      />

      <LiveBanner
        count={timeline.pending}
        onShow={timeline.showNewEvents}
        onDismiss={timeline.dismissBanner}
      />

      {timeline.error ? (
        <ErrorState
          title="The timeline could not be loaded"
          message={timeline.error}
          onRetry={timeline.refresh}
        />
      ) : null}

      {timeline.loading ? (
        <div className={styles.loading} aria-label="Loading activity timeline">
          <Skeleton lines={5} height={16} />
          <Skeleton height={320} />
        </div>
      ) : timeline.buckets.length === 0 ? (
        <EmptyState
          icon={<Activity size={22} />}
          title="No activity yet"
          description="Team activity appears here as challenges are solved, notes are written and hints are unlocked."
          action={
            <Button variant="secondary" onClick={timeline.refresh}>
              Check again
            </Button>
          }
        />
      ) : (
        <TimelineList
          buckets={timeline.buckets}
          loadingMore={timeline.loadingMore}
          onDismiss={timeline.removeEvent}
          onLoadMore={timeline.page?.has_more ? timeline.loadMore : undefined}
        />
      )}
    </main>
  );
}
