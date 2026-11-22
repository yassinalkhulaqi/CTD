/**
 * The settings page.
 */

import { useState } from "react";
import { KeyRound, RotateCcw, ShieldCheck } from "lucide-react";
import { useAuth } from "../../features/auth/useAuth";
import {
  usePreferencesStore,
  DEFAULT_PREFERENCES,
} from "../../stores/preferencesStore";
import { useDashboardStore } from "../../stores/dashboardStore";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Select,
  Switch,
  ThemeToggle,
} from "../../components/ui";
import styles from "./SettingsPage.module.css";

const DENSITY_OPTIONS = [
  { value: "comfortable", label: "Comfortable" },
  { value: "compact", label: "Compact" },
];

const WINDOW_OPTIONS = [
  { value: "6h", label: "Last 6 hours" },
  { value: "12h", label: "Last 12 hours" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
];

/**
 * Render the settings page.
 *
 * @returns The page element.
 */
export default function SettingsPage() {
  const { user, principal } = useAuth();
  const preferences = usePreferencesStore();
  const resetFilters = useDashboardStore((state) => state.resetFilters);
  const [apiKeyName, setApiKeyName] = useState("");

  return (
    <div className={styles.page}>
      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>How the interface feels and reads.</CardDescription>
        </CardHeader>
        <CardContent className={styles.rows}>
          <div className={styles.row}>
            <div className={styles.rowText}>
              <span className={styles.rowTitle}>Colour theme</span>
              <span className={styles.rowDescription}>
                Choose the light, dark or automatic colour scheme.
              </span>
            </div>
            <ThemeToggle />
          </div>

          <div className={styles.row}>
            <div className={styles.rowText}>
              <span className={styles.rowTitle}>Information density</span>
              <span className={styles.rowDescription}>
                Control the spacing of the tables and the challenge board.
              </span>
            </div>
            <Select
              options={DENSITY_OPTIONS}
              value={preferences.density}
              onChange={(event) =>
                preferences.setDensity(
                  event.target.value as "comfortable" | "compact",
                )
              }
              hideLabel
              aria-label="Information density"
            />
          </div>

          <div className={styles.row}>
            <div className={styles.rowText}>
              <span className={styles.rowTitle}>Analytics window</span>
              <span className={styles.rowDescription}>
                The trailing window used by the velocity charts.
              </span>
            </div>
            <Select
              options={WINDOW_OPTIONS}
              value={preferences.timeWindow}
              onChange={(event) =>
                preferences.setTimeWindow(
                  event.target.value as "6h" | "12h" | "24h" | "7d",
                )
              }
              hideLabel
              aria-label="Analytics window"
            />
          </div>

          <div className={styles.row}>
            <div className={styles.rowText}>
              <span className={styles.rowTitle}>Animated numbers</span>
              <span className={styles.rowDescription}>
                Animate the counters when the values change.
              </span>
            </div>
            <Switch
              checked={preferences.animatedNumbers}
              onChange={() => preferences.toggleAnimatedNumbers()}
            >
              <span className={styles.visuallyHidden}>Animated numbers</span>
            </Switch>
          </div>

          <div className={styles.row}>
            <div className={styles.rowText}>
              <span className={styles.rowTitle}>Pinned activity feed</span>
              <span className={styles.rowDescription}>
                Keep the activity feed visible while scrolling the board.
              </span>
            </div>
            <Switch
              checked={preferences.activityFeedPinned}
              onChange={() => preferences.toggleActivityFeed()}
            >
              <span className={styles.visuallyHidden}>
                Pinned activity feed
              </span>
            </Switch>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Session</CardTitle>
        </CardHeader>
        <CardContent className={styles.rows}>
          <div className={styles.row}>
            <div className={styles.rowText}>
              <span className={styles.rowTitle}>Signed in as</span>
              <span className={styles.rowDescription}>
                {user
                  ? `${user.username} · ${user.email}`
                  : "Open mode — no account required."}
              </span>
            </div>
            {principal ? (
              <Badge tone="accent">{principal.role}</Badge>
            ) : (
              <Badge tone="neutral">anonymous</Badge>
            )}
          </div>

          <div className={styles.row}>
            <div className={styles.rowText}>
              <span className={styles.rowTitle}>Permissions</span>
              <span className={styles.rowDescription}>
                {principal && principal.permissions.length > 0
                  ? principal.permissions.join(", ")
                  : "No permission is required in open mode."}
              </span>
            </div>
            <ShieldCheck size={16} aria-hidden="true" />
          </div>

          <div className={styles.row}>
            <div className={styles.rowText}>
              <span className={styles.rowTitle}>API keys</span>
              <span className={styles.rowDescription}>
                Machine credentials used by the ingestion bots.
              </span>
            </div>
            <div className={styles.keyRow}>
              <Input
                value={apiKeyName}
                onChange={(event) => setApiKeyName(event.target.value)}
                placeholder="Key name"
                hideLabel
                aria-label="API key name"
              />
              <Button
                variant="secondary"
                icon={<KeyRound size={14} />}
                disabled={!apiKeyName.trim()}
              >
                Create
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Danger zone</CardTitle>
        </CardHeader>
        <CardContent className={styles.rows}>
          <div className={styles.row}>
            <div className={styles.rowText}>
              <span className={styles.rowTitle}>Reset the workspace</span>
              <span className={styles.rowDescription}>
                Clear the filters and restore the default preferences.
              </span>
            </div>
            <Button
              variant="danger"
              icon={<RotateCcw size={14} />}
              onClick={() => {
                preferences.reset();
                resetFilters();
              }}
            >
              Reset
            </Button>
          </div>
          <p className={styles.note}>
            The default page size is {DEFAULT_PREFERENCES.pageSize} rows and the
            default time window is {DEFAULT_PREFERENCES.timeWindow}.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
