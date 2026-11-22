/**
 * Typed API adapter for the team roster feature.
 *
 * Every function delegates to the shared client so authentication, retries and
 * error normalisation behave identically to the rest of the dashboard.
 */

import {
  buildQuery,
  del,
  get,
  patch,
  post,
  type RequestOptions,
} from "../../api/client";
import type {
  AcceptanceResult,
  AssignmentInput,
  Availability,
  Invitation,
  InvitationInput,
  InvitationStatus,
  RosterAssignment,
  RosterMember,
  RosterMemberInput,
  RosterMemberPatch,
  RosterRole,
  RosterStats,
} from "./types";

/** Filters accepted when listing roster members. */
export interface MemberQuery {
  teamId?: string;
  role?: RosterRole;
  availability?: Availability;
}

/** Filters accepted when listing assignments. */
export interface AssignmentQuery {
  memberId?: string;
  challengeId?: string;
}

/** The roster endpoints used by the page and its hooks. */
export const rosterApi = {
  /**
   * List roster members with optional filters.
   *
   * @param query - The filters to apply.
   * @param options - Request options.
   * @returns The matching members.
   */
  listMembers(
    query: MemberQuery = {},
    options?: RequestOptions,
  ): Promise<RosterMember[]> {
    const search = buildQuery({
      team_id: query.teamId,
      role: query.role,
      availability: query.availability,
    });
    return get<RosterMember[]>(`/api/roster${search}`, options);
  },

  /**
   * Return one roster member.
   *
   * @param memberId - The member identifier.
   * @param options - Request options.
   * @returns The member.
   */
  getMember(memberId: string, options?: RequestOptions): Promise<RosterMember> {
    return get<RosterMember>(
      `/api/roster/${encodeURIComponent(memberId)}`,
      options,
    );
  },

  /**
   * Add a member to a roster.
   *
   * @param payload - The member fields.
   * @param options - Request options.
   * @returns The created member.
   */
  createMember(
    payload: RosterMemberInput,
    options?: RequestOptions,
  ): Promise<RosterMember> {
    return post<RosterMember>("/api/roster", payload, options);
  },

  /**
   * Partially update a member.
   *
   * @param memberId - The member identifier.
   * @param payload - The fields to change.
   * @param options - Request options.
   * @returns The updated member.
   */
  updateMember(
    memberId: string,
    payload: RosterMemberPatch,
    options?: RequestOptions,
  ): Promise<RosterMember> {
    return patch<RosterMember>(
      `/api/roster/${encodeURIComponent(memberId)}`,
      payload,
      options,
    );
  },

  /**
   * Change the role of a member.
   *
   * @param memberId - The member identifier.
   * @param role - The new role.
   * @param options - Request options.
   * @returns The updated member.
   */
  changeRole(
    memberId: string,
    role: RosterRole,
    options?: RequestOptions,
  ): Promise<RosterMember> {
    return patch<RosterMember>(
      `/api/roster/${encodeURIComponent(memberId)}/role`,
      { role },
      options,
    );
  },

  /**
   * Publish a new availability state.
   *
   * @param memberId - The member identifier.
   * @param availability - The new state.
   * @param options - Request options.
   * @returns The updated member.
   */
  setAvailability(
    memberId: string,
    availability: Availability,
    options?: RequestOptions,
  ): Promise<RosterMember> {
    return patch<RosterMember>(
      `/api/roster/${encodeURIComponent(memberId)}`,
      { availability },
      options,
    );
  },

  /**
   * Remove a member from the roster.
   *
   * @param memberId - The member identifier.
   * @param options - Request options.
   * @returns A promise resolved when the member was removed.
   */
  removeMember(memberId: string, options?: RequestOptions): Promise<void> {
    return del<void>(`/api/roster/${encodeURIComponent(memberId)}`, options);
  },

  /**
   * List invitations with optional filters.
   *
   * @param teamId - Optional team filter.
   * @param status - Optional lifecycle filter.
   * @param options - Request options.
   * @returns The matching invitations.
   */
  listInvitations(
    teamId?: string,
    status?: InvitationStatus,
    options?: RequestOptions,
  ): Promise<Invitation[]> {
    const search = buildQuery({ team_id: teamId, status_filter: status });
    return get<Invitation[]>(`/api/roster/invitations${search}`, options);
  },

  /**
   * Create a team invitation.
   *
   * @param payload - The email, team and role.
   * @param options - Request options.
   * @returns The created invitation.
   */
  createInvitation(
    payload: InvitationInput,
    options?: RequestOptions,
  ): Promise<Invitation> {
    return post<Invitation>("/api/roster/invitations", payload, options);
  },

  /**
   * Accept an invitation and create the invited member.
   *
   * @param invitationId - The invitation identifier.
   * @param handle - The handle chosen by the invitee.
   * @param displayName - Optional display name.
   * @param options - Request options.
   * @returns The accepted invitation and the new member.
   */
  acceptInvitation(
    invitationId: string,
    handle: string,
    displayName = "",
    options?: RequestOptions,
  ): Promise<AcceptanceResult> {
    return post<AcceptanceResult>(
      `/api/roster/invitations/${encodeURIComponent(invitationId)}/accept`,
      { handle, display_name: displayName },
      options,
    );
  },

  /**
   * Revoke a pending invitation.
   *
   * @param invitationId - The invitation identifier.
   * @param options - Request options.
   * @returns The revoked invitation.
   */
  revokeInvitation(
    invitationId: string,
    options?: RequestOptions,
  ): Promise<Invitation> {
    return post<Invitation>(
      `/api/roster/invitations/${encodeURIComponent(invitationId)}/revoke`,
      undefined,
      options,
    );
  },

  /**
   * Mark overdue invitations as expired.
   *
   * @param options - Request options.
   * @returns The number of invitations expired.
   */
  expireInvitations(options?: RequestOptions): Promise<number> {
    return post<number>("/api/roster/invitations/expire", undefined, options);
  },

  /**
   * List work assignments.
   *
   * @param query - Optional member and challenge filters.
   * @param options - Request options.
   * @returns The matching assignments.
   */
  listAssignments(
    query: AssignmentQuery = {},
    options?: RequestOptions,
  ): Promise<RosterAssignment[]> {
    const search = buildQuery({
      member_id: query.memberId,
      challenge_id: query.challengeId,
    });
    return get<RosterAssignment[]>(`/api/roster/assignments${search}`, options);
  },

  /**
   * Reserve work for a member.
   *
   * @param payload - The member, challenge and hours.
   * @param options - Request options.
   * @returns The created assignment.
   */
  createAssignment(
    payload: AssignmentInput,
    options?: RequestOptions,
  ): Promise<RosterAssignment> {
    return post<RosterAssignment>("/api/roster/assignments", payload, options);
  },

  /**
   * Change the hours of an assignment.
   *
   * @param assignmentId - The assignment identifier.
   * @param hours - The new hour count.
   * @param options - Request options.
   * @returns The updated assignment.
   */
  updateAssignmentHours(
    assignmentId: string,
    hours: number,
    options?: RequestOptions,
  ): Promise<RosterAssignment> {
    return patch<RosterAssignment>(
      `/api/roster/assignments/${encodeURIComponent(assignmentId)}`,
      { hours },
      options,
    );
  },

  /**
   * Release an assignment.
   *
   * @param assignmentId - The assignment identifier.
   * @param options - Request options.
   * @returns A promise resolved when the assignment was removed.
   */
  removeAssignment(
    assignmentId: string,
    options?: RequestOptions,
  ): Promise<void> {
    return del<void>(
      `/api/roster/assignments/${encodeURIComponent(assignmentId)}`,
      options,
    );
  },

  /**
   * Return aggregated roster statistics.
   *
   * @param teamId - Optional team filter.
   * @param options - Request options.
   * @returns The roster statistics.
   */
  stats(teamId?: string, options?: RequestOptions): Promise<RosterStats> {
    const search = buildQuery({ team_id: teamId });
    return get<RosterStats>(`/api/roster/stats${search}`, options);
  },
};
