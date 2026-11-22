/**
 * Plugin registration for the notes workspace feature.
 */

import type { FeaturePlugin } from "../plugins";
import { NotesPage } from "./NotesPage";

export const plugin: FeaturePlugin = {
  id: "notes",
  label: "Notes",
  path: "/notes",
  description: "Challenge notes, templates and revision history",
  group: "Workspace",
  component: NotesPage,
};
