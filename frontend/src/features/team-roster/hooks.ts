/**
 * Data loading and mutation helpers for the roster page.
 */

import { useCallback, useEffect, useState } from "react";
import { toApiError } from "../../api/client";
import { rosterApi } from "./api";
import type {
  AcceptanceResult,
  AssignmentInput,
  Availability,
  Invitation,
  InvitationInput,
  RosterAssignment,
  RosterMember,
  RosterMemberInput,
  RosterMemberPatch,
  RosterRole,
  RosterSnapshot,
  RosterStats,
} from "./types";

const EMPTY_SNAPSHOT: RosterSnapshot = {
  members: [],
  invitations: [],
  assignments: [],
  stats: null,
};

/** Values returned by {@link useRoster}. */
export interface UseRosterResult {
  /** The loaded members. */
  members: RosterMember[];
  /** The loaded invitations. */
  invitations: Invitation[];
  /** The loaded assignments. */
  assignments: RosterAssignment[];
  /** The loaded statistics. */
  stats: RosterStats | null;
  /** Whether the initial load is in progress. */
  loading: boolean;
  /** Whether a mutation is in progress. */
  busy: boolean;
  /** The most recent error message, when one occurred. */
  error: string | null;
  /** Reload every roster resource. */
  refresh: () => Promise<void>;
  /** Add a member. */
  addMember: (payload: RosterMemberInput) => Promise<RosterMember>;
  /** Update a member. */
  editMember: (id: string, payload: RosterMemberPatch) => Promise<RosterMember>;
  /** Remove a member. */
  removeMember: (id: string) => Promise<void>;
  /** Change a member's role. */
  changeRole: (id: string, role: RosterRole) => Promise<RosterMember>;
  /** Change a member's availability. */
  setAvailability: (id: string, value: Availability) => Promise<RosterMember>;
  /** Send an invitation. */
  invite: (payload: InvitationInput) => Promise<Invitation>;
  /** Accept an invitation. */
  accept: (
    id: string,
    handle: string,
    displayName?: string,
  ) => Promise<AcceptanceResult>;
  /** Revoke an invitation. */
  revoke: (id: string) => Promise<Invitation>;
  /** Reserve work for a member. */
  assign: (payload: AssignmentInput) => Promise<RosterAssignment>;
  /** Release an assignment. */
  release: (id: string) => Promise<void>;
}

/**
 * Load the roster and expose mutations that refresh the snapshot on success.
 *
 * @param teamId - Optional team identifier used to scope the data.
 * @returns The roster state and mutation helpers.
 */
export function useRoster(teamId?: string): UseRosterResult {
  const [snapshot, setSnapshot] = useState<RosterSnapshot>(EMPTY_SNAPSHOT);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      const [members, invitations, assignments, stats] = await Promise.all([
        rosterApi.listMembers(teamId ? { teamId } : {}, { signal }),
        rosterApi.listInvitations(teamId, undefined, { signal }),
        rosterApi.listAssignments({}, { signal }),
        rosterApi.stats(teamId, { signal }),
      ]);
      if (signal?.aborted) return;
      const memberIds = new Set(members.map((member) => member.id));
      setSnapshot({
        members,
        invitations,
        assignments: teamId
          ? assignments.filter((assignment) =>
              memberIds.has(assignment.member_id),
            )
          : assignments,
        stats,
      });
    },
    [teamId],
  );

  const refresh = useCallback(async () => {
    try {
      await load();
      setError(null);
    } catch (cause) {
      setError(toApiError(cause).message);
    }
  }, [load]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    void load(controller.signal)
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        setError(toApiError(cause).message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [load]);

  const run = useCallback(
    async <T>(action: () => Promise<T>): Promise<T> => {
      setBusy(true);
      try {
        const result = await action();
        await load();
        setError(null);
        return result;
      } catch (cause) {
        const message = toApiError(cause).message;
        setError(message);
        throw cause;
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  const addMember = useCallback(
    (payload: RosterMemberInput) => run(() => rosterApi.createMember(payload)),
    [run],
  );
  const editMember = useCallback(
    (id: string, payload: RosterMemberPatch) =>
      run(() => rosterApi.updateMember(id, payload)),
    [run],
  );
  const removeMember = useCallback(
    (id: string) => run(() => rosterApi.removeMember(id)),
    [run],
  );
  const changeRole = useCallback(
    (id: string, role: RosterRole) => run(() => rosterApi.changeRole(id, role)),
    [run],
  );
  const setAvailability = useCallback(
    (id: string, value: Availability) =>
      run(() => rosterApi.setAvailability(id, value)),
    [run],
  );
  const invite = useCallback(
    (payload: InvitationInput) =>
      run(() => rosterApi.createInvitation(payload)),
    [run],
  );
  const accept = useCallback(
    (id: string, handle: string, displayName = "") =>
      run(() => rosterApi.acceptInvitation(id, handle, displayName)),
    [run],
  );
  const revoke = useCallback(
    (id: string) => run(() => rosterApi.revokeInvitation(id)),
    [run],
  );
  const assign = useCallback(
    (payload: AssignmentInput) =>
      run(() => rosterApi.createAssignment(payload)),
    [run],
  );
  const release = useCallback(
    (id: string) => run(() => rosterApi.removeAssignment(id)),
    [run],
  );

  return {
    ...snapshot,
    loading,
    busy,
    error,
    refresh,
    addMember,
    editMember,
    removeMember,
    changeRole,
    setAvailability,
    invite,
    accept,
    revoke,
    assign,
    release,
  };
}
