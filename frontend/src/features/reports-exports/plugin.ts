import type { FeaturePlugin } from "../plugins";
import { ReportsPage } from "./ReportsPage";

export const plugin: FeaturePlugin = {
  id: "reports",
  label: "Reports",
  path: "/reports",
  description: "Compose, preview and export structured team reports.",
  group: "Analysis",
  component: ReportsPage,
};
