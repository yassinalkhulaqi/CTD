/**
 * Plugin declaration for the submission pipeline module.
 */

import type { FeaturePlugin } from "../plugins";
import { SubmissionsPage } from "./SubmissionsPage";

/** Registers the submissions screen with the dashboard launcher. */
export const plugin: FeaturePlugin = {
  id: "submissions",
  label: "Submissions",
  path: "/submissions",
  description:
    "Flag submission console with validation, deduplication and retries",
  group: "Operations",
  component: SubmissionsPage,
};
