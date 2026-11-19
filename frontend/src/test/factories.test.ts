import { describe, expect, it } from "vitest";
import {
  makeChallenge,
  makeChallengeSet,
  makeEvent,
  makeMember,
  makeTeam,
} from "./factories";

describe("factories", () => {
  it("builds unique team identifiers", () => {
    expect(makeTeam().id).not.toBe(makeTeam().id);
  });

  it("builds a member with the expected defaults", () => {
    const member = makeMember();
    expect(member.handle).toBe("nyx");
    expect(member.is_online).toBe(true);
  });

  it("builds a challenge with the expected defaults", () => {
    const challenge = makeChallenge();
    expect(challenge.category).toBe("crypto");
    expect(challenge.points).toBe(250);
  });

  it("spreads a challenge set across the statuses", () => {
    const statuses = new Set(
      makeChallengeSet(4).map((challenge) => challenge.status),
    );
    expect(statuses.size).toBe(4);
  });

  it("builds an activity event", () => {
    expect(makeEvent().kind).toBe("solve.created");
  });
});
