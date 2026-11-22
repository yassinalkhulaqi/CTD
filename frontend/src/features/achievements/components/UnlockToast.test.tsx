import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UnlockToast } from "./UnlockToast";
import { makeBadgeView } from "../testFixtures";

describe("UnlockToast", () => {
  it("renders nothing when no badges were unlocked", () => {
    const { container } = render(
      <UnlockToast badges={[]} onDismiss={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("announces a single unlock", () => {
    render(<UnlockToast badges={[makeBadgeView()]} onDismiss={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent("New badge unlocked!");
    expect(screen.getByText("First Blood")).toBeInTheDocument();
  });

  it("summarises multiple unlocks", () => {
    const badges = [
      makeBadgeView(),
      makeBadgeView({
        badge: { ...makeBadgeView().badge, id: "second", name: "Second" },
        display_name: "Second",
      }),
    ];
    render(<UnlockToast badges={badges} onDismiss={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveAttribute(
      "aria-label",
      "2 new badges unlocked",
    );
  });

  it("truncates long unlock lists and dismisses", () => {
    const onDismiss = vi.fn();
    const badges = Array.from({ length: 5 }, (_, index) =>
      makeBadgeView({
        badge: { ...makeBadgeView().badge, id: `badge-${index}` },
        display_name: `Badge ${index}`,
      }),
    );
    render(<UnlockToast badges={badges} onDismiss={onDismiss} />);
    expect(screen.getByText("+2 more")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Dismiss/i }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
