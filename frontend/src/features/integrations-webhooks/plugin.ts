/**
 * Plugin registration for the integrations feature.
 */

import type { FeaturePlugin } from "../plugins";
import IntegrationsPage from "./IntegrationsPage";

export const plugin: FeaturePlugin = {
  id: "integrations",
  label: "Integrations",
  path: "/integrations",
  description: "Webhook endpoints, signed deliveries and event adapters",
  group: "Operations",
  component: IntegrationsPage,
};
