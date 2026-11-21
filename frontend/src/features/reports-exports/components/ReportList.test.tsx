import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReportList } from "./ReportList";
import { EXPORT_JOB, REPORT } from "../testFixtures";

describe("ReportList", () => {
  it("renders saved reports with status and scope", () => {
    render(
      <ReportList
        reports={[REPORT]}
        selectedId={null}
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByText("Weekly report")).toBeInTheDocument();
    expect(screen.getByText("final")).toBeInTheDocument();
    expect(screen.getByText("redscribe")).toBeInTheDocument();
  });

  it("selects a report when its row is activated", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <ReportList reports={[REPORT]} selectedId={null} onSelect={onSelect} />,
    );
    await user.click(
      screen.getByRole("row", { name: /Open report Weekly report/ }),
    );
    expect(onSelect).toHaveBeenCalledWith(REPORT);
  });

  it("shows recent exports", () => {
    render(
      <ReportList
        reports={[REPORT]}
        selectedId={REPORT.id}
        exports={[EXPORT_JOB]}
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByText("Recent exports")).toBeInTheDocument();
    expect(screen.getByText("15 B")).toBeInTheDocument();
  });

  it("renders an empty state when there are no reports", () => {
    render(
      <ReportList reports={[]} selectedId={null} onSelect={() => undefined} />,
    );
    expect(screen.getByText("No reports yet")).toBeInTheDocument();
  });
});
