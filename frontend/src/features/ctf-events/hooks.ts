/** Data loading hooks for the events page. */

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../api/client";
import { eventsApi } from "./api";
import type {
  CtfEvent,
  EventFormat,
  EventStats,
  EventWindow,
  TeamOption,
} from "./types";

/** Filters that control the catalogue request. */
export interface CatalogueFilters {
  window: EventWindow;
  search: string;
  format: EventFormat | "all";
}

/** State returned by {@link useEventCatalogue}. */
export interface EventCatalogueState {
  events: CtfEvent[];
  stats: EventStats[];
  teams: TeamOption[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Load events, their statistics and the team list in parallel.
 *
 * Requests are cancelled when the filters change or the component unmounts.
 * A failure of the optional statistics or team requests does not hide the
 * catalogue, which remains the primary content of the screen.
 *
 * @param filters - The active catalogue filters.
 * @returns The catalogue state and a refresh callback.
 */
export function useEventCatalogue(
  filters: CatalogueFilters,
): EventCatalogueState {
  const [events, setEvents] = useState<CtfEvent[]>([]);
  const [stats, setStats] = useState<EventStats[]>([]);
  const [teams, setTeams] = useState<TeamOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const refresh = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setIsLoading(true);
    setError(null);

    const query = {
      window: filters.window,
      search: filters.search.trim() || undefined,
      format: filters.format === "all" ? undefined : filters.format,
    };

    async function load(): Promise<void> {
      const [eventsResult, statsResult, teamsResult] = await Promise.allSettled(
        [
          eventsApi.list(query, { signal: controller.signal }),
          eventsApi.allStats({ signal: controller.signal }),
          eventsApi.teams({ signal: controller.signal }),
        ],
      );
      if (!active || controller.signal.aborted) return;

      if (eventsResult.status === "rejected") {
        const reason = eventsResult.reason;
        setError(
          reason instanceof ApiError ? reason.message : "Unable to load events",
        );
        setEvents([]);
      } else {
        setEvents(eventsResult.value.events);
      }
      if (statsResult.status === "fulfilled") {
        setStats(statsResult.value.events);
      }
      if (teamsResult.status === "fulfilled") {
        setTeams(teamsResult.value);
      }
      setIsLoading(false);
    }

    void load();
    return () => {
      active = false;
      controller.abort();
    };
  }, [filters.window, filters.search, filters.format, revision]);

  return { events, stats, teams, isLoading, error, refresh };
}

/**
 * Return a timestamp that advances on an interval for live countdowns.
 *
 * @param intervalMs - The update interval in milliseconds.
 * @returns The current epoch time in milliseconds.
 */
export function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
  return now;
}
