/** Plugin registration for the visualisation gallery. */

import type { FeaturePlugin } from "../plugins";
import { VisualizationsPage } from "./VisualizationsPage";

export const plugin: FeaturePlugin = {
  id: "visualizations",
  label: "Visualizations",
  path: "/visualizations",
  description:
    "Responsive chart gallery with flows, radar profiles and sparklines",
  group: "Analysis",
  component: VisualizationsPage,
};
