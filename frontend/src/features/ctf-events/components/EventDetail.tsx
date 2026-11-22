/** Detail drawer with checklist, registrations and event metadata. */

import {
  CalendarDays,
  CheckCircle2,
  Globe2,
  ListChecks,
  Users,
} from "lucide-react";
import {
  Badge,
  Checkbox,
  Divider,
  Drawer,
  EmptyState,
  Progress,
  Skeleton,
} from "../../../components/ui";
import {
  deriveEventStatus,
  FORMAT_LABELS,
  formatEventWindow,
  STATUS_LABELS,
  statusTone,
} from "../utils";
import type {
  CtfEvent,
  EventRegistration,
  EventStats,
  EventTask,
} from "../types";
import styles from "./EventDetail.module.css";

/** Props accepted by {@link EventDetail}. */
export interface EventDetailProps {
  event: CtfEvent | null;
  open: boolean;
  now: number;
  tasks: EventTask[];
  registrations: EventRegistration[];
  stats?: EventStats;
  tasksLoading?: boolean;
  busyTaskId?: string | null;
  onClose: () => void;
  onToggleTask: (task: EventTask) => void;
}

/**
 * Render the detail drawer for one event.
 *
 * @param props - The component props.
 * @returns The drawer element, or `null` when closed.
 */
export function EventDetail({
  event,
  open,
  now,
  tasks,
  registrations,
  stats,
  tasksLoading = false,
  busyTaskId = null,
  onClose,
  onToggleTask,
}: EventDetailProps) {
  if (event === null) return null;
  const status = deriveEventStatus(event, now);
  const done = tasks.filter((task) => task.done).length;

  return (
    <Drawer open={open} onClose={onClose} title={event.name} width={480}>
      <div className={styles.body}>
        <div className={styles.hero}>
          <Badge tone={statusTone(status)} dot pulse={status === "live"}>
            {STATUS_LABELS[status]}
          </Badge>
          <span className={styles.format}>{FORMAT_LABELS[event.format]}</span>
        </div>

        <p className={styles.description}>
          {event.description ||
            "No description has been added for this event yet."}
        </p>

        <dl className={styles.facts}>
          <div className={styles.fact}>
            <dt>
              <CalendarDays size={14} aria-hidden="true" /> Window
            </dt>
            <dd>{formatEventWindow(event)}</dd>
          </div>
          <div className={styles.fact}>
            <dt>
              <Users size={14} aria-hidden="true" /> Capacity
            </dt>
            <dd>
              {stats?.confirmed ?? 0} confirmed / {event.max_team_size} teams
              {stats && stats.waitlisted > 0
                ? ` · ${stats.waitlisted} waiting`
                : ""}
            </dd>
          </div>
          {event.website_url ? (
            <div className={styles.fact}>
              <dt>
                <Globe2 size={14} aria-hidden="true" /> Website
              </dt>
              <dd>
                <a href={event.website_url} target="_blank" rel="noreferrer">
                  Visit event site
                </a>
              </dd>
            </div>
          ) : null}
        </dl>

        {stats ? (
          <div className={styles.fill}>
            <Progress
              value={stats.fill_percentage}
              tone={status === "live" ? "success" : "accent"}
              label="Registration fill"
            />
            <span>{stats.fill_percentage}% full</span>
          </div>
        ) : null}

        {event.tags.length > 0 ? (
          <div className={styles.tags} aria-label="Event tags">
            {event.tags.map((tag) => (
              <span key={tag} className={styles.tag}>
                #{tag}
              </span>
            ))}
          </div>
        ) : null}

        <Divider />

        <section className={styles.section} aria-label="Event checklist">
          <h3 className={styles.sectionTitle}>
            <ListChecks size={16} aria-hidden="true" />
            Checklist
            <span className={styles.count}>
              {done}/{tasks.length}
            </span>
          </h3>
          {tasksLoading ? (
            <Skeleton lines={3} />
          ) : tasks.length === 0 ? (
            <EmptyState
              title="No tasks yet"
              description="Checklist items added by the organisers will appear here."
            />
          ) : (
            <ul className={styles.tasks}>
              {tasks.map((task) => (
                <li
                  key={task.id}
                  className={task.done ? styles.taskDone : undefined}
                >
                  <Checkbox
                    checked={task.done}
                    disabled={busyTaskId === task.id}
                    onChange={() => onToggleTask(task)}
                  >
                    {task.title}
                  </Checkbox>
                  {task.is_overdue ? (
                    <span className={styles.overdue}>Overdue</span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>

        <Divider />

        <section className={styles.section} aria-label="Registered teams">
          <h3 className={styles.sectionTitle}>
            <Users size={16} aria-hidden="true" />
            Teams
            <span className={styles.count}>{registrations.length}</span>
          </h3>
          {registrations.length === 0 ? (
            <EmptyState
              title="No registrations"
              description="Be the first team to sign up."
            />
          ) : (
            <ul className={styles.registrations}>
              {registrations.map((registration) => (
                <li key={registration.id} className={styles.registration}>
                  <span>{registration.team_id}</span>
                  <Badge
                    tone={registration.is_confirmed ? "success" : "warning"}
                  >
                    {registration.status}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
          {done === tasks.length && tasks.length > 0 ? (
            <p className={styles.ready}>
              <CheckCircle2 size={15} aria-hidden="true" /> Checklist complete
            </p>
          ) : null}
        </section>
      </div>
    </Drawer>
  );
}
