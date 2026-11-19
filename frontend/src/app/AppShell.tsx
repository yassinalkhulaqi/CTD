/**
 * The application shell: sidebar, top bar and the routed content.
 */

import { Suspense, useMemo } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ActivityFeed } from "../components/layout/ActivityFeed";
import { Sidebar, type NavigationId } from "../components/layout/Sidebar";
import { TopBar } from "../components/layout/TopBar";
import { Spinner } from "../components/ui";
import { useDashboardSnapshot } from "../api/resources";
import { useHydrateDashboard } from "../hooks/useDashboardData";
import { useActivityStore } from "../stores/activityStore";
import { discoverPlugins, pluginForPath } from "../features/plugins";
import { NAVIGATION_ROUTES } from "./routes";
import styles from "./AppShell.module.css";

const PAGE_TITLES: Record<string, string> = {
  "/": "Competition overview",
  "/challenges": "Challenge board",
  "/members": "Team members",
  "/analytics": "Analytics",
  "/activity": "Activity feed",
  "/settings": "Settings",
  "/gallery": "Design system",
};

/**
 * Derive the navigation entry matching a pathname.
 *
 * @param pathname - The current location.
 * @returns The navigation entry.
 */
export function navigationFor(pathname: string): NavigationId {
  if (pathname.startsWith("/challenges")) return "challenges";
  if (pathname.startsWith("/members")) return "members";
  if (pathname.startsWith("/analytics")) return "analytics";
  if (pathname.startsWith("/activity")) return "activity";
  if (pathname.startsWith("/settings")) return "settings";
  if (pathname.startsWith("/gallery")) return "gallery";
  return "overview";
}

/**
 * Render the routed application shell.
 *
 * @returns The shell element.
 */
export function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const active = useMemo(
    () => navigationFor(location.pathname),
    [location.pathname],
  );
  const plugins = useMemo(() => discoverPlugins(), []);
  const activePlugin = useMemo(
    () => pluginForPath(location.pathname),
    [location.pathname],
  );
  const title =
    activePlugin?.label ?? PAGE_TITLES[location.pathname] ?? "Dashboard";

  const snapshot = useDashboardSnapshot(undefined, { refetchInterval: 30_000 });
  const { members } = useHydrateDashboard();
  const pushEvents = useActivityStore((state) => state.pushMany);

  useMemo(() => {
    if (!snapshot.data?.recent_events?.length) return;
    pushEvents(
      snapshot.data.recent_events.map((event) => ({
        id: event.id,
        team_id: event.team_id,
        kind: event.kind,
        payload: event.payload,
        occurred_at: event.occurred_at,
      })),
    );
  }, [pushEvents, snapshot.data]);

  return (
    <div className={styles.shell}>
      <Sidebar
        active={active}
        onNavigate={(id) => navigate(NAVIGATION_ROUTES[id])}
      />
      <div className={styles.content}>
        <TopBar title={title} />
        {plugins.length > 0 ? (
          <nav className={styles.modules} aria-label="Feature modules">
            <span className={styles.modulesLabel}>Modules</span>
            <div className={styles.moduleLinks}>
              {plugins.map((plugin) => (
                <NavLink
                  key={plugin.id}
                  to={plugin.path}
                  title={plugin.description}
                  className={({ isActive }) =>
                    isActive ? styles.moduleLinkActive : styles.moduleLink
                  }
                >
                  {plugin.label}
                </NavLink>
              ))}
            </div>
          </nav>
        ) : null}
        <main className={styles.main} id="main-content">
          <Suspense
            fallback={
              <div className={styles.loading}>
                <Spinner size={22} label="Loading the view" />
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </main>
      </div>

      <aside className={styles.aside} aria-label="Live activity">
        <h2 className={styles.asideTitle}>Live activity</h2>
        <ActivityFeed loading={!snapshot.data} limit={8} />
        {members.data ? (
          <p className={styles.asideMeta}>
            {members.data.length} members loaded
          </p>
        ) : null}
      </aside>
    </div>
  );
}

/**
 * Render a navigation link bound to a route.
 *
 * @param props - The component props.
 * @returns The link element.
 */
export function NavigationLink({
  id,
  children,
}: {
  id: NavigationId;
  children: React.ReactNode;
}) {
  return (
    <NavLink to={NAVIGATION_ROUTES[id]} end={id === "overview"}>
      {children}
    </NavLink>
  );
}
