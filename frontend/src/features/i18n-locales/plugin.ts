/** Plugin registration for the languages workspace. */

import type { FeaturePlugin } from "../plugins";
import { LanguagesPage } from "./LanguagesPage";

/** The languages plugin contributed to the module launcher. */
export const plugin: FeaturePlugin = {
  id: "languages",
  label: "Languages",
  path: "/languages",
  description: "Locale catalogue, translations and formatting rules",
  group: "Settings",
  component: LanguagesPage,
};
