/** Result list with loading, empty and error states. */

import { SearchX } from "lucide-react";
import { EmptyState, ErrorState, Skeleton } from "../../../components/ui";
import type { SearchResult } from "../types";
import { ResultRow } from "./ResultRow";
import styles from "./SearchResults.module.css";

/** Props accepted by {@link SearchResults}. */
export interface SearchResultsProps {
  /** The results to render. */
  results: SearchResult[];
  /** The raw query used for highlighting. */
  query: string;
  /** Whether a request is in flight. */
  loading: boolean;
  /** The last error message, when any. */
  error: string | null;
  /** Invoked when the user retries a failed request. */
  onRetry: () => void;
  /** Invoked when a result is activated. */
  onOpen: (result: SearchResult) => void;
}

/**
 * Render the results region.
 *
 * @param props - The component props.
 * @returns The results element.
 */
export function SearchResults({
  results,
  query,
  loading,
  error,
  onRetry,
  onOpen,
}: SearchResultsProps) {
  if (error) {
    return (
      <div className={styles.state}>
        <ErrorState
          title="Search is unavailable"
          message={error}
          onRetry={onRetry}
          retryLabel="Try again"
        />
      </div>
    );
  }

  if (loading && results.length === 0) {
    return (
      <ul className={styles.list} aria-busy="true" aria-label="Loading results">
        {[0, 1, 2].map((index) => (
          <li className={styles.placeholder} key={index}>
            <Skeleton width={34} height={34} circle />
            <div className={styles.placeholderLines}>
              <Skeleton lines={2} />
            </div>
          </li>
        ))}
      </ul>
    );
  }

  if (results.length === 0) {
    return (
      <div className={styles.state}>
        <EmptyState
          icon={<SearchX size={22} />}
          title="No matches"
          description={
            query
              ? "Try a shorter query, remove a filter or rebuild the index."
              : "Index dashboard entities to start searching across your workspace."
          }
        />
      </div>
    );
  }

  return (
    <ul className={styles.list} aria-label="Search results" aria-busy={loading}>
      {results.map((result) => (
        <ResultRow
          key={result.document_id}
          result={result}
          query={query}
          onOpen={onOpen}
        />
      ))}
    </ul>
  );
}
