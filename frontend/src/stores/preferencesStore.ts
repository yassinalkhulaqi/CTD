/**
 * Preferences store: the UI preferences persisted across sessions.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { useShallow } from "zustand/react/shallow";
import type { Density, TimeWindow } from "./dashboardStore";

/** The state managed by the preferences store. */
export interface PreferencesState {
  /** Whether the sidebar is collapsed. */
  sidebarCollapsed: boolean;
  /** Whether the activity feed is pinned to the bottom. */
  activityFeedPinned: boolean;
  /** Whether the dashboard animates value changes. */
  animatedNumbers: boolean;
  /** The information density of the tables and boards. */
  density: Density;
  /** The analytics window. */
  timeWindow: TimeWindow;
  /** The number of rows rendered by the paginated tables. */
  pageSize: number;
  /** Toggle the collapsed state of the sidebar. */
  toggleSidebar: () => void;
  /** Set the collapsed state of the sidebar. */
  setSidebarCollapsed: (collapsed: boolean) => void;
  /** Toggle the pinned state of the activity feed. */
  toggleActivityFeed: () => void;
  /** Toggle the animated numbers. */
  toggleAnimatedNumbers: () => void;
  /** Set the information density. */
  setDensity: (density: Density) => void;
  /** Set the analytics window. */
  setTimeWindow: (window: TimeWindow) => void;
  /** Set the page size. */
  setPageSize: (size: number) => void;
  /** Restore the default preferences. */
  reset: () => void;
}

/** The default preferences of the dashboard. */
export const DEFAULT_PREFERENCES = {
  sidebarCollapsed: false,
  activityFeedPinned: true,
  animatedNumbers: true,
  density: "comfortable" as Density,
  timeWindow: "24h" as TimeWindow,
  pageSize: 25,
};

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      ...DEFAULT_PREFERENCES,

      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleActivityFeed: () =>
        set((state) => ({ activityFeedPinned: !state.activityFeedPinned })),
      toggleAnimatedNumbers: () =>
        set((state) => ({ animatedNumbers: !state.animatedNumbers })),
      setDensity: (density) => set({ density }),
      setTimeWindow: (timeWindow) => set({ timeWindow }),
      setPageSize: (pageSize) => set({ pageSize: Math.max(5, Math.min(pageSize, 200)) }),
      reset: () => set({ ...DEFAULT_PREFERENCES }),
    }),
    {
      name: "ctfd.preferences",
      version: 1,
      storage: createJSONStorage(() => window.localStorage),
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        activityFeedPinned: state.activityFeedPinned,
        animatedNumbers: state.animatedNumbers,
        density: state.density,
        timeWindow: state.timeWindow,
        pageSize: state.pageSize,
      }),
    },
  ),
);

/**
 * Return the preferences of the dashboard.
 *
 * @returns The persisted preferences.
 */
export function usePreferences(): Omit<
  PreferencesState,
  | "toggleSidebar"
  | "setSidebarCollapsed"
  | "toggleActivityFeed"
  | "toggleAnimatedNumbers"
  | "setDensity"
  | "setTimeWindow"
  | "setPageSize"
  | "reset"
> {
  return usePreferencesStore(
    useShallow((state) => ({
      sidebarCollapsed: state.sidebarCollapsed,
      activityFeedPinned: state.activityFeedPinned,
      animatedNumbers: state.animatedNumbers,
      density: state.density,
      timeWindow: state.timeWindow,
      pageSize: state.pageSize,
    })),
  );
}

/**
 * Return whether the dashboard should animate its numbers.
 *
 * @returns `true` when the animation is enabled.
 */
export function useAnimatedNumbers(): boolean {
  return usePreferencesStore((state) => state.animatedNumbers);
}

/**
 * Return the current information density.
 *
 * @returns The density.
 */
export function useDensity(): Density {
  return usePreferencesStore((state) => state.density);
}
