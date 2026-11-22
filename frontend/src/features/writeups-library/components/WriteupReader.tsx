/** Long-form reader with a generated table of contents. */

import { useState, type ReactNode } from "react";
import { BookOpen, Clock3, Eye, List } from "lucide-react";
import { Avatar, Badge } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import {
  categoryLabel,
  formatCount,
  relativeDate,
  splitMarkdownSections,
  statusTone,
} from "../logic";
import type { Writeup } from "../types";
import { BookmarkButton } from "./BookmarkButton";
import { RatingStars } from "./RatingStars";
import styles from "./WriteupReader.module.css";

/** Props accepted by {@link WriteupReader}. */
export interface WriteupReaderProps {
  /** The writeup to render. */
  writeup: Writeup;
  /** The member's current rating. */
  userRating?: number;
  /** Whether the member bookmarked the writeup. */
  bookmarked?: boolean;
  /** Called with a new star rating. */
  onRate?: (score: number) => void;
  /** Called when the bookmark button is pressed. */
  onBookmark?: () => void;
  /** Called to close the reader. */
  onClose?: () => void;
}

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`)/g;

/**
 * Render inline markdown emphasis and code without injecting HTML.
 *
 * @param text - A single line of markdown.
 * @returns A list of React nodes.
 */
function renderInline(text: string): ReactNode[] {
  return text
    .split(INLINE)
    .filter(Boolean)
    .map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code key={index} className={styles.inlineCode}>
            {part.slice(1, -1)}
          </code>
        );
      }
      return <span key={index}>{part}</span>;
    });
}

/**
 * Render one markdown block: code fence, list, quote or paragraph.
 *
 * @param block - The raw block text.
 * @param key - React key.
 * @returns The rendered block.
 */
function renderBlock(block: string, key: string): ReactNode {
  const fenced = /^```(\w*)\n([\s\S]*)$/.exec(block);
  if (fenced) {
    return (
      <pre key={key} className={styles.codeBlock}>
        <code>{fenced[2]}</code>
      </pre>
    );
  }
  if (block.startsWith("> ")) {
    return (
      <blockquote key={key} className={styles.quote}>
        {renderInline(block.replace(/^> ?/gm, ""))}
      </blockquote>
    );
  }
  const lines = block.split("\n");
  if (lines.every((line) => /^\s*[-*]\s+/.test(line))) {
    return (
      <ul key={key} className={styles.list}>
        {lines.map((line, index) => (
          <li key={index}>{renderInline(line.replace(/^\s*[-*]\s+/, ""))}</li>
        ))}
      </ul>
    );
  }
  return (
    <p key={key} className={styles.paragraph}>
      {renderInline(block)}
    </p>
  );
}

/**
 * Render a writeup as an article with a sticky table of contents.
 *
 * @param props - The component props.
 * @returns The reader element.
 */
export function WriteupReader({
  writeup,
  userRating = 0,
  bookmarked = false,
  onRate,
  onBookmark,
  onClose,
}: WriteupReaderProps) {
  const [activeAnchor, setActiveAnchor] = useState("");
  const sections = splitMarkdownSections(writeup.body);
  const toc = writeup.toc;

  return (
    <div className={styles.reader}>
      <nav className={styles.toc} aria-label="Table of contents">
        <p className={styles.tocTitle}>
          <List size={14} aria-hidden="true" /> On this page
        </p>
        <ol className={styles.tocList}>
          {toc.map((entry) => (
            <li
              key={entry.anchor}
              className={cn(styles.tocItem, styles[`level${entry.level}`])}
            >
              <a
                href={`#${entry.anchor}`}
                className={cn(
                  styles.tocLink,
                  activeAnchor === entry.anchor && styles.tocActive,
                )}
                onClick={() => setActiveAnchor(entry.anchor)}
              >
                {entry.title}
              </a>
            </li>
          ))}
        </ol>
        {toc.length === 0 ? (
          <p className={styles.tocEmpty}>No headings in this writeup yet.</p>
        ) : null}
      </nav>

      <article className={styles.article}>
        <header className={styles.header}>
          <div className={styles.headerTop}>
            <Badge tone="accent">{categoryLabel(writeup.category)}</Badge>
            <Badge tone={statusTone(writeup.status)}>{writeup.status}</Badge>
            <Badge tone="neutral" outline>
              {writeup.difficulty}
            </Badge>
            {onClose ? (
              <button
                type="button"
                className={styles.close}
                onClick={onClose}
                aria-label="Close reader"
              >
                ×
              </button>
            ) : null}
          </div>
          <h1 className={styles.title}>{writeup.title}</h1>
          <p className={styles.summary}>{writeup.summary}</p>
          <div className={styles.byline}>
            <Avatar name={writeup.author_id} size="sm" />
            <div className={styles.bylineText}>
              <span className={styles.author}>{writeup.author_id}</span>
              <span className={styles.published}>
                Published{" "}
                {relativeDate(writeup.published_at ?? writeup.created_at)}
              </span>
            </div>
            <span className={styles.reading}>
              <Clock3 size={14} aria-hidden="true" /> {writeup.reading_minutes}{" "}
              min read
            </span>
            <span className={styles.views}>
              <Eye size={14} aria-hidden="true" /> {formatCount(writeup.views)}
            </span>
          </div>
          <div className={styles.actions}>
            <RatingStars
              value={userRating}
              average={writeup.average_rating}
              count={writeup.rating_count}
              onRate={onRate}
            />
            {onBookmark ? (
              <BookmarkButton bookmarked={bookmarked} onToggle={onBookmark} />
            ) : null}
          </div>
        </header>

        <div className={styles.body}>
          {sections.map((section) => (
            <section
              key={section.anchor}
              className={styles.section}
              aria-labelledby={section.anchor}
            >
              {section.anchor !== "introduction" ? (
                <h2 id={section.anchor} className={styles.heading}>
                  {section.title}
                </h2>
              ) : null}
              {section.content
                .split(/\n\s*\n/)
                .map((block, index) =>
                  renderBlock(block, `${section.anchor}-${index}`),
                )}
            </section>
          ))}
        </div>

        <footer className={styles.footer}>
          <BookOpen size={16} aria-hidden="true" />
          <span>
            {writeup.word_count.toLocaleString()} words ·{" "}
            {writeup.reading_minutes} minute read
          </span>
        </footer>
      </article>
    </div>
  );
}
