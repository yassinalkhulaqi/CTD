import { describe, expect, it } from "vitest";
import {
  AVAILABILITY_OPTIONS,
  ROLE_META,
  ROLE_OPTIONS,
  assignedHoursByMember,
  availabilityLabel,
  availabilityTone,
  effectiveInvitationStatus,
  filterMembers,
  formatHours,
  initialsOf,
  isInvitationExpired,
  isValidHandle,
  isValidInviteEmail,
  permits,
  roleRank,
  sortMembers,
  summariseRoster,
  utilisation,
} from "./domain";
import {
  makeAssignment,
  makeInvitation,
  makeMember,
  makeMemberSet,
} from "./fixtures";

describe("role and availability metadata", () => {
  it("exposes four ordered roles with presentation metadata", () => {
    expect(ROLE_OPTIONS.map((option) => option.value)).toEqual([
      "observer",
      "analyst",
      "member",
      "lead",
    ]);
    expect(roleRank("lead")).toBe(3);
    expect(roleRank("observer")).toBe(0);
    expect(ROLE_META.lead.tone).toBe("warning");
  });

  it("maps permissions by seniority", () => {
    expect(permits("lead", "roster:manage")).toBe(true);
    expect(permits("member", "roster:manage")).toBe(false);
    expect(permits("observer", "roster:view")).toBe(true);
    expect(permits("analyst", "roster:contacts")).toBe(true);
  });

  it("labels availability and assigns accessible tones", () => {
    expect(availabilityLabel("busy")).toBe("Busy");
    expect(availabilityTone("available")).toBe("success");
    expect(availabilityTone("offline")).toBe("neutral");
    expect(AVAILABILITY_OPTIONS).toHaveLength(3);
  });
});

describe("pure formatting and capacity helpers", () => {
  it("derives initials from display names", () => {
    expect(initialsOf("Nyx Chandler")).toBe("NC");
    expect(initialsOf("nyx")).toBe("NY");
    expect(initialsOf("")).toBe("??");
  });

  it("clamps utilisation ratios", () => {
    expect(utilisation(4, 8)).toBe(0.5);
    expect(utilisation(16, 8)).toBe(1);
    expect(utilisation(2, 0)).toBe(0);
  });

  it("formats compact hour labels", () => {
    expect(formatHours(4)).toBe("4h");
    expect(formatHours(4.5)).toBe("4.5h");
    expect(formatHours(0)).toBe("0h");
  });

  it("validates invite input", () => {
    expect(isValidInviteEmail("Teammate@Example.com")).toBe(true);
    expect(isValidInviteEmail("not-an-email")).toBe(false);
    expect(isValidHandle("night_owl")).toBe(true);
    expect(isValidHandle("a")).toBe(false);
  });
});

describe("invitation deadlines", () => {
  it("detects expired invitations against a reference time", () => {
    const invitation = makeInvitation({ expires_at: "2026-01-02T00:00:00Z" });
    expect(
      isInvitationExpired(invitation, Date.parse("2026-01-03T00:00:00Z")),
    ).toBe(true);
    expect(
      isInvitationExpired(invitation, Date.parse("2026-01-01T00:00:00Z")),
    ).toBe(false);
  });

  it("resolves the effective status of a stale pending invitation", () => {
    const stale = makeInvitation({ expires_at: "2026-01-01T00:00:00Z" });
    expect(
      effectiveInvitationStatus(stale, Date.parse("2026-02-01T00:00:00Z")),
    ).toBe("expired");
    expect(
      effectiveInvitationStatus(stale, Date.parse("2025-12-01T00:00:00Z")),
    ).toBe("pending");
    const accepted = makeInvitation({ status: "accepted" });
    expect(effectiveInvitationStatus(accepted)).toBe("accepted");
  });
});

describe("member filtering and sorting", () => {
  const members = makeMemberSet();

  it("filters by team, role and availability", () => {
    expect(
      filterMembers(members, {
        teamId: "team-alpha",
        role: "all",
        availability: "all",
        query: "",
      }),
    ).toHaveLength(3);
    expect(
      filterMembers(members, {
        teamId: "all",
        role: "lead",
        availability: "all",
        query: "",
      }).map((member) => member.handle),
    ).toEqual(["atlas"]);
    expect(
      filterMembers(members, {
        teamId: "all",
        role: "all",
        availability: "busy",
        query: "",
      }),
    ).toHaveLength(1);
  });

  it("matches free-text queries against handle, specialty and timezone", () => {
    const filters = {
      teamId: "all",
      role: "all" as const,
      availability: "all" as const,
      query: "cipher",
    };
    expect(filterMembers(members, filters).map((member) => member.id)).toEqual([
      "member-3",
    ]);
    expect(filterMembers(members, { ...filters, query: "Europe" }).length).toBe(
      4,
    );
  });

  it("sorts by role, name and capacity without mutating input", () => {
    expect(sortMembers(members, "role")[0].role).toBe("lead");
    expect(sortMembers(members, "name")[0].display_name).toBe("Atlas Vale");
    expect(sortMembers(members, "capacity")[0].id).toBe("member-1");
    expect(members[0].role).toBe("lead");
  });
});

describe("aggregation helpers", () => {
  it("totals assigned hours per member", () => {
    const totals = assignedHoursByMember([
      makeAssignment({ member_id: "m1", hours: 2 }),
      makeAssignment({ id: "a2", member_id: "m1", hours: 3 }),
      makeAssignment({ id: "a3", member_id: "m2", hours: 1 }),
    ]);
    expect(totals).toEqual({ m1: 5, m2: 1 });
  });

  it("summarises a roster for the statistics tiles", () => {
    const members = makeMemberSet();
    const summary = summariseRoster(
      members,
      [makeAssignment({ member_id: "member-1", hours: 8 })],
      2,
    );
    expect(summary).toEqual({
      members: 4,
      leads: 1,
      available: 2,
      pending: 2,
      utilisation: 0.25,
    });
  });

  it("handles an empty roster", () => {
    expect(summariseRoster([], [], 0).utilisation).toBe(0);
    expect(assignedHoursByMember([])).toEqual({});
  });
});

describe("fixture consistency", () => {
  it("builds a member with derived fields matching its role", () => {
    const member = makeMember({ role: "lead", availability: "offline" });
    expect(member.rank).toBe(3);
    expect(member.initials).toBe("NC");
  });
});
