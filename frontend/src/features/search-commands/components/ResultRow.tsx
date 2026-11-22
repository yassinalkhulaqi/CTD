/** A single ranked search result. */

import {
  FileCode2,
  Users,
  UserRound,
  FileText,
  ArrowUpRight,
} from "lucide-react";
import { scoreLabel } from "../searchUtils";
import { kindLabel, type SearchResult } from "../types";
import { Highlight } from "./Highlight";
import styles from "./ResultRow.module.css";

/** Props accepted by {@link ResultRow}. */
export interface ResultRowProps {
  /** The result to display. */
  result: SearchResult;
  /** The raw query used to highlight matches. */
  query: string;
  /** Invoked when the user activates the result. */
  onOpen?: (result: SearchResult) => void;
}

/**
 * Return the icon associated with a result kind.
 *
 * @param kind - The document kind.
 * @returns The icon element.
 */
function kindIcon(kind: SearchResult["kind"]) {
  switch (kind) {
    case "challenge":
      return <FileCode2 size={16} aria-hidden="true" />;
    case "team":
      return <Users size={16} aria-hidden="true" />;
    case "member":
      return <UserRound size={16} aria-hidden="true" />;
    default:
      return <FileText size={16} aria-hidden="true" />;
  }
}

/**
 * Render a search result as a keyboard operable row.
 *
 * @param props - The component props.
 * @returns The result row element.
 */
export function ResultRow({ result, query, onOpen }: ResultRowProps) {
  return (
    <li className={styles.item}>
      <button
        type="button"
        className={styles.row}
        onClick={() => onOpen?.(result)}
        data-result-id={result.document_id}
      >
        <span className={styles.icon} data-kind={result.kind}>
          {kindIcon(result.kind)}
        </span>
        <span className={styles.content}>
          <span className={styles.top}>
            <span className={styles.title}>
              <Highlight text={result.title} query={query} />
            </span>
            <span className={styles.kind}>{kindLabel(result.kind)}</span>
          </span>
          <span className={styles.snippet}>
            <Highlight text={result.snippet} query={query} />
          </span>
          <span className={styles.meta}>
            <code>{result.path}</code>
            <span>
              {result.highlights.length} match
              {result.highlights.length === 1 ? "" : "es"}
            </span>
          </span>
        </span>
        <span className={styles.score} title={`Score ${result.score}`}>
          {scoreLabel(result.score)}
          <strong>{result.score.toFixed(1)}</strong>
        </span>
        <ArrowUpRight className={styles.arrow} size={16} aria-hidden="true" />
      </button>
    </li>
  );
}
