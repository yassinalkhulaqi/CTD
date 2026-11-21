import type { FeaturePlugin } from "../plugins";
import { PreferencesPage } from "./PreferencesPage";

export const plugin: FeaturePlugin = {
  id: "preferences",
  label: "Preferences",
  path: "/preferences",
  description: "Appearance, workspace, and notification settings",
  group: "Settings",
  component: PreferencesPage,
};
