/** Routed screen for browsing events and registering teams. */

import { useCallback, useEffect, useState } from "react";
import { CalendarRange, RefreshCw, ShieldAlert } from "lucide-react";
import { Button, EmptyState, ErrorState, Skeleton } from "../../components/ui";
import { eventsApi } from "./api";
import { EventCard } from "./components/EventCard";
import { EventDetail } from "./components/EventDetail";
import { EventFilters } from "./components/EventFilters";
import { EventStatsView } from "./components/EventStats";
import { RegistrationDialog } from "./components/RegistrationDialog";
import { useEventCatalogue, useNow } from "./hooks";
import type {
  CtfEvent,
  EventFormat,
  EventRegistration,
  EventTask,
  EventWindow,
} from "./types";
import { deriveEventStatus } from "./utils";
import styles from "./EventsPage.module.css";

/** The initial filter state of the catalogue. */
const INITIAL_COUNTS: Record<EventWindow, number> = {
  all: 0,
  draft: 0,
  upcoming: 0,
  live: 0,
  archived: 0,
};

/**
 * Render the events module page.
 *
 * @returns The events page.
 */
export function EventsPage() {
  const [windowFilter, setWindowFilter] = useState<EventWindow>("upcoming");
  const [format, setFormat] = useState<EventFormat | "all">("all");
  const [search, setSearch] = useState("");
  const catalogue = useEventCatalogue({ window: windowFilter, format, search });
  const now = useNow(1000);

  const [counts, setCounts] =
    useState<Record<EventWindow, number>>(INITIAL_COUNTS);
  const [reloadToken, setReloadToken] = useState(0);
  const [registerEvent, setRegisterEvent] = useState<CtfEvent | null>(null);
  const [detailEvent, setDetailEvent] = useState<CtfEvent | null>(null);
  const [tasks, setTasks] = useState<EventTask[]>([]);
  const [registrations, setRegistrations] = useState<EventRegistration[]>([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [busyTaskId, setBusyTaskId] = useState<string | null>(null);
  const [registering, setRegistering] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    eventsApi
      .list({ window: "all", limit: 500 })
      .then((list) => {
        if (!active) return;
        const next: Record<EventWindow, number> = {
          ...INITIAL_COUNTS,
          all: list.events.length,
        };
        for (const event of list.events) {
          next[deriveEventStatus(event, Date.now())] += 1;
        }
        setCounts(next);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [reloadToken]);

  const refreshAll = useCallback(() => {
    catalogue.refresh();
    setReloadToken((value) => value + 1);
  }, [catalogue]);

  const openDetails = useCallback(async (event: CtfEvent) => {
    setDetailEvent(event);
    setActionError(null);
    setTasksLoading(true);
    const [taskList, ledger] = await Promise.allSettled([
      eventsApi.tasks(event.id),
      eventsApi.registrations(event.id),
    ]);
    setTasks(taskList.status === "fulfilled" ? taskList.value : []);
    setRegistrations(
      ledger.status === "fulfilled" ? ledger.value.registrations : [],
    );
    setTasksLoading(false);
  }, []);

  const submitRegistration = useCallback(
    async (teamId: string) => {
      if (!registerEvent) return;
      setRegistering(true);
      setActionError(null);
      try {
        const registration = await eventsApi.register(registerEvent.id, teamId);
        setNotice(
          registration.is_waitlisted
            ? `Team ${teamId} joined the waitlist for ${registerEvent.name}.`
            : `Team ${teamId} is registered for ${registerEvent.name}.`,
        );
        setRegisterEvent(null);
        refreshAll();
      } catch (reason) {
        setActionError(
          reason instanceof Error ? reason.message : "Registration failed",
        );
      } finally {
        setRegistering(false);
      }
    },
    [registerEvent, refreshAll],
  );

  const toggleTask = useCallback(
    async (task: EventTask) => {
      setBusyTaskId(task.id);
      setTasks((current) =>
        current.map((item) =>
          item.id === task.id ? { ...item, done: !item.done } : item,
        ),
      );
      try {
        await eventsApi.toggleTask(task.event_id, task.id);
        refreshAll();
      } catch (reason) {
        setTasks((current) =>
          current.map((item) =>
            item.id === task.id ? { ...item, done: task.done } : item,
          ),
        );
        setActionError(
          reason instanceof Error ? reason.message : "Unable to update task",
        );
      } finally {
        setBusyTaskId(null);
      }
    },
    [refreshAll],
  );

  const clearFilters = () => {
    setWindowFilter("all");
    setFormat("all");
    setSearch("");
  };

  const filtered = catalogue.events.length > 0;
  const hasFilters =
    windowFilter !== "all" || format !== "all" || search.trim() !== "";

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Operations</p>
          <h1 className={styles.title}>CTF Events</h1>
          <p className={styles.subtitle}>
            Track upcoming competitions, live countdowns and team registrations.
          </p>
        </div>
        <Button
          variant="secondary"
          icon={<RefreshCw size={15} />}
          onClick={refreshAll}
          loading={catalogue.isLoading}
        >
          Refresh
        </Button>
      </header>

      <EventStatsView stats={catalogue.stats} loading={catalogue.isLoading} />

      <EventFilters
        value={windowFilter}
        format={format}
        search={search}
        counts={counts}
        onWindowChange={setWindowFilter}
        onFormatChange={setFormat}
        onSearchChange={setSearch}
      />

      {notice ? (
        <div className={styles.notice} role="status">
          {notice}
          <button
            type="button"
            onClick={() => setNotice(null)}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      ) : null}

      {actionError ? (
        <ErrorState
          title="The last action could not be completed"
          message={actionError}
          onRetry={() => setActionError(null)}
          retryLabel="Dismiss"
        />
      ) : null}

      {catalogue.error ? (
        <ErrorState
          title="Events could not be loaded"
          message={catalogue.error}
          onRetry={refreshAll}
        />
      ) : catalogue.isLoading ? (
        <div className={styles.grid} aria-label="Loading events">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton
              key={index}
              height={290}
              className={styles.skeletonCard}
            />
          ))}
        </div>
      ) : !filtered ? (
        <EmptyState
          icon={<CalendarRange size={24} />}
          title={
            hasFilters ? "No events match your filters" : "No events scheduled"
          }
          description={
            hasFilters
              ? "Try a different status, format or search term."
              : "Events created by the organisers will appear here."
          }
          action={
            hasFilters ? (
              <Button variant="secondary" onClick={clearFilters}>
                Clear filters
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className={styles.grid}>
          {catalogue.events.map((event) => (
            <EventCard
              key={event.id}
              event={event}
              now={now}
              stats={catalogue.stats.find((item) => item.event_id === event.id)}
              onRegister={setRegisterEvent}
              onDetails={(selected) => void openDetails(selected)}
            />
          ))}
        </div>
      )}

      <RegistrationDialog
        event={registerEvent}
        teams={catalogue.teams}
        open={registerEvent !== null}
        busy={registering}
        error={actionError}
        onClose={() => {
          setRegisterEvent(null);
          setActionError(null);
        }}
        onSubmit={(teamId) => void submitRegistration(teamId)}
      />

      <EventDetail
        event={detailEvent}
        open={detailEvent !== null}
        now={now}
        tasks={tasks}
        registrations={registrations}
        stats={catalogue.stats.find(
          (item) => item.event_id === detailEvent?.id,
        )}
        tasksLoading={tasksLoading}
        busyTaskId={busyTaskId}
        onClose={() => setDetailEvent(null)}
        onToggleTask={(task) => void toggleTask(task)}
      />

      <footer className={styles.footer}>
        <ShieldAlert size={14} aria-hidden="true" />
        Registration is randomised for offline practice events and does not
        grant CTF credentials.
      </footer>
    </div>
  );
}
