/**
 * Barrel export for the realtime layer.
 */

export {
  RealtimeClient,
  buildSocketUrl,
  socketAuthHeaders,
} from "./socket";
export type {
  ConnectionState,
  EventPayload,
  RealtimeClientOptions,
  RealtimeClientState,
  ServerFrame,
  ServerFrameType,
} from "./socket";

export { RealtimeProvider, useRealtime } from "./RealtimeProvider";
export type { RealtimeContextValue, RealtimeProviderProps } from "./RealtimeProvider";
