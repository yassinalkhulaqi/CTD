/** Channel and kind preference controls with quiet hours. */

import { Moon, Settings2 } from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Switch,
} from "../../../components/ui";
import {
  CHANNELS,
  CHANNEL_LABELS,
  KINDS,
  KIND_LABELS,
  formatHour,
  isPreferenceEnabled,
  isWithinQuietHours,
} from "../logic";
import type { Channel, NotificationKind, Preference } from "../types";
import styles from "./PreferencePanel.module.css";

/** Props accepted by {@link PreferencePanel}. */
export interface PreferencePanelProps {
  /** The effective preference matrix. */
  preferences: Preference[];
  /** Called when a switch is toggled. */
  onToggle: (
    channel: Channel,
    kind: NotificationKind,
    enabled: boolean,
  ) => void;
  /** Called when a quiet window changes. */
  onQuietChange: (channel: Channel, start: number, end: number) => void;
  /** Called to persist the current matrix. */
  onSave: () => void;
  /** Whether a save is in flight. */
  saving: boolean;
}

/**
 * Render the preference matrix grouped by channel.
 *
 * @param props - The component props.
 * @returns The preference panel.
 */
export function PreferencePanel({
  preferences,
  onToggle,
  onQuietChange,
  onSave,
  saving,
}: PreferencePanelProps) {
  const nowHour = new Date().getHours();
  const wildcardFor = (channel: Channel): Preference | undefined =>
    preferences.find((item) => item.channel === channel && item.kind === "*");

  return (
    <Card
      className={styles.panel}
      as="section"
      aria-labelledby="preference-title"
    >
      <CardHeader
        actions={
          <Button
            size="sm"
            variant="secondary"
            onClick={onSave}
            disabled={saving}
          >
            Save preferences
          </Button>
        }
      >
        <CardTitle level={2} id="preference-title">
          <Settings2 size={16} aria-hidden="true" /> Delivery preferences
        </CardTitle>
        <p className={styles.hint}>Choose which events reach each channel.</p>
      </CardHeader>
      <CardContent>
        <div className={styles.channels}>
          {CHANNELS.map((channel) => {
            const wildcard = wildcardFor(channel);
            const start = wildcard?.quiet_start_hour ?? 0;
            const end = wildcard?.quiet_end_hour ?? 0;
            const quiet = isWithinQuietHours(start, end, nowHour);
            return (
              <section key={channel} className={styles.channel}>
                <header className={styles.channelHeader}>
                  <h3>{CHANNEL_LABELS[channel]}</h3>
                  <span
                    className={quiet ? styles.quietActive : styles.quietIdle}
                    aria-label={
                      quiet
                        ? "Quiet hours active now"
                        : "Quiet hours inactive now"
                    }
                  >
                    <Moon size={13} aria-hidden="true" />
                    {formatHour(start)}–{formatHour(end)}
                  </span>
                </header>
                <div className={styles.switches}>
                  {KINDS.map((kind) => (
                    <Switch
                      key={`${channel}-${kind}`}
                      checked={isPreferenceEnabled(preferences, channel, kind)}
                      onChange={(event) =>
                        onToggle(channel, kind, event.target.checked)
                      }
                      aria-label={`${CHANNEL_LABELS[channel]} ${KIND_LABELS[kind]}`}
                    >
                      {KIND_LABELS[kind]}
                    </Switch>
                  ))}
                </div>
                <div className={styles.quietFields}>
                  <Input
                    type="number"
                    min={0}
                    max={23}
                    value={start}
                    onChange={(event) =>
                      onQuietChange(channel, Number(event.target.value), end)
                    }
                    aria-label={`${CHANNEL_LABELS[channel]} quiet start hour`}
                    label="Quiet from"
                  />
                  <Input
                    type="number"
                    min={0}
                    max={23}
                    value={end}
                    onChange={(event) =>
                      onQuietChange(channel, start, Number(event.target.value))
                    }
                    aria-label={`${CHANNEL_LABELS[channel]} quiet end hour`}
                    label="Quiet until"
                  />
                </div>
              </section>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
