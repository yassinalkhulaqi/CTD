/** Magazine-style card summarising one writeup. */

import type { CSSProperties } from "react";
import { ArrowUpRight, Clock3, Eye, FileText } from "lucide-react";
import { Avatar, Badge } from "../../../components/ui";
import { cn } from "../../../lib/utils";
import { categoryLabel, formatCount, relativeDate, statusTone } from "../logic";
import type { Writeup } from "../types";
import { BookmarkButton } from "./BookmarkButton";
import { RatingStars } from "./RatingStars";
import styles from "./WriteupCard.module.css";

/** Props accepted by {@link WriteupCard}. */
export interface WriteupCardProps {
  /** The writeup being summarised. */
  writeup: Writeup;
  /** Whether the current member bookmarked it. */
  bookmarked?: boolean;
  /** Called when the reader should be opened. */
  onOpen: (writeup: Writeup) => void;
  /** Called when the bookmark button is pressed. */
  onBookmark?: (writeup: Writeup) => void;
  /** Highlight the card as the active selection. */
  active?: boolean;
}

/**
 * Render one writeup tile for the library grid.
 *
 * @param props - The component props.
 * @returns The card element.
 */
export function WriteupCard({
  writeup,
  bookmarked = false,
  onOpen,
  onBookmark,
  active = false,
}: WriteupCardProps) {
  const accent = {
    web: "#38bdf8",
    crypto: "#c084fc",
    pwn: "#fb7185",
    reverse: "#fbbf24",
    forensics: "#34d399",
    osint: "#a3e635",
    misc: "#94a3b8",
  }[writeup.category];

  return (
    <article
      className={cn(styles.card, active && styles.active)}
      style={{ "--card-accent": accent } as CSSProperties}
      aria-labelledby={`title-${writeup.id}`}
    >
      <div className={styles.topline}>
        <Badge tone="accent" outline className={styles.category}>
          {categoryLabel(writeup.category)}
        </Badge>
        <Badge tone={statusTone(writeup.status)} dot className={styles.status}>
          {writeup.status}
        </Badge>
      </div>

      <button
        id={`title-${writeup.id}`}
        type="button"
        className={styles.title}
        onClick={() => onOpen(writeup)}
      >
        {writeup.title}
        <ArrowUpRight size={16} aria-hidden="true" className={styles.arrow} />
      </button>

      <p className={styles.excerpt}>{writeup.excerpt}</p>

      <ul className={styles.tags} aria-label="Tags">
        {writeup.tags.slice(0, 3).map((tag) => (
          <li key={tag} className={styles.tag}>
            #{tag}
          </li>
        ))}
      </ul>

      <div className={styles.ratingRow}>
        <RatingStars
          average={writeup.average_rating}
          count={writeup.rating_count}
          size="sm"
        />
        <span className={styles.score}>
          {writeup.bayesian_score.toFixed(2)}
        </span>
      </div>

      <div className={styles.footer}>
        <div className={styles.author}>
          <Avatar name={writeup.author_id} size="xs" />
          <span className={styles.authorName}>{writeup.author_id}</span>
        </div>
        <div className={styles.meta}>
          <span title="Reading time">
            <Clock3 size={13} aria-hidden="true" /> {writeup.reading_minutes}m
          </span>
          <span title="Views">
            <Eye size={13} aria-hidden="true" /> {formatCount(writeup.views)}
          </span>
          <span title="Word count">
            <FileText size={13} aria-hidden="true" />{" "}
            {formatCount(writeup.word_count)}
          </span>
        </div>
      </div>

      <div className={styles.bottom}>
        <span className={styles.date}>
          {relativeDate(writeup.published_at ?? writeup.created_at)}
        </span>
        {onBookmark ? (
          <BookmarkButton
            bookmarked={bookmarked}
            compact
            onToggle={() => onBookmark(writeup)}
          />
        ) : null}
      </div>
    </article>
  );
}
