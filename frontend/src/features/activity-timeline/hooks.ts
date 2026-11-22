/**
 * Data loading, live updates and filter state for the timeline screen.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { timelineApi } from "./api";
import { mergeClusters, newEventsSince } from "./logic";
import type {
  ActorSummary,
  EventCluster,
  Importance,
  TimelineBucket,
  TimelineCreatePayload,
  TimelineEvent,
  TimelinePage,
  TimelineQuery,
  TimelineStats,
} from "./types";

/** Interval between background checks for new activity. */
export const POLL_INTERVAL_MS = 15_000;

/** Number of raw events requested per page. */
export const PAGE_SIZE = 50;

/**
 * Extract a display message from an unknown failure.
 *
 * @param error - The caught value.
 * @param fallback - Message used for non-error values.
 * @returns The message to show.
 */
function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

/** The state and actions exposed by {@link useTimeline}. */
export interface TimelineController {
  page: TimelinePage | null;
  buckets: TimelineBucket[];
  stats: TimelineStats | null;
  actors: ActorSummary[];
  clusters: EventCluster[];
  teams: string[];
  loading: boolean;
  loadingMore: boolean;
  error: string | null;
  kinds: string[];
  activeKinds: string[];
  activeActors: string[];
  activeImportance: Importance[];
  teamId: string | null;
  pending: number;
  toggleKind: (kind: string) => void;
  toggleActor: (actorId: string) => void;
  toggleImportance: (tier: Importance) => void;
  setTeamId: (teamId: string | null) => void;
  clearFilters: () => void;
  refresh: () => void;
  loadMore: () => void;
  showNewEvents: () => void;
  dismissBanner: () => void;
  removeEvent: (id: string) => void;
  record: (payload: TimelineCreatePayload) => Promise<void>;
}

/**
 * Manage timeline data, filters, pagination and the live arrival banner.
 *
 * @returns The controller consumed by the page component.
 */
export function useTimeline(): TimelineController {
  const [filters, setFilters] = useState<TimelineQuery>({
    limit: PAGE_SIZE,
    offset: 0,
  });
  const [page, setPage] = useState<TimelinePage | null>(null);
  const [buckets, setBuckets] = useState<TimelineBucket[]>([]);
  const [stats, setStats] = useState<TimelineStats | null>(null);
  const [actors, setActors] = useState<ActorSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(0);
  const latestIdRef = useRef<string | null>(null);
  const liveRef = useRef(true);

  const load = useCallback(async (query: TimelineQuery) => {
    setLoading(true);
    setError(null);
    try {
      const [nextPage, nextBuckets, nextStats, nextActors] = await Promise.all([
        timelineApi.listEvents(query),
        timelineApi.getGroups(query),
        timelineApi.getStats(query),
        timelineApi.getActors(query.teamId),
      ]);
      setPage(nextPage);
      setBuckets(nextBuckets);
      setStats(nextStats);
      setActors(nextActors);
      const newest = nextPage.events[0]?.id ?? null;
      if (latestIdRef.current === null) latestIdRef.current = newest;
    } catch (cause) {
      setError(messageOf(cause, "Unable to load the activity timeline"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(filters);
  }, [filters, load]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (!liveRef.current || document.visibilityState === "hidden") return;
      void timelineApi
        .listEvents({ ...filters, limit: PAGE_SIZE, offset: 0 })
        .then((fresh) => {
          const arrivals = newEventsSince(fresh.events, latestIdRef.current);
          if (arrivals.length === 0) return;
          setPending((current) => current + arrivals.length);
          latestIdRef.current = arrivals[0].id;
        })
        .catch(() => {
          liveRef.current = false;
        });
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [filters]);

  const refresh = useCallback(() => {
    setPending(0);
    latestIdRef.current = null;
    liveRef.current = true;
    void load(filters);
  }, [filters, load]);

  const toggleValue = useCallback(
    (key: "kinds" | "actors" | "importance", value: string) => {
      setFilters((current) => {
        const existing = (current[key] ?? []) as string[];
        const next = existing.includes(value)
          ? existing.filter((item) => item !== value)
          : [...existing, value];
        return { ...current, [key]: next, offset: 0 };
      });
    },
    [],
  );

  const toggleKind = useCallback(
    (kind: string) => toggleValue("kinds", kind),
    [toggleValue],
  );
  const toggleActor = useCallback(
    (actorId: string) => toggleValue("actors", actorId),
    [toggleValue],
  );
  const toggleImportance = useCallback(
    (tier: Importance) => toggleValue("importance", tier),
    [toggleValue],
  );

  const setTeamId = useCallback((teamId: string | null) => {
    setFilters((current) => ({
      ...current,
      teamId: teamId ?? undefined,
      offset: 0,
    }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({ limit: PAGE_SIZE, offset: 0 });
  }, []);

  const loadMore = useCallback(() => {
    if (!page?.next_offset || loadingMore) return;
    const offset = page.next_offset;
    setLoadingMore(true);
    setError(null);
    void Promise.all([
      timelineApi.listEvents({ ...filters, offset }),
      timelineApi.getGroups({ ...filters, limit: offset + PAGE_SIZE }),
    ])
      .then(([nextPage, nextBuckets]) => {
        setPage((current) => {
          if (!current) return nextPage;
          const clusters = mergeClusters(current.clusters, nextPage.clusters);
          return {
            ...current,
            clusters,
            events: clusters.map((cluster) => cluster.event),
            offset,
            has_more: nextPage.has_more,
            next_offset: nextPage.next_offset,
          };
        });
        setBuckets(nextBuckets);
      })
      .catch((cause: unknown) => {
        setError(messageOf(cause, "Unable to load more activity"));
      })
      .finally(() => setLoadingMore(false));
  }, [filters, loadingMore, page]);

  const showNewEvents = useCallback(() => {
    setPending(0);
    latestIdRef.current = null;
    liveRef.current = true;
    void load(filters);
  }, [filters, load]);

  const dismissBanner = useCallback(() => {
    setPending(0);
    liveRef.current = false;
  }, []);

  const removeEvent = useCallback(
    (id: string) => {
      setPage((current) => {
        if (!current) return current;
        const clusters = current.clusters.filter(
          (cluster) => cluster.id !== id,
        );
        return {
          ...current,
          clusters,
          events: clusters.map((cluster) => cluster.event),
          total: Math.max(0, current.total - 1),
        };
      });
      setBuckets((current) =>
        current.map((bucket) => ({
          ...bucket,
          children: bucket.children.map((child) => ({
            ...child,
            events: child.events.filter((cluster) => cluster.id !== id),
          })),
        })),
      );
      void timelineApi
        .deleteEvent(id)
        .then(() => timelineApi.getStats(filters))
        .then(setStats)
        .catch((cause: unknown) => {
          setError(messageOf(cause, "Unable to remove the event"));
          refresh();
        });
    },
    [filters, refresh],
  );

  const record = useCallback(
    async (payload: TimelineCreatePayload) => {
      await timelineApi.createEvent(payload);
      refresh();
    },
    [refresh],
  );

  const clusters = useMemo(() => page?.clusters ?? [], [page]);
  const teams = useMemo(
    () =>
      Array.from(
        new Set(
          (page?.events ?? []).map((event: TimelineEvent) => event.team_id),
        ),
      ).sort(),
    [page],
  );
  const kinds = useMemo(
    () =>
      Array.from(
        new Set((page?.events ?? []).map((event) => event.kind)),
      ).sort(),
    [page],
  );

  return {
    page,
    buckets,
    stats,
    actors,
    clusters,
    teams,
    loading,
    loadingMore,
    error,
    kinds,
    activeKinds: filters.kinds ?? [],
    activeActors: filters.actors ?? [],
    activeImportance: (filters.importance ?? []) as Importance[],
    teamId: filters.teamId ?? null,
    pending,
    toggleKind,
    toggleActor,
    toggleImportance,
    setTeamId,
    clearFilters,
    refresh,
    loadMore,
    showNewEvents,
    dismissBanner,
    removeEvent,
    record,
  };
}
