import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { Challenge } from "../../types";

const mockChallenges = vi.fn();
const mockSolves = vi.fn();

vi.mock("../../api/resources", () => ({
  useChallenges: () => mockChallenges(),
  useSolves: () => mockSolves(),
}));

vi.mock("../../stores/dashboardStore", () => ({
  useDashboardStore: (selector: (state: Record<string, unknown>) => unknown) =>
    selector({
      selectedTeamId: null,
      categoryFilter: "all",
      statusFilter: "all",
      searchQuery: "",
    }),
}));

import { ChallengeBoard } from "./ChallengeBoard";

function challenge(overrides: Partial<Challenge> = {}): Challenge {
  return {
    id: "challenge-1",
    team_id: "team-1",
    title: "Nonce Reuse",
    category: "crypto",
    difficulty: "medium",
    points: 250,
    description: "The IV looks suspiciously familiar.",
    status: "active",
    tags: ["aes", "stream-cipher"],
    starts_at: null,
    ends_at: null,
    created_at: "2026-01-01T00:00:00Z",
    seconds_remaining: 3600,
    ...overrides,
  };
}

describe("ChallengeBoard", () => {
  beforeEach(() => {
    mockChallenges.mockReturnValue({ data: [challenge()], isLoading: false });
    mockSolves.mockReturnValue({ data: [], isLoading: false });
  });

  it("renders the four lifecycle columns", () => {
    render(<ChallengeBoard onSelect={() => undefined} />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Solved")).toBeInTheDocument();
    expect(screen.getByText("Locked")).toBeInTheDocument();
  });

  it("renders the challenge of the matching column", () => {
    render(<ChallengeBoard onSelect={() => undefined} />);
    expect(screen.getByText("Nonce Reuse")).toBeInTheDocument();
  });

  it("invokes the selection handler", () => {
    const onSelect = vi.fn();
    render(<ChallengeBoard onSelect={onSelect} />);
    screen.getByText("Nonce Reuse").click();
    expect(onSelect).toHaveBeenCalled();
  });

  it("renders a placeholder for an empty column", () => {
    mockChallenges.mockReturnValue({ data: [], isLoading: false });
    render(<ChallengeBoard onSelect={() => undefined} />);
    expect(screen.getAllByText("No challenge").length).toBe(4);
  });
});
