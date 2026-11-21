import { createElement, lazy, Suspense } from "react";
import type { FeaturePlugin } from "../plugins";
import "./admin-console.css";

const AdminPage = lazy(() =>
  import("./AdminPage").then((module) => ({ default: module.AdminPage })),
);

function AdminRoute() {
  return createElement(
    Suspense,
    {
      fallback: createElement(
        "div",
        { role: "status" },
        "Loading administration console…",
      ),
    },
    createElement(AdminPage),
  );
}

export const plugin: FeaturePlugin = {
  id: "admin",
  label: "Admin",
  path: "/admin",
  description: "Moderation, account controls and platform health",
  group: "Settings",
  component: AdminRoute,
};
