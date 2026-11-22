/**
 * The integrations screen: endpoints, delivery ledger, adapters and stats.
 */

import { useState } from "react";
import { Plus, Send, Webhook } from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  Input,
  SegmentedControl,
  Select,
  Spinner,
  Switch,
  Textarea,
} from "../../components/ui";
import {
  AdapterCard,
  DeliveryInspector,
  EventSelector,
  IntegrationCard,
  IntegrationStats,
  SecretField,
} from "./components";
import { useIntegrations } from "./hooks";
import { eventLabel, validateDraft } from "./logic";
import {
  ALL_EVENTS,
  EMPTY_DRAFT,
  EVENT_LABELS,
  INTEGRATION_KINDS,
  type DeliveryStatus,
  type Integration,
  type IntegrationDraft,
} from "./types";
import styles from "./IntegrationsPage.module.css";

type View = "integrations" | "deliveries" | "adapters";

const VIEW_OPTIONS = [
  { value: "integrations" as const, label: "Integrations" },
  { value: "deliveries" as const, label: "Deliveries" },
  { value: "adapters" as const, label: "Adapters" },
];

/** Read a JSON object from a textarea, returning a parse error message. */
function parseObject(text: string): {
  value: Record<string, unknown> | null;
  error: string | null;
} {
  if (!text.trim()) return { value: {}, error: null };
  try {
    const parsed: unknown = JSON.parse(text);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      return { value: null, error: "Enter a JSON object" };
    }
    return { value: parsed as Record<string, unknown>, error: null };
  } catch {
    return { value: null, error: "Payload is not valid JSON" };
  }
}

/**
 * Render the routed integrations page.
 *
 * @returns The page element.
 */
export default function IntegrationsPage() {
  const controller = useIntegrations();
  const [view, setView] = useState<View>("integrations");
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<IntegrationDraft>(EMPTY_DRAFT);
  const [draftErrors, setDraftErrors] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState<string | null>(null);
  const [dispatchEventName, setDispatchEventName] =
    useState("challenge.solved");
  const [dispatchPayload, setDispatchPayload] = useState(
    '{\n  "challenge": "web-100"\n}',
  );
  const [dispatchError, setDispatchError] = useState<string | null>(null);
  const [adapterOpen, setAdapterOpen] = useState(false);
  const [adapterName, setAdapterName] = useState("");
  const [adapterMap, setAdapterMap] = useState(
    '{\n  "challenge.solved": "score.changed"\n}',
  );
  const [adapterError, setAdapterError] = useState<string | null>(null);

  const patchDraft = (changes: Partial<IntegrationDraft>): void => {
    setDraft((current) => ({ ...current, ...changes }));
    setDraftErrors({});
  };

  const openCreate = (): void => {
    setEditingId(null);
    setDraft(EMPTY_DRAFT);
    setDraftErrors({});
    setFormOpen(true);
  };

  const openEdit = (integration: Integration): void => {
    setEditingId(integration.id);
    setDraft({
      name: integration.name,
      kind: integration.kind,
      endpoint_url: integration.endpoint_url,
      events: [...integration.events],
      secret: "",
      enabled: integration.enabled,
    });
    setDraftErrors({});
    setFormOpen(true);
  };

  const saveIntegration = async (): Promise<void> => {
    const errors = validateDraft(draft);
    if (Object.keys(errors).length > 0) {
      setDraftErrors(errors);
      return;
    }
    if (editingId) {
      await controller.update(editingId, {
        name: draft.name,
        kind: draft.kind,
        endpoint_url: draft.endpoint_url,
        events: draft.events,
        enabled: draft.enabled,
        ...(draft.secret ? { secret: draft.secret } : {}),
      });
      setNotice(`Updated ${draft.name}`);
    } else {
      await controller.create({ ...draft });
      setNotice(`Created ${draft.name}`);
    }
    setFormOpen(false);
  };

  const toggleIntegration = async (
    integration: Integration,
    enabled: boolean,
  ): Promise<void> => {
    await controller.update(integration.id, { enabled });
    setNotice(`${integration.name} ${enabled ? "enabled" : "paused"}`);
  };

  const removeIntegration = async (integration: Integration): Promise<void> => {
    await controller.remove(integration.id);
    setNotice(`${integration.name} deleted`);
  };

  const sendTest = async (integration: Integration): Promise<void> => {
    const event = integration.events[0] ?? "challenge.solved";
    await controller.dispatch({
      event,
      payload: { source: "integration-test", integration: integration.name },
    });
    setView("deliveries");
    setNotice(`Dispatched ${event} to ${integration.name}`);
  };

  const dispatchTest = async (): Promise<void> => {
    const parsed = parseObject(dispatchPayload);
    if (parsed.error || !parsed.value) {
      setDispatchError(parsed.error ?? "Invalid payload");
      return;
    }
    setDispatchError(null);
    await controller.dispatch({
      event: dispatchEventName,
      payload: parsed.value,
    });
    setNotice(`Dispatched ${eventLabel(dispatchEventName)}`);
  };

  const addAdapter = async (): Promise<void> => {
    const parsed = parseObject(adapterMap);
    if (parsed.error || !parsed.value) {
      setAdapterError(parsed.error ?? "Invalid mapping");
      return;
    }
    if (!adapterName.trim()) {
      setAdapterError("Give the adapter a name");
      return;
    }
    const eventMap: Record<string, string> = {};
    for (const [source, target] of Object.entries(parsed.value)) {
      if (typeof target !== "string" || !target.trim()) {
        setAdapterError("Every mapping target must be an event name");
        return;
      }
      eventMap[source.trim().toLowerCase()] = target.trim().toLowerCase();
    }
    setAdapterError(null);
    await controller.addAdapter({ name: adapterName, event_map: eventMap });
    setAdapterName("");
    setAdapterOpen(false);
    setNotice("Adapter created");
  };

  const runWithStatus = async (
    status: DeliveryStatus,
    deliveryId: string,
  ): Promise<void> => {
    await controller.simulate(deliveryId, { status, response_code: null });
    setNotice(`Delivery marked ${status}`);
  };

  const isBusy = (integration: Integration): boolean =>
    controller.busy === `update-${integration.id}` ||
    controller.busy === `delete-${integration.id}`;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>
            <Webhook size={22} aria-hidden="true" /> Integrations
          </h1>
          <p className={styles.subtitle}>
            Route CTF events to webhooks and team tools. Secrets are hashed on
            write and every delivery is recorded with its signed payload.
          </p>
        </div>
        <Button icon={<Plus size={15} />} onClick={openCreate}>
          New integration
        </Button>
      </header>

      {controller.error ? (
        <ErrorState
          message={controller.error}
          onRetry={() => void controller.refresh()}
        />
      ) : null}
      {notice ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}

      <IntegrationStats stats={controller.stats} loading={controller.loading} />

      {formOpen ? (
        <Card
          as="section"
          className={styles.formCard}
          aria-label="Integration form"
        >
          <CardHeader>
            <CardTitle level={3}>
              {editingId ? "Edit integration" : "New integration"}
            </CardTitle>
            <CardDescription>
              Choose an allowlisted event set and an http or https endpoint.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className={styles.formGrid}>
              <Input
                label="Name"
                value={draft.name}
                onChange={(event) => patchDraft({ name: event.target.value })}
                error={draftErrors.name}
                placeholder="Score alerts"
              />
              <Select
                label="Transport"
                value={draft.kind}
                onChange={(event) =>
                  patchDraft({
                    kind: event.target.value as IntegrationDraft["kind"],
                  })
                }
                options={INTEGRATION_KINDS.map((kind) => ({
                  value: kind.value,
                  label: kind.label,
                }))}
              />
              <Input
                label="Endpoint URL"
                value={draft.endpoint_url}
                onChange={(event) =>
                  patchDraft({ endpoint_url: event.target.value })
                }
                error={draftErrors.endpoint_url}
                placeholder="https://hooks.example.com/ctf"
                className={styles.wide}
              />
              <Switch
                checked={draft.enabled}
                onChange={(event) =>
                  patchDraft({ enabled: event.target.checked })
                }
                aria-label="Enable integration"
              >
                Enabled on save
              </Switch>
            </div>
            <EventSelector
              selected={draft.events}
              onChange={(events) => patchDraft({ events })}
              error={draftErrors.events}
            />
            <SecretField
              value={draft.secret}
              onChange={(secret) => patchDraft({ secret })}
              error={draftErrors.secret}
              configured={Boolean(editingId)}
              hint={
                editingId
                  ? "Leave blank to keep the existing signing digest."
                  : "Optional, at least 8 characters. Stored only as a digest."
              }
            />
          </CardContent>
          <CardContent className={styles.formActions}>
            <Button
              onClick={() => void saveIntegration()}
              loading={
                controller.busy === "create" ||
                Boolean(editingId && controller.busy)
              }
            >
              {editingId ? "Save changes" : "Create integration"}
            </Button>
            <Button variant="ghost" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader
          actions={
            <SegmentedControl
              options={VIEW_OPTIONS}
              value={view}
              onValueChange={(value) => setView(value as View)}
              label="Integration sections"
            />
          }
        >
          <CardTitle>Control plane</CardTitle>
        </CardHeader>
        <CardContent>
          {controller.loading ? (
            <div className={styles.loading}>
              <Spinner label="Loading integrations" /> Loading integrations…
            </div>
          ) : null}

          {view === "integrations" ? (
            controller.integrations.length === 0 ? (
              <EmptyState
                title="No integrations configured"
                description="Create a webhook to start forwarding CTF events."
                action={<Button onClick={openCreate}>Add integration</Button>}
              />
            ) : (
              <div className={styles.cardGrid}>
                {controller.integrations.map((integration) => (
                  <IntegrationCard
                    key={integration.id}
                    integration={integration}
                    busy={isBusy(integration)}
                    onToggle={(enabled) =>
                      void toggleIntegration(integration, enabled)
                    }
                    onEdit={() => openEdit(integration)}
                    onDelete={() => void removeIntegration(integration)}
                    onSendTest={() => void sendTest(integration)}
                  />
                ))}
              </div>
            )
          ) : null}

          {view === "deliveries" ? (
            <>
              <div className={styles.dispatch}>
                <Select
                  label="Event"
                  value={dispatchEventName}
                  onChange={(event) => setDispatchEventName(event.target.value)}
                  options={ALL_EVENTS.map((event) => ({
                    value: event,
                    label: EVENT_LABELS[event] ?? event,
                  }))}
                />
                <Textarea
                  label="Payload (JSON)"
                  value={dispatchPayload}
                  onChange={(event) => setDispatchPayload(event.target.value)}
                  error={dispatchError ?? undefined}
                  rows={4}
                  className={styles.wide}
                />
                <Button
                  icon={<Send size={14} />}
                  loading={controller.busy === "dispatch"}
                  onClick={() => void dispatchTest()}
                >
                  Dispatch test event
                </Button>
              </div>
              <DeliveryInspector
                deliveries={controller.deliveries}
                integrations={controller.integrations}
                busyId={controller.busy}
                onRetry={(deliveryId) => void controller.retry(deliveryId)}
                onSimulate={(deliveryId, status) =>
                  void runWithStatus(status, deliveryId)
                }
              />
            </>
          ) : null}

          {view === "adapters" ? (
            <>
              {adapterOpen ? (
                <div className={styles.adapterForm}>
                  <Input
                    label="Adapter name"
                    value={adapterName}
                    onChange={(event) => setAdapterName(event.target.value)}
                    placeholder="Score bridge"
                  />
                  <Textarea
                    label="Event map (JSON)"
                    value={adapterMap}
                    onChange={(event) => setAdapterMap(event.target.value)}
                    error={adapterError ?? undefined}
                    rows={4}
                  />
                  <div className={styles.formActions}>
                    <Button
                      loading={controller.busy === "adapter"}
                      onClick={() => void addAdapter()}
                    >
                      Save adapter
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => setAdapterOpen(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <Button
                  variant="secondary"
                  onClick={() => setAdapterOpen(true)}
                >
                  New adapter
                </Button>
              )}
              {controller.adapters.length === 0 ? (
                <EmptyState
                  title="No adapters configured"
                  description="Adapters rewrite event names before matching subscriptions."
                />
              ) : (
                <div className={styles.cardGrid}>
                  {controller.adapters.map((adapter) => (
                    <AdapterCard
                      key={adapter.id}
                      adapter={adapter}
                      busy={controller.busy === `adapter-${adapter.id}`}
                      onDelete={() => void controller.removeAdapter(adapter.id)}
                    />
                  ))}
                </div>
              )}
            </>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
