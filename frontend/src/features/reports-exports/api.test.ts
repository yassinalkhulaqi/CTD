import { beforeEach, describe, expect, it, vi } from "vitest";
import type * as ClientModule from "../../api/client";
import { get, patch, post } from "../../api/client";
import { reportsApi } from "./api";

vi.mock("../../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof ClientModule>();
  return {
    ...actual,
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  };
});

describe("reportsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads templates, exports and stats from their static routes", async () => {
    vi.mocked(get).mockResolvedValue([]);
    vi.mocked(get).mockResolvedValueOnce([{ id: "tpl-1" }]);
    await reportsApi.listTemplates();
    await reportsApi.listExports(25);
    await reportsApi.stats();
    expect(get).toHaveBeenNthCalledWith(1, "/api/reports/templates", {});
    expect(get).toHaveBeenNthCalledWith(2, "/api/reports/exports?limit=25", {});
    expect(get).toHaveBeenNthCalledWith(3, "/api/reports/stats", {});
  });

  it("encodes filters and report identifiers", async () => {
    vi.mocked(get).mockResolvedValue(null);
    await reportsApi.listReports({ status: "final", limit: 10 });
    await reportsApi.getReport("rep 1");
    expect(get).toHaveBeenNthCalledWith(
      1,
      "/api/reports?status=final&limit=10",
      {},
    );
    expect(get).toHaveBeenNthCalledWith(2, "/api/reports/rep%201", {});
  });

  it("posts create, finalise, export and preview requests", async () => {
    vi.mocked(post).mockResolvedValue({ id: "rep-1" });
    vi.mocked(get).mockResolvedValue({ title: "Report" });
    await reportsApi.createReport({
      template_id: "tpl-1",
      title: "Report",
      scope_id: "team",
    });
    await reportsApi.finalise("rep-1");
    await reportsApi.exportReport("rep-1", "csv");
    await reportsApi.preview("rep-1", "html");
    expect(post).toHaveBeenNthCalledWith(1, "/api/reports", {
      template_id: "tpl-1",
      title: "Report",
      scope_id: "team",
    });
    expect(post).toHaveBeenNthCalledWith(2, "/api/reports/rep-1/finalise");
    expect(post).toHaveBeenNthCalledWith(3, "/api/reports/rep-1/export", {
      format: "csv",
    });
    expect(get).toHaveBeenCalledWith(
      "/api/reports/rep-1/preview?format=html",
      {},
    );
  });

  it("patches the captured snapshot", async () => {
    vi.mocked(patch).mockResolvedValue({ id: "rep-1" });
    await reportsApi.updateSnapshot("rep-1", { score: 10 });
    expect(patch).toHaveBeenCalledWith("/api/reports/rep-1/data", {
      data: { score: 10 },
    });
  });
});
