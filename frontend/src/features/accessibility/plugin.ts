import type { FeaturePlugin } from "../plugins";
import { AccessibilityPage } from "./AccessibilityPage";

export const plugin: FeaturePlugin = {
  id: "accessibility",
  label: "Accessibility",
  path: "/accessibility",
  description:
    "Audit contrast, manage keyboard shortcuts and rehearse accessible focus paths.",
  group: "Settings",
  component: AccessibilityPage,
};
