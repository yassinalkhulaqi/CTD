/** Interaction tests for the command palette. */

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

/** Return the option currently marked as selected. */
function selectedOption(): HTMLElement {
  const option = screen
    .getAllByRole("option")
    .find((item) => item.getAttribute("aria-selected") === "true");
  if (!option) throw new Error("no selected option");
  return option;
}
import { CommandPalette } from "./CommandPalette";
import { commandInitials } from "../searchUtils";
import type { Command } from "../types";

function makeCommand(
  id: string,
  name: string,
  group: string,
  shortcut: string,
): Command {
  return {
    id,
    name,
    description: `Open ${name.toLowerCase()} page`,
    group,
    shortcut,
    keywords: [],
    initials: commandInitials(name),
    shortcut_label: shortcut,
  };
}

const commands: Command[] = [
  makeCommand("a.first", "Open challenges", "Workspace", "G C"),
  makeCommand("b.second", "Focus search", "Search", "Mod+K"),
];

describe("CommandPalette", () => {
  it("renders grouped commands with shortcuts", () => {
    render(
      <CommandPalette
        open
        commands={commands}
        onClose={vi.fn()}
        onExecute={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("dialog", { name: "Command palette" }),
    ).toBeVisible();
    expect(screen.getByText("Search", { selector: "h3" })).toBeVisible();
    expect(screen.getByText("Workspace", { selector: "h3" })).toBeVisible();
    expect(screen.getAllByRole("option")).toHaveLength(2);
    expect(screen.getByLabelText("Shortcut G C")).toBeVisible();
  });

  it("supports arrow keys, Enter and Escape", () => {
    const onExecute = vi.fn();
    const onClose = vi.fn();
    render(
      <CommandPalette
        open
        commands={commands}
        onClose={onClose}
        onExecute={onExecute}
      />,
    );
    const input = screen.getByLabelText("Search commands");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(selectedOption()).toHaveAttribute("data-index", "1");
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(selectedOption()).toHaveAttribute("data-index", "0");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onExecute).toHaveBeenCalledWith(commands[1]);
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(input, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("filters commands as the user types", () => {
    render(
      <CommandPalette
        open
        commands={commands}
        onClose={vi.fn()}
        onExecute={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("Search commands"), {
      target: { value: "focus" },
    });
    expect(screen.getAllByRole("option")).toHaveLength(1);
    expect(screen.getByRole("option")).toHaveTextContent("Focus search");
  });

  it("executes a command when its option is clicked", () => {
    const onExecute = vi.fn();
    const onClose = vi.fn();
    render(
      <CommandPalette
        open
        commands={commands}
        onClose={onClose}
        onExecute={onExecute}
      />,
    );
    fireEvent.click(screen.getByText("Focus search"));
    expect(onExecute).toHaveBeenCalledWith(commands[1]);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders nothing while closed", () => {
    const { container } = render(
      <CommandPalette
        open={false}
        commands={commands}
        onClose={vi.fn()}
        onExecute={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
