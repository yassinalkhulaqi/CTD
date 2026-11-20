/** Plugin declaration for the notification centre. */

import type { FeaturePlugin } from "../plugins";
import { NotificationsPage } from "./NotificationsPage";

export const plugin: FeaturePlugin = {
  id: "notifications",
  label: "Notifications",
  path: "/notifications",
  description: "Notification centre with preferences, digests and toasts",
  group: "Workspace",
  component: NotificationsPage,
};
