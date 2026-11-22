/** Plugin registration for the writeups library. */

import type { FeaturePlugin } from "../plugins";
import { WriteupsPage } from "./WriteupsPage";

/** The writeups library feature plugin. */
export const plugin: FeaturePlugin = {
  id: "writeups",
  label: "Writeups",
  path: "/writeups",
  description:
    "A curated library of solved-challenge writeups, ratings and peer review",
  group: "Knowledge",
  component: WriteupsPage,
};
