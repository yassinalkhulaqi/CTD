/** Peer review timeline and verdict submission form. */

import { useState } from "react";
import {
  CheckCircle2,
  MessageSquare,
  MessageSquareWarning,
} from "lucide-react";
import {
  Avatar,
  Badge,
  Button,
  EmptyState,
  Textarea,
} from "../../../components/ui";
import { cn } from "../../../lib/utils";
import { relativeDate } from "../logic";
import type {
  ReviewPayload,
  ReviewVerdict,
  Writeup,
  WriteupReview,
} from "../types";
import styles from "./ReviewPanel.module.css";

/** Props accepted by {@link ReviewPanel}. */
export interface ReviewPanelProps {
  /** The writeup under review. */
  writeup: Writeup;
  /** Reviews already recorded. */
  reviews: WriteupReview[];
  /** Identifier of the current reviewer. */
  reviewerId: string;
  /** Called when a verdict is submitted. */
  onReview: (payload: ReviewPayload) => void;
  /** Disable the form while a request is in flight. */
  busy?: boolean;
}

/**
 * Render the review timeline and an accessible verdict form.
 *
 * @param props - The component props.
 * @returns The review panel.
 */
export function ReviewPanel({
  writeup,
  reviews,
  reviewerId,
  onReview,
  busy = false,
}: ReviewPanelProps) {
  const [verdict, setVerdict] = useState<ReviewVerdict>("approve");
  const [comment, setComment] = useState("");
  const open = writeup.status === "review";

  const submit = () => {
    if (!open || comment.trim().length < 8) return;
    onReview({ reviewer_id: reviewerId, verdict, comment: comment.trim() });
    setComment("");
  };

  return (
    <section className={styles.panel} aria-label="Peer reviews">
      <div className={styles.header}>
        <h2 className={styles.title}>Peer review</h2>
        <Badge tone={open ? "warning" : "neutral"} outline>
          {reviews.length} review{reviews.length === 1 ? "" : "s"}
        </Badge>
      </div>

      {reviews.length === 0 ? (
        <EmptyState
          icon={<MessageSquare size={18} />}
          title="No reviews yet"
          description={
            open
              ? "Be the first to check the reasoning and leave feedback."
              : "Reviews appear here while the writeup is in the review stage."
          }
        />
      ) : (
        <ul className={styles.timeline}>
          {reviews.map((review) => (
            <li key={review.id} className={styles.review}>
              <Avatar name={review.reviewer_id} size="xs" />
              <div className={styles.reviewBody}>
                <div className={styles.reviewMeta}>
                  <span className={styles.reviewer}>{review.reviewer_id}</span>
                  <Badge tone={review.approved ? "success" : "warning"} dot>
                    {review.approved ? "Approved" : "Changes requested"}
                  </Badge>
                  <span className={styles.date}>
                    {relativeDate(review.created_at)}
                  </span>
                </div>
                {review.comment ? (
                  <p className={styles.comment}>{review.comment}</p>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}

      {open ? (
        <form
          className={styles.form}
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <fieldset className={styles.verdicts}>
            <legend className={styles.legend}>Your verdict</legend>
            <label
              className={cn(
                styles.verdict,
                verdict === "approve" && styles.selected,
              )}
            >
              <input
                type="radio"
                name="verdict"
                value="approve"
                checked={verdict === "approve"}
                onChange={() => setVerdict("approve")}
              />
              <CheckCircle2 size={15} aria-hidden="true" /> Approve
            </label>
            <label
              className={cn(
                styles.verdict,
                verdict === "request_changes" && styles.selected,
              )}
            >
              <input
                type="radio"
                name="verdict"
                value="request_changes"
                checked={verdict === "request_changes"}
                onChange={() => setVerdict("request_changes")}
              />
              <MessageSquareWarning size={15} aria-hidden="true" /> Request
              changes
            </label>
          </fieldset>

          <Textarea
            label="Feedback"
            placeholder="What worked well, and what should be clarified?"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            rows={3}
            maxLength={2000}
            hint="At least 8 characters are required."
          />

          <Button
            type="submit"
            size="sm"
            block
            loading={busy}
            disabled={comment.trim().length < 8}
            icon={<MessageSquare size={14} />}
          >
            Submit review
          </Button>
        </form>
      ) : null}
    </section>
  );
}
