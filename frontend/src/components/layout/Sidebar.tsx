/**
 * Sidebar navigation with the team selector.
 */

import {
  Activity,
  Flag,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Trophy,
  Users,
} from "lucide-react";
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

/** Props accepted by {@link Sidebar}. */
export interface SidebarProps {
  /** The currently active navigation entry. */
  active: NavigationId;
  /** Called when a navigation entry is activated. */
  onNavigate: (id: NavigationId) => void;
  /** Optional additional class applied to the sidebar. */
  className?: string;
}

/**
 * Render the dashboard sidebar.
 *
 * @param props - The component props.
 * @returns The sidebar element.
 */
export function Sidebar({ active, onNavigate, className }: SidebarProps) {
  const teams = useDashboardStore((state) => state.teams);
  const selectedTeamId = useDashboardStore((state) => state.selectedTeamId);
  const setSelectedTeam = useDashboardStore((state) => state.setSelectedTeam);
  const collapsed = usePreferencesStore((state) => state.sidebarCollapsed);
  const toggleSidebar = usePreferencesStore((state) => state.toggleSidebar);

  return (
    <aside
      className={cn(styles.sidebar, collapsed && styles.sidebarCollapsed, className)}
      aria-label="Primary navigation"
    >
      <nav className={styles.nav}>
        {NAVIGATION.map((entry) => {
          const Icon = entry.icon;
          const isActive = entry.id === active;
          const button = (
            <button
              key={entry.id}
              type="button"
              className={cn(styles.navItem, isActive && styles.navItemActive)}
              aria-current={isActive ? "page" : undefined}
              onClick={() => onNavigate(entry.id)}
            >
              <Icon size={16} aria-hidden="true" />
              <span className={styles.navLabel}>{entry.label}</span>
              {isActive ? <span className={styles.navIndicator} aria-hidden="true" /> : null}
            </button>
          );

          return collapsed ? (
            <Tooltip key={entry.id} content={entry.label} side="right">
              {button}
            </Tooltip>
          ) : (
            button
          );
        })}
      </nav>

      <div className={styles.teams}>
        {!collapsed ? <p className={styles.sectionLabel}>Teams</p> : null}
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
              <Badge tone="neutral" className={styles.teamBadge}>
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
        <span aria-hidden="true">{collapsed ? "»" : "«"}</span>
        {!collapsed ? <span>Collapse</span> : null}
      </button>
    </aside>
  );
}
