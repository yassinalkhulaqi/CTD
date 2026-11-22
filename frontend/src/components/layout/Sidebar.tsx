/**
 * Sidebar navigation with the team selector.
 */

import { Activity, Flag, LayoutDashboard, Settings, ShieldCheck, Trophy, Users, X } from "lucide-react";
import { cn } from "../../lib/utils";
import { useDashboardStore } from "../../stores/dashboardStore";
import { usePreferencesStore } from "../../stores/preferencesStore";
import { Avatar, Badge, Tooltip } from "../ui";
import styles from "./Sidebar.module.css";

/** The navigation entries of the dashboard. */
export const NAVIGATION = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "challenges", label: "Challenges", icon: Flag },
  { id: "members", label: "Members", icon: Users },
  { id: "analytics", label: "Analytics", icon: Trophy },
  { id: "activity", label: "Activity", icon: Activity },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "gallery", label: "Design system", icon: LayoutDashboard },
] as const;

/** The identifier of a navigation entry. */
export type NavigationId = (typeof NAVIGATION)[number]["id"];

const GROUPS: Array<{ label: string; ids: NavigationId[] }> = [
  { label: "Workspace", ids: ["overview", "challenges", "members"] },
  { label: "Insights", ids: ["analytics", "activity"] },
  { label: "System", ids: ["settings", "gallery"] },
];

/** Props accepted by {@link Sidebar}. */
export interface SidebarProps {
  /** The currently active navigation entry. */
  active: NavigationId;
  /** Called when a navigation entry is activated. */
  onNavigate: (id: NavigationId) => void;
  /** Whether the mobile drawer is open. */
  mobileOpen?: boolean;
  /** Called when the mobile drawer should close. */
  onClose?: () => void;
  /** Render every label regardless of the collapsed preference. */
  forceExpanded?: boolean;
  /** Optional additional class applied to the sidebar. */
  className?: string;
}

/**
 * Render the dashboard sidebar.
 *
 * @param props - The component props.
 * @returns The sidebar element.
 */
export function Sidebar({
  active,
  onNavigate,
  mobileOpen = false,
  onClose,
  forceExpanded = false,
  className,
}: SidebarProps) {
  const teams = useDashboardStore((state) => state.teams);
  const selectedTeamId = useDashboardStore((state) => state.selectedTeamId);
  const setSelectedTeam = useDashboardStore((state) => state.setSelectedTeam);
  const collapsedPreference = usePreferencesStore((state) => state.sidebarCollapsed);
  const collapsed = collapsedPreference && !forceExpanded;
  const toggleSidebar = usePreferencesStore((state) => state.toggleSidebar);

  const go = (id: NavigationId) => {
    onNavigate(id);
    onClose?.();
  };

  return (
    <aside
      className={cn(
        styles.sidebar,
        collapsed && styles.sidebarCollapsed,
        mobileOpen && styles.sidebarMobileOpen,
        className,
      )}
      aria-label="Primary navigation"
    >
      <div className={styles.brand}>
        <button type="button" className={styles.brandMark} onClick={() => go("overview")} aria-label="Go to overview">
          <ShieldCheck size={17} aria-hidden="true" />
        </button>
        {!collapsed ? (
          <div className={styles.brandText}>
            <span className={styles.brandName}>CTF Team</span>
            <span className={styles.brandMeta}>Dashboard</span>
          </div>
        ) : null}
        {onClose ? (
          <button type="button" className={styles.mobileClose} onClick={onClose} aria-label="Close navigation">
            <X size={16} aria-hidden="true" />
          </button>
        ) : null}
      </div>

      <nav className={styles.nav}>
        {GROUPS.map((group) => (
          <div key={group.label} className={styles.navGroup}>
            {!collapsed ? <p className={styles.sectionLabel}>{group.label}</p> : null}
            {group.ids.map((id) => {
              const entry = NAVIGATION.find((item) => item.id === id);
              if (!entry) return null;
              const Icon = entry.icon;
              const isActive = entry.id === active;
              const button = (
                <button
                  type="button"
                  className={cn(styles.navItem, isActive && styles.navItemActive)}
                  aria-current={isActive ? "page" : undefined}
                  onClick={() => go(entry.id)}
                >
                  <span className={styles.navIcon}>
                    <Icon size={16} aria-hidden="true" />
                  </span>
                  <span className={styles.navLabel}>{entry.label}</span>
                  {isActive ? <span className={styles.navIndicator} aria-hidden="true" /> : null}
                </button>
              );

              return collapsed ? (
                <Tooltip key={entry.id} content={entry.label} side="right">
                  {button}
                </Tooltip>
              ) : (
                <span key={entry.id} className={styles.navSlot}>
                  {button}
                </span>
              );
            })}
          </div>
        ))}
      </nav>

      <div className={styles.teams}>
        <div className={styles.teamsHeader}>
          {!collapsed ? <p className={styles.sectionLabel}>Teams</p> : null}
          {!collapsed && teams.length > 0 ? (
            <Badge tone="neutral" size="sm">
              {teams.length}
            </Badge>
          ) : null}
        </div>
        <button
          type="button"
          className={cn(styles.teamItem, selectedTeamId === null && styles.teamItemActive)}
          onClick={() => setSelectedTeam(null)}
        >
          <span className={styles.teamMark} aria-hidden="true">
            <ShieldCheck size={13} />
          </span>
          {!collapsed ? <span className={styles.teamName}>All teams</span> : null}
        </button>

        {teams.map((team) => (
          <button
            key={team.id}
            type="button"
            className={cn(styles.teamItem, selectedTeamId === team.id && styles.teamItemActive)}
            onClick={() => setSelectedTeam(team.id)}
          >
            <Avatar name={team.name} size="xs" color={team.color} />
            {!collapsed ? <span className={styles.teamName}>{team.name}</span> : null}
            {!collapsed ? (
              <Badge tone="neutral" size="sm" className={styles.teamBadge}>
                {team.initials}
              </Badge>
            ) : null}
          </button>
        ))}
      </div>

      <button
        type="button"
        className={styles.collapseButton}
        onClick={toggleSidebar}
        aria-label={collapsed ? "Expand the sidebar" : "Collapse the sidebar"}
      >
        <span className={styles.collapseIcon} aria-hidden="true">
          {collapsed ? "»" : "«"}
        </span>
        {!collapsed ? <span>Collapse</span> : null}
      </button>
    </aside>
  );
}
