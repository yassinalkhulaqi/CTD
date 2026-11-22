/** The routed Languages page. */

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { toApiError } from "../../api";
import {
  CalendarDays,
  CheckCircle2,
  Globe2,
  MessageSquare,
  Plus,
  RefreshCw,
} from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  ErrorState,
  Input,
  Spinner,
  StatCard,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../../components/ui";
import {
  useCompleteness,
  useCreateLocale,
  useFormatRules,
  useLocales,
  useMessages,
  useMissingKeys,
  useUpdateFormatRule,
  useUpsertMessages,
} from "./hooks";
import { CompletenessTable } from "./components/CompletenessTable";
import { FormatPlayground } from "./components/FormatPlayground";
import { LocalePreview } from "./components/LocalePreview";
import { LocaleSwitcher } from "./components/LocaleSwitcher";
import { MessageEditor } from "./components/MessageEditor";
import { MissingKeyList } from "./components/MissingKeyList";
import type { MessageDraft } from "./types";
import styles from "./LanguagesPage.module.css";

const EMPTY_DRAFT: MessageDraft = {
  locale: "en",
  namespace: "ui",
  key: "",
  value: "",
};

/**
 * Render the languages workspace.
 *
 * @returns The languages page element.
 */
export function LanguagesPage() {
  const [activeLocale, setActiveLocale] = useState("en");
  const [tab, setTab] = useState("overview");
  const [draft, setDraft] = useState<MessageDraft>(EMPTY_DRAFT);
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [feedback, setFeedback] = useState("");

  const localesQuery = useLocales();
  const messagesQuery = useMessages();
  const completenessQuery = useCompleteness();
  const missingQuery = useMissingKeys(activeLocale);
  const rulesQuery = useFormatRules();
  const createLocale = useCreateLocale();
  const upsertMessages = useUpsertMessages();
  const updateRule = useUpdateFormatRule();

  const locales = useMemo(() => localesQuery.data ?? [], [localesQuery.data]);

  useEffect(() => {
    if (
      !locales.some((locale) => locale.code === activeLocale) &&
      locales.length > 0
    ) {
      setActiveLocale(locales[0].code);
    }
  }, [activeLocale, locales]);

  useEffect(() => {
    setDraft((current) => ({ ...current, locale: activeLocale }));
  }, [activeLocale]);

  const active = locales.find((locale) => locale.code === activeLocale) ?? null;
  const rule = rulesQuery.data?.find((item) => item.locale === activeLocale);
  const messages = (messagesQuery.data ?? []).filter(
    (message) => message.locale === activeLocale,
  );
  const stats = useMemo(
    () => completenessQuery.data ?? [],
    [completenessQuery.data],
  );
  const average = useMemo(() => {
    if (stats.length === 0) return 0;
    return Math.round(
      stats.reduce((sum, item) => sum + item.percent, 0) / stats.length,
    );
  }, [stats]);
  const rtlCount = locales.filter((locale) => locale.is_rtl).length;

  const handleRegister = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!newCode.trim() || !newName.trim()) return;
    const result = await createLocale.mutate({
      code: newCode.trim(),
      name: newName.trim(),
    });
    if (result) {
      setActiveLocale(result.code);
      setNewCode("");
      setNewName("");
      setFeedback(`${result.name} registered.`);
    } else {
      setFeedback(toApiError(createLocale.error).message);
    }
  };

  const handleSaveMessage = async () => {
    const result = await upsertMessages.mutate({
      locale: draft.locale,
      namespace: draft.namespace,
      messages: { [draft.key]: draft.value },
    });
    setFeedback(
      result
        ? `Saved ${draft.namespace}:${draft.key} for ${draft.locale}.`
        : toApiError(upsertMessages.error).message,
    );
  };

  const handleSaveRule = async (numberPattern: string, datePattern: string) => {
    const result = await updateRule.mutate({
      locale: activeLocale,
      number_pattern: numberPattern,
      date_pattern: datePattern,
    });
    setFeedback(
      result
        ? `Formatting rules saved for ${activeLocale}.`
        : toApiError(updateRule.error).message,
    );
  };

  if (localesQuery.isLoading) {
    return (
      <div className={styles.center} role="status">
        <Spinner label="Loading languages" size={24} />
        <span>Loading language catalogue…</span>
      </div>
    );
  }

  if (localesQuery.error) {
    return (
      <ErrorState
        title="The language catalogue could not be loaded"
        message={toApiError(localesQuery.error).message}
        onRetry={() => void localesQuery.refetch()}
      />
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Languages</h1>
          <p className={styles.subtitle}>
            Manage locales, translation catalogues and locale-aware formatting.
          </p>
        </div>
        <LocaleSwitcher
          locales={locales}
          value={activeLocale}
          onChange={setActiveLocale}
        />
      </header>

      {feedback ? (
        <p className={styles.feedback} role="status">
          {feedback}
        </p>
      ) : null}

      <div className={styles.stats}>
        <StatCard
          label="Locales"
          value={locales.length}
          icon={<Globe2 size={16} />}
          accent="var(--accent-base)"
        />
        <StatCard
          label="Messages"
          value={messagesQuery.data?.length ?? 0}
          icon={<MessageSquare size={16} />}
          accent="var(--info-base)"
        />
        <StatCard
          label="RTL locales"
          value={rtlCount}
          icon={<CheckCircle2 size={16} />}
          accent="var(--warning-base)"
        />
        <StatCard
          label="Avg completeness"
          value={`${average}%`}
          icon={<CalendarDays size={16} />}
          accent="var(--success-base)"
        />
      </div>

      <Tabs value={tab} onValueChange={setTab} label="Languages sections">
        <TabsList scrollable>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="messages" badge={messages.length}>
            Messages
          </TabsTrigger>
          <TabsTrigger value="formatting">Formatting</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className={styles.section}>
          <div className={styles.overviewGrid}>
            <Card as="section" aria-label="Locale preview">
              <CardHeader>
                <CardTitle>Layout direction</CardTitle>
                <CardDescription>
                  See how the interface mirrors for the selected language.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <LocalePreview locale={active} />
              </CardContent>
            </Card>
            <Card as="section" aria-label="Register locale">
              <CardHeader>
                <CardTitle>Register a locale</CardTitle>
                <CardDescription>
                  Add a language before authoring its message catalogue.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form
                  className={styles.register}
                  onSubmit={(event: FormEvent<HTMLFormElement>) =>
                    void handleRegister(event)
                  }
                >
                  <Input
                    label="Code"
                    value={newCode}
                    placeholder="es-MX"
                    onChange={(event) => setNewCode(event.target.value)}
                  />
                  <Input
                    label="Name"
                    value={newName}
                    placeholder="Spanish (Mexico)"
                    onChange={(event) => setNewName(event.target.value)}
                  />
                  <Button
                    type="submit"
                    icon={<Plus size={14} />}
                    loading={createLocale.isPending}
                  >
                    Register
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
          <Card as="section" aria-label="Translation completeness">
            <CardHeader
              actions={
                <Button
                  size="sm"
                  variant="secondary"
                  icon={<RefreshCw size={14} />}
                  onClick={() => void completenessQuery.refetch()}
                >
                  Refresh
                </Button>
              }
            >
              <CardTitle>Translation completeness</CardTitle>
              <CardDescription>
                Coverage of every locale against the English reference
                catalogue.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <CompletenessTable
                stats={stats}
                selectedLocale={activeLocale}
                onSelect={setActiveLocale}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="messages" className={styles.section}>
          <div className={styles.overviewGrid}>
            <Card as="section" aria-label="Message editor">
              <CardHeader>
                <CardTitle>Message editor</CardTitle>
                <CardDescription>
                  Edit a catalogue entry for {activeLocale}.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <MessageEditor
                  locales={locales}
                  draft={draft}
                  onChange={setDraft}
                  onSave={() => void handleSaveMessage()}
                  saving={upsertMessages.isPending}
                  error={
                    upsertMessages.error
                      ? toApiError(upsertMessages.error).message
                      : undefined
                  }
                />
              </CardContent>
            </Card>
            <Card as="section" aria-label="Stored messages">
              <CardHeader>
                <CardTitle>Stored messages</CardTitle>
                <CardDescription>
                  Select an entry to load it into the editor.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {messages.length === 0 ? (
                  <p className={styles.empty}>
                    No messages for {activeLocale} yet.
                  </p>
                ) : (
                  <ul className={styles.messageList}>
                    {messages.map((message) => (
                      <li key={message.id}>
                        <Button
                          variant="subtle"
                          size="sm"
                          onClick={() =>
                            setDraft({
                              locale: message.locale,
                              namespace: message.namespace,
                              key: message.key,
                              value: message.value,
                            })
                          }
                        >
                          {message.qualified_key}
                        </Button>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>
          <Card as="section" aria-label="Missing keys">
            <CardHeader>
              <CardTitle>Missing keys</CardTitle>
              <CardDescription>
                Reference strings that {activeLocale} still needs to translate.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MissingKeyList
                items={(missingQuery.data ?? []).filter(
                  (item) => item.locale === activeLocale,
                )}
                locale={activeLocale}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="formatting" className={styles.section}>
          <Card as="section" aria-label="Formatting playground">
            <CardHeader>
              <CardTitle>Formatting playground</CardTitle>
              <CardDescription>
                Experiment with number and date patterns, then save them for{" "}
                {activeLocale}.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FormatPlayground
                locale={activeLocale}
                rule={rule}
                onSaveRule={(numberPattern, datePattern) =>
                  void handleSaveRule(numberPattern, datePattern)
                }
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
