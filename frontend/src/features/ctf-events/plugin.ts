/** Plugin declaration discovered by the module launcher. */

import type { FeaturePlugin } from "../plugins";
import { EventsPage } from "./EventsPage";

export const plugin: FeaturePlugin = {
  id: "events",
  label: "Events",
  path: "/events",
  description: "Event lifecycle, schedules, registration and countdowns",
  group: "Operations",
  component: EventsPage,
};
