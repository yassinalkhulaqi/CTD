/**
 * The application shell: sidebar, top bar and the routed content.
 */

import { Suspense, useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { ActivityFeed } from "../components/layout/ActivityFeed";
import { Sidebar, type NavigationId } from "../components/layout/Sidebar";
import { TopBar } from "../components/layout/TopBar";
import { Spinner } from "../components/ui";
import { useDashboardSnapshot } from "../api/resources";
import { useHydrateDashboard } from "../hooks/useDashboardData";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { useActivityStore } from "../stores/activityStore";
import { NAVIGATION_ROUTES } from "./routes";
import styles from "./AppShell.module.css";

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Competition overview", subtitle: "Live scores, momentum and team focus" },
  "/challenges": { title: "Challenge board", subtitle: "Track, filter and solve every challenge" },
  "/members": { title: "Team members", subtitle: "Roster, roles and individual form" },
  "/analytics": { title: "Analytics", subtitle: "Trends across categories and time" },
  "/activity": { title: "Activity feed", subtitle: "Everything the team has done, in order" },
  "/settings": { title: "Settings", subtitle: "Workspace, team and account preferences" },
  "/gallery": { title: "Design system", subtitle: "The primitives this interface is built from" },
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
  const isMobile = useMediaQuery("(max-width: 900px)");
  const [navOpen, setNavOpen] = useState(false);

  const active = useMemo(() => navigationFor(location.pathname), [location.pathname]);
  const page = PAGE_TITLES[location.pathname] ?? {
    title: "Challenge detail",
    subtitle: "Everything known about this challenge",
  };

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

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!isMobile) {
      setNavOpen(false);
      return;
    }
    if (!navOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [isMobile, navOpen]);

  return (
    <div className={styles.shell}>
      <a href="#main-content" className={styles.skipLink}>
        Skip to content
      </a>

      <Sidebar
        active={active}
        onNavigate={(id) => navigate(NAVIGATION_ROUTES[id])}
        mobileOpen={navOpen}
        onClose={isMobile ? () => setNavOpen(false) : undefined}
        forceExpanded={isMobile}
      />

      {isMobile && navOpen ? (
        <button
          type="button"
          className={styles.backdrop}
          aria-label="Close navigation"
          onClick={() => setNavOpen(false)}
        />
      ) : null}

      <div className={styles.workspace}>
        <div className={styles.content}>
          <TopBar
            title={page.title}
            subtitle={page.subtitle}
            onOpenNavigation={isMobile ? () => setNavOpen(true) : undefined}
          />
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
          <div className={styles.asideHeader}>
            <h2 className={styles.asideTitle}>Live activity</h2>
            <Link to="/activity" className={styles.asideLink}>
              View all
              <ArrowUpRight size={13} aria-hidden="true" />
            </Link>
          </div>
          <ActivityFeed loading={!snapshot.data} limit={8} />
          {members.data ? (
            <p className={styles.asideMeta}>{members.data.length} members loaded</p>
          ) : null}
        </aside>
      </div>
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
