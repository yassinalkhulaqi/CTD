/**
 * Barrel export for the dashboard state stores.
 */

export {
  useActiveFilterCount,
  useActiveTeamId,
  useDashboardStore,
  useOnlineMemberCount,
  useSelectedTeam,
  useSelectedTeamMembers,
  windowToHours,
} from "./dashboardStore";
export type { DashboardState, Density, TimeWindow } from "./dashboardStore";

export {
  DEFAULT_PREFERENCES,
  useAnimatedNumbers,
  useDensity,
  usePreferences,
  usePreferencesStore,
} from "./preferencesStore";
export type { PreferencesState } from "./preferencesStore";

export {
  MAX_ACTIVITY_EVENTS,
  matchesFilter,
  useActivityStore,
  useActivitySummary,
  useFilteredActivity,
  useSolveEventCount,
} from "./activityStore";
export type { ActivityState } from "./activityStore";

export {
  MAX_NOTIFICATIONS,
  useNotificationStore,
  useNotifications,
} from "./notificationStore";
export type { Notification, NotificationState, NotificationTone } from "./notificationStore";
