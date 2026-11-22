/**
 * Plugin registration for the Offline & Sync module.
 */

import type { FeaturePlugin } from "../plugins";
import { OfflinePage } from "./OfflinePage";

/** The offline sync plugin discovered by the module launcher. */
export const plugin: FeaturePlugin = {
  id: "offline",
  label: "Offline & Sync",
  path: "/offline",
  description: "Queue offline edits, reconcile conflicts and monitor sync health",
  group: "Operations",
  component: OfflinePage,
};
