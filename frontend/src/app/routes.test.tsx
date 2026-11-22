import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { buildRoutes, NAVIGATION_ROUTES } from "./routes";
import { navigationFor } from "./AppShell";

describe("routes", () => {
  it("maps the navigation entries to their path", () => {
    expect(NAVIGATION_ROUTES.overview).toBe("/");
    expect(NAVIGATION_ROUTES.challenges).toBe("/challenges");
    expect(NAVIGATION_ROUTES.members).toBe("/members");
  });

  it("builds a route tree covering every page", () => {
    const routes = buildRoutes();
    const paths = routes.map((route) => route.path);
    expect(paths).toContain("/");
    expect(paths).toContain("/challenges");
    expect(paths).toContain("/members");
    expect(paths).toContain("/analytics");
    expect(paths).toContain("/activity");
    expect(paths).toContain("/settings");
    expect(paths).toContain("*");
  });

  it("renders the not found page for an unknown path", async () => {
    render(
      <MemoryRouter
        initialEntries={["/does-not-exist"]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          {buildRoutes().map((route) => (
            <Route key={route.path} path={route.path} element={route.element} />
          ))}
        </Routes>
      </MemoryRouter>,
    );

    expect(
      await screen.findByText("This screen does not exist"),
    ).toBeInTheDocument();
  });
});

describe("navigationFor", () => {
  it("resolves the navigation entry of a pathname", () => {
    expect(navigationFor("/")).toBe("overview");
    expect(navigationFor("/challenges")).toBe("challenges");
    expect(navigationFor("/challenges/challenge-1")).toBe("challenges");
    expect(navigationFor("/members")).toBe("members");
    expect(navigationFor("/analytics")).toBe("analytics");
    expect(navigationFor("/activity")).toBe("activity");
    expect(navigationFor("/settings")).toBe("settings");
  });

  it("falls back to the overview for unknown paths", () => {
    expect(navigationFor("/unknown")).toBe("overview");
  });
});
