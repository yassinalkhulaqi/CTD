/**
 * Plugin registration for the activity timeline feature.
 */

import type { FeaturePlugin } from "../plugins";
import { TimelinePage } from "./TimelinePage";

export const plugin: FeaturePlugin = {
  id: "timeline",
  label: "Timeline",
  path: "/timeline",
  description: "Live activity feed with filters, grouping and statistics",
  group: "Analysis",
  component: TimelinePage,
};
