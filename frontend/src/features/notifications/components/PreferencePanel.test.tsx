/** Preference panel interaction tests. */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Preference } from "../types";
import { PreferencePanel } from "./PreferencePanel";

function preferences(): Preference[] {
  const rows: Preference[] = [];
  for (const channel of ["in_app", "email", "webhook"] as const) {
    for (const kind of [
      "solve",
      "challenge",
      "team",
      "security",
      "system",
    ] as const) {
      rows.push({
        recipient_id: "member-1",
        channel,
        kind,
        enabled: true,
        quiet_start_hour: 0,
        quiet_end_hour: 0,
        quiet_hours: "No quiet hours",
      });
    }
  }
  return rows;
}

function setup(overrides: { preferences?: Preference[] } = {}) {
  const onToggle = vi.fn();
  const onQuietChange = vi.fn();
  const onSave = vi.fn();
  render(
    <PreferencePanel
      preferences={overrides.preferences ?? preferences()}
      onToggle={onToggle}
      onQuietChange={onQuietChange}
      onSave={onSave}
      saving={false}
    />,
  );
  return { onToggle, onQuietChange, onSave };
}

describe("PreferencePanel", () => {
  it("renders a switch for every channel and kind pair", () => {
    setup();
    expect(screen.getAllByRole("switch")).toHaveLength(15);
    expect(screen.getByText("Delivery preferences")).toBeInTheDocument();
    expect(screen.getAllByText("Quiet from")).toHaveLength(3);
  });

  it("reports switch toggles with the correct key", () => {
    const { onToggle } = setup();
    fireEvent.click(screen.getByRole("switch", { name: "Email Security" }));
    expect(onToggle).toHaveBeenCalledWith("email", "security", false);
  });

  it("reports quiet hours changes", () => {
    const { onQuietChange } = setup();
    fireEvent.change(screen.getByLabelText("Webhook quiet start hour"), {
      target: { value: "22" },
    });
    expect(onQuietChange).toHaveBeenCalledWith("webhook", 22, 0);
  });

  it("reflects an explicit disabled row and saves", () => {
    const rows = preferences().map((row) =>
      row.channel === "email" && row.kind === "solve"
        ? { ...row, enabled: false }
        : row,
    );
    const { onSave } = setup({ preferences: rows });
    expect(
      screen.getByRole("switch", { name: "Email Solves" }),
    ).not.toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "Save preferences" }));
    expect(onSave).toHaveBeenCalled();
  });
});
