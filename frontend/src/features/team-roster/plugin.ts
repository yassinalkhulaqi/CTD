/**
 * Plugin registration for the team roster module.
 */

import type { FeaturePlugin } from "../plugins";
import { RosterPage } from "./RosterPage";

/** The roster plugin discovered by the foundation launcher. */
export const plugin: FeaturePlugin = {
  id: "roster",
  label: "Roster",
  path: "/roster",
  description: "Team roster, roles, availability and invitations",
  group: "Operations",
  component: RosterPage,
};
