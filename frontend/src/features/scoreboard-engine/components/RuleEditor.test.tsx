import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RuleEditor } from "./RuleEditor";
import type { ScoreRule } from "../types";

const rule: ScoreRule = {
  id: "rule-1",
  team_id: "team-1",
  name: "Balanced",
  base_points: 100,
  difficulty_multiplier: 1,
  first_blood_bonus: 50,
  hint_penalty: 10,
  decay_factor: 0.9,
  decay_enabled: true,
  updated_at: "2026-01-01T00:00:00Z",
  summary: "Balanced policy",
};

describe("RuleEditor", () => {
  it("renders the stored values and a live preview", () => {
    render(<RuleEditor rule={rule} onSave={() => undefined} />);
    expect(screen.getByLabelText("Policy name")).toHaveValue("Balanced");
    expect(screen.getByLabelText("Base points")).toHaveValue(100);
    expect(screen.getByRole("switch")).toBeChecked();
    expect(screen.getByText("Preview streak")).toBeInTheDocument();
  });

  it("updates the projected points when a slider moves", () => {
    render(<RuleEditor rule={rule} onSave={() => undefined} />);
    const before =
      screen.getByText("Preview streak").parentElement?.textContent;
    fireEvent.change(screen.getByLabelText("Base points slider"), {
      target: { value: "200" },
    });
    const after = screen.getByText("Preview streak").parentElement?.textContent;
    expect(after).not.toBe(before);
    expect(screen.getByLabelText("Base points")).toHaveValue(200);
  });

  it("blocks saving and shows validation feedback for invalid values", () => {
    render(<RuleEditor rule={rule} onSave={() => undefined} />);
    fireEvent.change(screen.getByLabelText("Base points"), {
      target: { value: "-5" },
    });
    expect(
      screen.getByText("Base points cannot be negative."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Save policy/ })).toBeDisabled();
  });

  it("submits a valid edited draft", async () => {
    const onSave = vi.fn().mockResolvedValue(true);
    const user = userEvent.setup();
    render(<RuleEditor rule={rule} onSave={onSave} />);
    const name = screen.getByLabelText("Policy name");
    await user.clear(name);
    await user.type(name, "Aggressive");
    await user.click(screen.getByRole("button", { name: /Save policy/ }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Aggressive", base_points: 100 }),
    );
  });

  it("restores the stored values when reset is pressed", async () => {
    const user = userEvent.setup();
    render(<RuleEditor rule={rule} onSave={() => undefined} />);
    fireEvent.change(screen.getByLabelText("First blood bonus"), {
      target: { value: "999" },
    });
    await user.click(screen.getByRole("button", { name: /Reset/ }));
    expect(screen.getByLabelText("First blood bonus")).toHaveValue(50);
  });
});
