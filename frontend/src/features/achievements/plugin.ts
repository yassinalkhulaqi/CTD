/**
 * Plugin declaration for the achievements module.
 */

import type { FeaturePlugin } from "../plugins";
import { AchievementsPage } from "./AchievementsPage";

/** The achievements plugin contributes the gallery route. */
export const plugin: FeaturePlugin = {
  id: "achievements",
  label: "Achievements",
  path: "/achievements",
  description: "Badge catalogue, progress rings and unlocks",
  group: "Progress",
  component: AchievementsPage,
};
