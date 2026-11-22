import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { configureAuth } from "../../api/client";
import { onboardingApi } from "./api";
import type { OnboardingStep, ProgressSummary } from "./types";

const originalFetch = globalThis.fetch;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function mockFetch(body: unknown) {
  const spy = vi.fn(
    (_input: RequestInfo | URL, _init?: RequestInit): Promise<Response> =>
      Promise.resolve(jsonResponse(body)),
  );
  globalThis.fetch = spy as unknown as typeof fetch;
  return spy;
}

const step: OnboardingStep = {
  id: "step-welcome",
  slug: "welcome",
  title: "Welcome",
  description: "Start here",
  target: "#hero",
  order: 1,
  completion_key: "tour.welcome",
  kind: "welcome",
  estimated_seconds: 45,
  required: true,
  hint: "Hint",
  icon: "sparkles",
  created_at: "2026-01-01T00:00:00Z",
  state: "active",
  is_current: true,
  target_kind: "anchor",
  duration_label: "45s",
};

const summary: ProgressSummary = {
  user_id: "alice",
  status: "not-started",
  total: 1,
  completed: 0,
  skipped: 0,
  remaining: 1,
  percent: 0,
  checklist_percent: 0,
  steps: [step],
  records: [],
  next_step: step,
  checklist: {
    user_id: "alice",
    items: [],
    completed: 0,
    total: 0,
    percent: 0,
    updated_at: "2026-01-01T00:00:00Z",
  },
  resume: {
    can_resume: false,
    next_step_slug: "welcome",
    percent: 0,
    last_activity_at: null,
    message: "Start when ready",
  },
  welcome_note: {
    id: "note-1",
    user_id: "alice",
    title: "Welcome",
    body: "Hello",
    tone: "info",
    word_count: 2,
    reading_seconds: 1,
    created_at: "2026-01-01T00:00:00Z",
  },
};

describe("onboardingApi", () => {
  beforeEach(() => {
    configureAuth(() => null);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("loads steps with the user identifier encoded", async () => {
    const spy = mockFetch([step]);
    await expect(onboardingApi.listSteps("a b")).resolves.toEqual([step]);
    expect(String(spy.mock.calls[0][0])).toBe(
      "/api/onboarding/steps?user_id=a%20b",
    );
  });

  it("loads the progress summary and next step", async () => {
    mockFetch(summary);
    await expect(onboardingApi.getProgress("alice")).resolves.toEqual(summary);
    const spy = mockFetch(step);
    await expect(onboardingApi.getNext("alice")).resolves.toEqual(step);
    expect(String(spy.mock.calls[0][0])).toContain("/api/onboarding/next");
  });

  it("completes and skips steps over POST", async () => {
    const action = {
      step,
      message: "Done",
      finished: false,
      progress: summary,
    };
    const spy = mockFetch(action);
    await expect(
      onboardingApi.completeStep("welcome", "alice"),
    ).resolves.toEqual(action);
    expect(String(spy.mock.calls[0][0])).toBe(
      "/api/onboarding/steps/welcome/complete?user_id=alice",
    );
    expect(spy.mock.calls[0][1]?.method).toBe("POST");
    const skipSpy = mockFetch(action);
    await onboardingApi.skipStep("step-welcome", "alice");
    expect(String(skipSpy.mock.calls[0][0])).toContain(
      "/api/onboarding/steps/step-welcome/skip",
    );
  });

  it("replaces and toggles checklist items over PUT", async () => {
    const checklist = summary.checklist;
    const spy = mockFetch(checklist);
    await expect(
      onboardingApi.putChecklist("alice", [
        { id: "one", label: "First", done: true },
      ]),
    ).resolves.toEqual(checklist);
    expect(spy.mock.calls[0][1]?.method).toBe("PUT");
    expect(spy.mock.calls[0][1]?.body).toContain("First");

    const toggleSpy = mockFetch(checklist);
    await onboardingApi.setChecklistItem("alice", "item/one", true);
    expect(String(toggleSpy.mock.calls[0][0])).toBe(
      "/api/onboarding/checklist/item%2Fone?user_id=alice",
    );
    expect(toggleSpy.mock.calls[0][1]?.body).toBe('{"done":true}');
  });

  it("resets progress and validates targets", async () => {
    const resetSpy = mockFetch({
      user_id: "alice",
      removed_progress: 1,
      removed_checklist: false,
      message: "Reset",
      checklist: summary.checklist,
      progress: summary,
    });
    await onboardingApi.reset("alice");
    expect(String(resetSpy.mock.calls[0][0])).toBe(
      "/api/onboarding/reset?user_id=alice",
    );

    const targetSpy = mockFetch({
      target: "#hero",
      valid: true,
      kind: "anchor",
      reason: "element id",
      label: "anchor",
    });
    await expect(onboardingApi.checkTarget("#hero")).resolves.toMatchObject({
      valid: true,
    });
    expect(targetSpy.mock.calls[0][1]?.body).toBe('{"target":"#hero"}');
  });
});
