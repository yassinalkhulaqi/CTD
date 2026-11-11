/**
 * Activity store: the live feed of dashboard events.
 */

import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";
import type { ActivityEvent, EventKind } from "../types";

/** The maximum number of events kept in the feed. */
export const MAX_ACTIVITY_EVENTS = 200;

/** The state managed by the activity store. */
export interface ActivityState {
  /** The events shown in the feed, newest first. */
  events: ActivityEvent[];
  /** The number of events that arrived while the tab was hidden. */
  missedCount: number;
  /** Whether the feed is currently paused. */
  paused: boolean;
  /** The kind filter applied to the feed. */
  kindFilter: EventKind | "all";
  /** Prepend an event to the feed. */
  push: (event: ActivityEvent) => void;
  /** Prepend a batch of events to the feed. */
  pushMany: (events: ActivityEvent[]) => void;
  /** Replace the whole feed. */
  replace: (events: ActivityEvent[]) => void;
  /** Remove every event from the feed. */
  clear: () => void;
  /** Pause or resume the feed. */
  setPaused: (paused: boolean) => void;
  /** Toggle the paused state of the feed. */
  togglePaused: () => void;
  /** Set the kind filter. */
  setKindFilter: (kind: EventKind | "all") => void;
  /** Reset the counter of missed events. */
  acknowledgeMissed: () => void;
}

/**
 * Return whether an event matches the current filter.
 *
 * @param event - The event to test.
 * @param filter - The active filter.
 * @returns `true` when the event should be shown.
 */
export function matchesFilter(event: ActivityEvent, filter: EventKind | "all"): boolean {
  return filter === "all" || event.kind === filter;
}

export const useActivityStore = create<ActivityState>()((set) => ({
  events: [],
  missedCount: 0,
  paused: false,
  kindFilter: "all",

  push: (event) =>
    set((state) => {
      if (state.paused) return { missedCount: state.missedCount + 1 };
      const next = [event, ...state.events];
      return {
        events: next.length > MAX_ACTIVITY_EVENTS ? next.slice(0, MAX_ACTIVITY_EVENTS) : next,
        missedCount: 0,
      };
    }),

  pushMany: (incoming) =>
    set((state) => {
      if (incoming.length === 0) return {};
      if (state.paused) return { missedCount: state.missedCount + incoming.length };
      const next = [...incoming.reverse(), ...state.events];
      return {
        events: next.length > MAX_ACTIVITY_EVENTS ? next.slice(0, MAX_ACTIVITY_EVENTS) : next,
        missedCount: 0,
      };
    }),

  replace: (events) => set({ events: events.slice(0, MAX_ACTIVITY_EVENTS), missedCount: 0 }),
  clear: () => set({ events: [], missedCount: 0 }),
  setPaused: (paused) => set({ paused }),
  togglePaused: () => set((state) => ({ paused: !state.paused })),
  setKindFilter: (kindFilter) => set({ kindFilter }),
  acknowledgeMissed: () => set({ missedCount: 0 }),
}));

/**
 * Return the events matching the active filter.
 *
 * @returns The filtered events.
 */
export function useFilteredActivity(): ActivityEvent[] {
  return useActivityStore(
    useShallow((state) => state.events.filter((event) => matchesFilter(event, state.kindFilter))),
  );
}

/**
 * Return the summary counters of the activity feed.
 *
 * @returns The counters.
 */
export function useActivitySummary(): { total: number; missed: number; paused: boolean } {
  return useActivityStore(
    useShallow((state) => ({
      total: state.events.length,
      missed: state.missedCount,
      paused: state.paused,
    })),
  );
}

/**
 * Return the number of solves recorded in the feed.
 *
 * @returns The number of solve events.
 */
export function useSolveEventCount(): number {
  return useActivityStore(
    useShallow(
      (state) => state.events.filter((event) => event.kind === "solve.created").length,
    ),
  );
}
