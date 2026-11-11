/**
 * React bindings for the realtime channel.
 */

import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useActivityStore } from "../stores/activityStore";
import { useDashboardStore } from "../stores/dashboardStore";
import { RealtimeClient, type ConnectionState, type EventPayload } from "./socket";

/** The value exposed by the realtime context. */
export interface RealtimeContextValue {
  /** The lifecycle of the connection. */
  state: ConnectionState;
  /** The number of events received since the connection was opened. */
  received: number;
  /** Force a reconnection. */
  reconnect: () => void;
  /** Narrow the stream to a team. */
  setScope: (teamId: string | null) => void;
}

const RealtimeContext = createContext<RealtimeContextValue | null>(null);

/**
 * Read the realtime context.
 *
 * @returns The realtime context.
 * @throws When used outside of a {@link RealtimeProvider}.
 */
export function useRealtime(): RealtimeContextValue {
  const context = useContext(RealtimeContext);
  if (!context) {
    throw new Error("useRealtime must be used inside a <RealtimeProvider>");
  }
  return context;
}

/** Props accepted by {@link RealtimeProvider}. */
export interface RealtimeProviderProps {
  /** The application tree the provider wraps. */
  children: ReactNode;
  /** Disable the connection entirely. */
  enabled?: boolean;
  /** The base URL of the API. */
  baseUrl?: string;
}

/**
 * Maintain the realtime connection and dispatch the events to the stores.
 *
 * @param props - The component props.
 * @returns The provider element.
 */
export function RealtimeProvider({ children, enabled = true, baseUrl }: RealtimeProviderProps) {
  const [state, setState] = useState<ConnectionState>("idle");
  const [received, setReceived] = useState(0);
  const clientRef = useRef<RealtimeClient | null>(null);
  const pushEvent = useActivityStore((state) => state.push);
  const selectedTeamId = useDashboardStore((state) => state.selectedTeamId);

  useEffect(() => {
    if (!enabled) return;

    const client = new RealtimeClient({
      baseUrl,
      teamId: selectedTeamId,
      onStateChange: setState,
      onEvent: (event: EventPayload) => {
        pushEvent({
          id: event.id,
          team_id: event.team_id,
          kind: event.kind as never,
          payload: event.payload ?? {},
          occurred_at: event.occurred_at,
        });
        setReceived((count) => count + 1);
      },
    });

    clientRef.current = client;
    client.connect();

    return () => {
      client.close();
      clientRef.current = null;
    };
  }, [baseUrl, enabled, pushEvent, selectedTeamId]);

  const value = useMemo<RealtimeContextValue>(
    () => ({
      state,
      received,
      reconnect: () => {
        clientRef.current?.close();
        clientRef.current?.connect();
      },
      setScope: (teamId: string | null) => {
        useDashboardStore.getState().setSelectedTeam(teamId);
      },
    }),
    [received, state],
  );

  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>;
}
