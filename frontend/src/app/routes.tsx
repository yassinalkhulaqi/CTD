/**
 * Route definitions of the dashboard.
 */

import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

/**
 * Build the route tree of the dashboard.
 *
 * The pages are loaded lazily so the initial bundle only contains the shell
 * and the overview screen.
 *
 * @returns The route objects.
 */
export function buildRoutes(): RouteObject[] {
  const OverviewPage = lazy(() => import("./pages/OverviewPage"));
  const ChallengesPage = lazy(() => import("./pages/ChallengesPage"));
  const MembersPage = lazy(() => import("./pages/MembersPage"));
  const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
  const ActivityPage = lazy(() => import("./pages/ActivityPage"));
  const SettingsPage = lazy(() => import("./pages/SettingsPage"));
  const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
  const GalleryPage = lazy(() => import("./pages/GalleryPage"));

  return [
    {
      path: "/",
      element: <OverviewPage />,
    },
    {
      path: "/challenges",
      element: <ChallengesPage />,
    },
    {
      path: "/challenges/:challengeId",
      element: <ChallengesPage />,
    },
    {
      path: "/members",
      element: <MembersPage />,
    },
    {
      path: "/analytics",
      element: <AnalyticsPage />,
    },
    {
      path: "/activity",
      element: <ActivityPage />,
    },
    {
      path: "/settings",
      element: <SettingsPage />,
    },
    {
      path: "/gallery",
      element: <GalleryPage />,
    },
    {
      path: "*",
      element: <NotFoundPage />,
    },
  ];
}

/** The navigation entries of the dashboard keyed by their route. */
export const NAVIGATION_ROUTES = {
  overview: "/",
  challenges: "/challenges",
  members: "/members",
  analytics: "/analytics",
  activity: "/activity",
  settings: "/settings",
  gallery: "/gallery",
} as const;

/** The identifier of a navigation entry. */
export type NavigationId = keyof typeof NAVIGATION_ROUTES;
