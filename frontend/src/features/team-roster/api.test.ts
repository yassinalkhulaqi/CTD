import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RosterMember } from "./types";
import { makeMember } from "./fixtures";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
  buildQuery: vi.fn(
    (params?: Record<string, string | number | boolean | null | undefined>) => {
      if (!params) return "";
      const search = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (value === undefined || value === null || value === "") continue;
        search.set(key, String(value));
      }
      const encoded = search.toString();
      return encoded ? `?${encoded}` : "";
    },
  ),
}));

vi.mock("../../api/client", () => ({
  get: mocks.get,
  post: mocks.post,
  patch: mocks.patch,
  del: mocks.del,
  buildQuery: mocks.buildQuery,
}));

import { rosterApi } from "./api";

const member: RosterMember = makeMember();

beforeEach(() => {
  vi.clearAllMocks();
  mocks.get.mockResolvedValue([member]);
  mocks.post.mockResolvedValue(member);
  mocks.patch.mockResolvedValue(member);
  mocks.del.mockResolvedValue(undefined);
});

describe("rosterApi members", () => {
  it("lists members without filters", async () => {
    await expect(rosterApi.listMembers()).resolves.toEqual([member]);
    expect(mocks.get).toHaveBeenCalledWith("/api/roster", undefined);
  });

  it("encodes member filters in the query string", async () => {
    await rosterApi.listMembers({
      teamId: "team-alpha",
      role: "lead",
      availability: "available",
    });
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/roster?team_id=team-alpha&role=lead&availability=available",
      undefined,
    );
  });

  it("creates and updates members through the right verbs", async () => {
    const payload = {
      team_id: "team-alpha",
      handle: "nyx",
      capacity_hours: 6,
    };
    await rosterApi.createMember(payload);
    expect(mocks.post).toHaveBeenCalledWith("/api/roster", payload, undefined);
    await rosterApi.updateMember("member-1", { display_name: "Nyx" });
    expect(mocks.patch).toHaveBeenCalledWith(
      "/api/roster/member-1",
      { display_name: "Nyx" },
      undefined,
    );
  });

  it("uses dedicated role and availability endpoints", async () => {
    await rosterApi.changeRole("member/1", "lead");
    expect(mocks.patch).toHaveBeenCalledWith(
      "/api/roster/member%2F1/role",
      { role: "lead" },
      undefined,
    );
    await rosterApi.setAvailability("member-1", "busy");
    expect(mocks.patch).toHaveBeenCalledWith(
      "/api/roster/member-1",
      { availability: "busy" },
      undefined,
    );
  });

  it("deletes a member", async () => {
    await rosterApi.removeMember("member-1");
    expect(mocks.del).toHaveBeenCalledWith("/api/roster/member-1", undefined);
  });
});

describe("rosterApi invitations", () => {
  it("lists invitations with the status filter name used by the API", async () => {
    await rosterApi.listInvitations("team-alpha", "pending");
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/roster/invitations?team_id=team-alpha&status_filter=pending",
      undefined,
    );
  });

  it("creates, accepts, revokes and expires invitations", async () => {
    await rosterApi.createInvitation({
      team_id: "team-alpha",
      email: "a@example.com",
      role: "analyst",
    });
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/roster/invitations",
      { team_id: "team-alpha", email: "a@example.com", role: "analyst" },
      undefined,
    );
    await rosterApi.acceptInvitation("invite-1", "alex", "Alex");
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/roster/invitations/invite-1/accept",
      { handle: "alex", display_name: "Alex" },
      undefined,
    );
    await rosterApi.revokeInvitation("invite-1");
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/roster/invitations/invite-1/revoke",
      undefined,
      undefined,
    );
    await rosterApi.expireInvitations();
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/roster/invitations/expire",
      undefined,
      undefined,
    );
  });
});

describe("rosterApi assignments and statistics", () => {
  it("lists assignments with member and challenge filters", async () => {
    await rosterApi.listAssignments({ memberId: "m1", challengeId: "c1" });
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/roster/assignments?member_id=m1&challenge_id=c1",
      undefined,
    );
  });

  it("creates, updates and releases assignments", async () => {
    await rosterApi.createAssignment({
      member_id: "m1",
      challenge_id: "c1",
      hours: 3,
    });
    expect(mocks.post).toHaveBeenCalledWith(
      "/api/roster/assignments",
      { member_id: "m1", challenge_id: "c1", hours: 3 },
      undefined,
    );
    await rosterApi.updateAssignmentHours("a1", 4);
    expect(mocks.patch).toHaveBeenCalledWith(
      "/api/roster/assignments/a1",
      { hours: 4 },
      undefined,
    );
    await rosterApi.removeAssignment("a1");
    expect(mocks.del).toHaveBeenCalledWith(
      "/api/roster/assignments/a1",
      undefined,
    );
  });

  it("loads statistics scoped to a team", async () => {
    await rosterApi.stats("team-alpha");
    expect(mocks.get).toHaveBeenCalledWith(
      "/api/roster/stats?team_id=team-alpha",
      undefined,
    );
  });

  it("propagates API failures to callers", async () => {
    mocks.get.mockRejectedValueOnce(new Error("offline"));
    await expect(rosterApi.stats()).rejects.toThrow("offline");
  });
});
