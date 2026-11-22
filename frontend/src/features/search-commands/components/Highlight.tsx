/** Render text with query matches emphasised. */

import { tokenizeQuery, foldText } from "../searchUtils";
import styles from "./Highlight.module.css";

/** Props accepted by {@link Highlight}. */
export interface HighlightProps {
  /** The text to render. */
  text: string;
  /** The raw query whose tokens should be highlighted. */
  query: string;
  /** Optional class applied to the wrapper. */
  className?: string;
}

/**
 * Split text into plain and highlighted segments.
 *
 * @param text - The source text.
 * @param query - The raw query.
 * @returns An ordered list of segments and their match flag.
 */
export function highlightSegments(
  text: string,
  query: string,
): Array<{ text: string; match: boolean }> {
  const tokens = tokenizeQuery(query);
  if (!tokens.length || !text) return [{ text, match: false }];
  const escaped = tokens.map((token) =>
    token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
  );
  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
  const matches = new Set(tokens);
  return text
    .split(pattern)
    .filter((part) => part.length > 0)
    .map((part) => ({ text: part, match: matches.has(foldText(part)) }));
}

/**
 * Render a string with matched query tokens wrapped in marks.
 *
 * @param props - The component props.
 * @returns The highlighted text element.
 */
export function Highlight({ text, query, className }: HighlightProps) {
  const segments = highlightSegments(text, query);
  return (
    <span className={className}>
      {segments.map((segment, index) =>
        segment.match ? (
          <mark className={styles.mark} key={index} data-highlight="true">
            {segment.text}
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </span>
  );
}
