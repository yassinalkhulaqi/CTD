/**
 * Plugin declaration of the onboarding tour feature.
 */

import type { FeaturePlugin } from "../plugins";
import OnboardingPage from "./OnboardingPage";

/** The module descriptor discovered by the dynamic plugin registry. */
export const plugin: FeaturePlugin = {
  id: "onboarding",
  label: "Onboarding",
  path: "/onboarding",
  description: "Setup wizard, guided tour and progress checklist",
  group: "Settings",
  component: OnboardingPage,
};
