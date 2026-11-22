import { beforeEach, describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
const putMock = vi.fn();
const postMock = vi.fn();

vi.mock("../../api/client", () => ({
  get: (...args: unknown[]) => getMock(...args),
  put: (...args: unknown[]) => putMock(...args),
  post: (...args: unknown[]) => postMock(...args),
  del: vi.fn(),
}));

import {
  exportConfig,
  getPreferences,
  importConfig,
  updateLayout,
  updatePreferences,
} from "./api";

describe("settings-preferences api", () => {
  beforeEach(() => {
    getMock.mockReset();
    putMock.mockReset();
    postMock.mockReset();
  });

  it("calls preference endpoints with expected payloads", async () => {
    getMock.mockResolvedValueOnce({
      user_id: "default",
      values: {},
      defaults: {},
      schema_fields: [],
    });
    await getPreferences("alice");
    expect(getMock).toHaveBeenCalledWith("/api/preferences?user_id=alice");

    putMock.mockResolvedValueOnce({ user_id: "alice" });
    await updatePreferences("alice", { "appearance.theme": "dark" });
    expect(putMock).toHaveBeenCalledWith("/api/preferences", {
      user_id: "alice",
      values: { "appearance.theme": "dark" },
    });

    putMock.mockResolvedValueOnce({ user_id: "alice" });
    await updateLayout("alice", { density: "compact" });
    expect(putMock).toHaveBeenCalledWith("/api/preferences/layout", {
      user_id: "alice",
      density: "compact",
    });
  });

  it("handles import/export calls", async () => {
    getMock.mockResolvedValueOnce({ version: 1 });
    await exportConfig("alice");
    expect(getMock).toHaveBeenCalledWith(
      "/api/preferences/import?user_id=alice",
    );

    postMock.mockResolvedValueOnce({ version: 1 });
    await importConfig("alice", { version: 1 });
    expect(postMock).toHaveBeenCalledWith("/api/preferences/import", {
      user_id: "alice",
      config: { version: 1 },
    });
  });
});
