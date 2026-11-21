import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { reportsApi } from "./api";
import {
  DRAFT_REPORT,
  REPORT,
  STATS,
  TEMPLATE,
  EXPORT_JOB,
} from "./testFixtures";

const mockCatalog = vi.fn();
const mockDraft = vi.fn();

vi.mock("./hooks", () => ({
  useReportCatalog: () => mockCatalog(),
  useReportDraft: () => mockDraft(),
}));

vi.mock("./api", () => ({
  reportsApi: {
    createReport: vi.fn(),
    finalise: vi.fn(),
    exportReport: vi.fn(),
  },
}));

import { ReportsPage } from "./ReportsPage";

const draft = {
  templateId: TEMPLATE.id,
  title: "Weekly report",
  scopeId: "redscribe",
  sections: TEMPLATE.sections,
};

const builder = {
  draft,
  errors: {},
  selectTemplate: vi.fn(),
  loadReport: vi.fn(),
  setTitle: vi.fn(),
  setScope: vi.fn(),
  addSection: vi.fn(),
  patchSection: vi.fn(),
  toggle: vi.fn(),
  move: vi.fn(),
  remove: vi.fn(),
  reset: vi.fn(),
};

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCatalog.mockReturnValue({
      templates: [TEMPLATE],
      reports: [REPORT],
      exports: [EXPORT_JOB],
      stats: STATS,
      loading: false,
      error: null,
      refresh: vi.fn().mockResolvedValue(undefined),
    });
    mockDraft.mockReturnValue(builder);
    vi.mocked(reportsApi.createReport).mockResolvedValue(REPORT);
    vi.mocked(reportsApi.finalise).mockResolvedValue(REPORT);
    vi.mocked(reportsApi.exportReport).mockResolvedValue(EXPORT_JOB);
  });

  it("renders the studio shell and live preview", () => {
    render(<ReportsPage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Report studio" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Live preview")).toBeInTheDocument();
    expect(screen.getByText("Saved reports")).toBeInTheDocument();
    expect(
      screen.getByText("1 reports · 1 templates · 1 exports"),
    ).toBeInTheDocument();
  });

  it("creates a draft with the captured snapshot", async () => {
    const user = userEvent.setup();
    render(<ReportsPage />);
    await user.click(
      screen.getByRole("button", { name: /Create draft report/ }),
    );
    expect(reportsApi.createReport).toHaveBeenCalledWith({
      template_id: TEMPLATE.id,
      title: "Weekly report",
      scope_id: "redscribe",
      data: expect.objectContaining({ team: "redscribe", score: 1240 }),
    });
    expect(screen.getByRole("status")).toHaveTextContent("Draft rep-1 created");
  });

  it("finalises the selected report before export", async () => {
    const user = userEvent.setup();
    mockCatalog.mockReturnValue({
      templates: [TEMPLATE],
      reports: [DRAFT_REPORT],
      exports: [],
      stats: STATS,
      loading: false,
      error: null,
      refresh: vi.fn().mockResolvedValue(undefined),
    });
    render(<ReportsPage />);
    await user.click(
      screen.getByRole("row", { name: /Open report Draft report/ }),
    );
    expect(builder.loadReport).toHaveBeenCalledWith(DRAFT_REPORT);
    await user.click(screen.getByRole("button", { name: /Finalise report/ }));
    expect(reportsApi.finalise).toHaveBeenCalledWith("rep-2");
    await user.click(screen.getByRole("button", { name: /Export report/ }));
    await user.click(screen.getByRole("menuitem", { name: /JSON/ }));
    expect(reportsApi.exportReport).toHaveBeenCalledWith("rep-1", "json");
  });

  it("shows validation feedback when the draft is incomplete", async () => {
    const user = userEvent.setup();
    mockDraft.mockReturnValue({
      ...builder,
      errors: { title: "Give the report a title." },
    });
    render(<ReportsPage />);
    await user.click(
      screen.getByRole("button", { name: /Create draft report/ }),
    );
    expect(reportsApi.createReport).not.toHaveBeenCalled();
    expect(
      screen
        .getAllByRole("alert")
        .some((element) =>
          element.textContent?.includes("Fix the highlighted fields"),
        ),
    ).toBe(true);
  });

  it("renders a retryable error state", () => {
    mockCatalog.mockReturnValue({
      templates: [],
      reports: [],
      exports: [],
      stats: null,
      loading: false,
      error: "API offline",
      refresh: vi.fn(),
    });
    render(<ReportsPage />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Report studio unavailable",
    );
    expect(
      screen.getByRole("button", { name: /Try again/ }),
    ).toBeInTheDocument();
  });
});
