/**
 * Plugin registration for the scoreboard feature.
 */

import type { FeaturePlugin } from "../plugins";
import { ScoreboardPage } from "./ScoreboardPage";

/** The scoreboard module contributed by this feature branch. */
export const plugin: FeaturePlugin = {
  id: "scoreboard",
  label: "Scoreboard",
  path: "/scoreboard",
  description: "Dynamic scoring, rank movement and scoring snapshots",
  group: "Analysis",
  component: ScoreboardPage,
};
