/** Dynamic feature plugin declaration for the hint engine. */

import type { FeaturePlugin } from "../plugins";
import { HintsPage } from "./HintsPage";

export const plugin: FeaturePlugin = {
  id: "hints",
  label: "Hints",
  path: "/hints",
  description: "Tiered hints, shared budgets and a transparent reveal ledger",
  group: "Workspace",
  component: HintsPage,
};
