/** Routed search workspace with a global command palette. */

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Command as CommandIcon, DatabaseZap, Search } from "lucide-react";
import { toApiError } from "../../api/client";
import { Button, Card, Spinner } from "../../components/ui";
import { searchApi } from "./api";
import { CommandPalette } from "./components/CommandPalette";
import { SearchFilters } from "./components/SearchFilters";
import { SearchResults } from "./components/SearchResults";
import { useCommandsFeed, useRecentQueries, useSearchFeed } from "./hooks";
import { parseQueryText } from "./searchUtils";
import type { Command, SearchKind, SearchResult, SearchStats } from "./types";
import styles from "./SearchPage.module.css";

/** Navigate within the SPA without reloading the document. */
function navigateTo(target: string): void {
  window.history.pushState({}, "", target);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

/**
 * Render the search page and register the global palette shortcut.
 *
 * @returns The search workspace element.
 */
export function SearchPage() {
  const [query, setQuery] = useState("");
  const [kinds, setKinds] = useState<SearchKind[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [limit, setLimit] = useState(20);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [stats, setStats] = useState<SearchStats | null>(null);
  const [rebuilding, setRebuilding] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const feed = useSearchFeed(query, kinds, tags, limit);
  const commandsFeed = useCommandsFeed();
  const recent = useRecentQueries();
  const parsed = parseQueryText(query);

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    let active = true;
    searchApi
      .stats()
      .then((payload) => {
        if (active) setStats(payload);
      })
      .catch(() => {
        if (active) setStats(null);
      });
    return () => {
      active = false;
    };
  }, [feed.results?.returned, rebuilding]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    recent.remember(parsed.text || query);
    inputRef.current?.blur();
  }

  function toggleKind(kind: SearchKind) {
    setKinds((current) =>
      current.includes(kind)
        ? current.filter((item) => item !== kind)
        : [...current, kind],
    );
  }

  function applyRecent(value: string) {
    setQuery(value);
    recent.remember(value);
    inputRef.current?.focus();
  }

  function openResult(result: SearchResult) {
    recent.remember(parsed.text || query);
    navigateTo(result.path);
  }

  async function rebuildIndex() {
    setRebuilding(true);
    setNotice(null);
    try {
      const result = await searchApi.index({ include_repositories: true });
      feed.refresh();
      setNotice(`Indexed ${result.indexed} documents.`);
    } catch (cause) {
      setNotice(toApiError(cause).message);
    } finally {
      setRebuilding(false);
    }
  }

  async function executeCommand(command: Command) {
    try {
      const execution = await searchApi.execute(command.id);
      setNotice(execution.message);
      if (execution.is_navigation) navigateTo(execution.target);
      if (execution.target === "/search") inputRef.current?.focus();
    } catch (cause) {
      setNotice(toApiError(cause).message);
    }
  }

  const results = feed.results?.results ?? [];
  const indexed = stats?.document_count ?? null;

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Workspace</p>
          <h1 className={styles.title}>Search</h1>
          <p className={styles.subtitle}>
            One index across challenges, teams, members and your own notes.
          </p>
        </div>
        <div className={styles.actions}>
          <span className={styles.indexBadge} aria-live="polite">
            <DatabaseZap size={14} aria-hidden="true" />
            {indexed === null ? "Index loading" : `${indexed} indexed`}
          </span>
          <Button
            variant="secondary"
            size="sm"
            loading={rebuilding}
            onClick={rebuildIndex}
          >
            Rebuild index
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setPaletteOpen(true)}
          >
            <CommandIcon size={15} aria-hidden="true" />
            Commands
            <kbd className={styles.hotkey}>⌘/Ctrl K</kbd>
          </Button>
        </div>
      </header>

      {notice ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}

      <Card className={styles.workspace}>
        <form
          className={styles.searchForm}
          onSubmit={handleSubmit}
          role="search"
        >
          <Search size={18} aria-hidden="true" className={styles.searchIcon} />
          <input
            ref={inputRef}
            className={styles.input}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search everything — try kind:challenge tag:web"
            aria-label="Search dashboard"
            autoComplete="off"
          />
          {feed.loading ? (
            <Spinner size={16} label="Searching" />
          ) : (
            <button type="submit" className={styles.submit}>
              Search
            </button>
          )}
        </form>

        <SearchFilters
          kinds={kinds}
          onToggle={toggleKind}
          onClear={() => {
            setKinds([]);
            setTags([]);
          }}
          limit={limit}
          onLimitChange={setLimit}
          stats={stats}
        />

        {parsed.kinds.length > 0 || parsed.tags.length > 0 ? (
          <p className={styles.inlineFilters}>
            Inline filters:
            {parsed.kinds.map((kind) => (
              <code key={`k-${kind}`}>kind:{kind}</code>
            ))}
            {parsed.tags.map((tag) => (
              <code key={`t-${tag}`}>tag:{tag}</code>
            ))}
          </p>
        ) : null}

        {recent.queries.length > 0 ? (
          <div className={styles.recent} aria-label="Recent queries">
            <span>Recent</span>
            {recent.queries.map((item) => (
              <button
                type="button"
                className={styles.chip}
                key={item}
                onClick={() => applyRecent(item)}
              >
                {item}
              </button>
            ))}
            <button
              type="button"
              className={styles.clearRecent}
              onClick={recent.clear}
            >
              Clear
            </button>
          </div>
        ) : null}
      </Card>

      <section className={styles.results} aria-label="Search results">
        <div className={styles.resultsHead}>
          <h2>
            {feed.results?.returned ?? 0} results
            {feed.results ? ` of ${feed.results.total_indexed} indexed` : ""}
          </h2>
          {feed.results?.query.limit ? (
            <span>Limit {feed.results.query.limit}</span>
          ) : null}
        </div>
        <SearchResults
          results={results}
          query={query}
          loading={feed.loading}
          error={feed.error}
          onRetry={feed.refresh}
          onOpen={openResult}
        />
      </section>

      <CommandPalette
        open={paletteOpen}
        commands={commandsFeed.commands}
        onClose={() => setPaletteOpen(false)}
        onExecute={executeCommand}
      />
    </main>
  );
}
