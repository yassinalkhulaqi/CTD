/** Plugin declaration for the search workspace. */

import type { FeaturePlugin } from "../plugins";
import { SearchPage } from "./SearchPage";

/** The search feature contributed to the module launcher. */
export const plugin: FeaturePlugin = {
  id: "search",
  label: "Search",
  path: "/search",
  description: "Unified search index and command palette",
  group: "Workspace",
  component: SearchPage,
};
