/**
 * Filter chips for timeline kinds, importance tiers, actors and teams.
 */

import { SlidersHorizontal, X } from "lucide-react";
import type { CSSProperties } from "react";
import { cn } from "../../../lib/utils";
import { IMPORTANCE_ORDER, KIND_OPTIONS, importanceLabel } from "../logic";
import type { ActorSummary, Importance } from "../types";
import styles from "./FilterChips.module.css";

/** Props accepted by {@link FilterChips}. */
export interface FilterChipsProps {
  kinds: string[];
  activeKinds: string[];
  importance: Importance[];
  activeImportance: Importance[];
  actors: ActorSummary[];
  activeActors: string[];
  teams: string[];
  teamId: string | null;
  activeCount: number;
  onToggleKind: (kind: string) => void;
  onToggleImportance: (tier: Importance) => void;
  onToggleActor: (actorId: string) => void;
  onSelectTeam: (teamId: string | null) => void;
  onClear: () => void;
}

/**
 * Render the filter control cluster above the timeline list.
 *
 * @param props - The filter state and callbacks.
 * @returns The filter bar element.
 */
export function FilterChips({
  kinds,
  activeKinds,
  importance,
  activeImportance,
  actors,
  activeActors,
  teams,
  teamId,
  activeCount,
  onToggleKind,
  onToggleImportance,
  onToggleActor,
  onSelectTeam,
  onClear,
}: FilterChipsProps) {
  const available =
    kinds.length > 0
      ? KIND_OPTIONS.filter((option) => kinds.includes(option.value))
      : KIND_OPTIONS;
  const visibleActors = actors.slice(0, 6);
  return (
    <section className={styles.filter} aria-label="Timeline filters">
      <div className={styles.group}>
        <span className={styles.label}>
          <SlidersHorizontal size={12} aria-hidden="true" /> Kind
        </span>
        <div className={styles.chips}>
          {available.map((option) => (
            <button
              key={option.value}
              type="button"
              className={cn(
                styles.chip,
                activeKinds.includes(option.value) && styles.chipActive,
              )}
              aria-pressed={activeKinds.includes(option.value)}
              aria-label={`Filter by ${option.label}`}
              style={{ "--chip-color": option.color } as CSSProperties}
              onClick={() => onToggleKind(option.value)}
            >
              <span className={styles.dot} aria-hidden="true" />
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.group}>
        <span className={styles.label}>Importance</span>
        <div className={styles.chips}>
          {IMPORTANCE_ORDER.map((tier) => (
            <button
              key={tier}
              type="button"
              className={cn(
                styles.chip,
                importance.includes(tier) && styles.chipActive,
                styles[tier],
              )}
              aria-pressed={activeImportance.includes(tier)}
              aria-label={`Filter by ${importanceLabel(tier)} importance`}
              onClick={() => onToggleImportance(tier)}
            >
              {importanceLabel(tier)}
            </button>
          ))}
        </div>
      </div>

      {visibleActors.length > 0 ? (
        <div className={styles.group}>
          <span className={styles.label}>Actors</span>
          <div className={styles.chips}>
            {visibleActors.map((actor) => (
              <button
                key={actor.actor_id}
                type="button"
                className={cn(
                  styles.chip,
                  activeActors.includes(actor.actor_id) && styles.chipActive,
                )}
                aria-pressed={activeActors.includes(actor.actor_id)}
                aria-label={`Filter by ${actor.label}`}
                onClick={() => onToggleActor(actor.actor_id)}
              >
                {actor.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {teams.length > 1 ? (
        <label className={styles.team}>
          <span className={styles.label}>Team</span>
          <select
            className={styles.select}
            value={teamId ?? ""}
            aria-label="Filter by team"
            onChange={(event) => onSelectTeam(event.target.value || null)}
          >
            <option value="">All teams</option>
            {teams.map((team) => (
              <option key={team} value={team}>
                {team}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {activeCount > 0 ? (
        <button
          type="button"
          className={styles.clear}
          onClick={onClear}
          aria-label="Clear all timeline filters"
        >
          <X size={12} aria-hidden="true" /> Clear ({activeCount})
        </button>
      ) : null}
    </section>
  );
}
