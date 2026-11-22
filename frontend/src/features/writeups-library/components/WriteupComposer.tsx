/** Composer with markdown textarea and live preview. */

import { useState, type FormEvent } from "react";
import { Eye, PenLine, Sparkles } from "lucide-react";
import { Button, Input, Select, Textarea } from "../../../components/ui";
import {
  CATEGORIES,
  CATEGORY_LABELS,
  DIFFICULTIES,
  type WriteupCategory,
  type WriteupCreatePayload,
  type WriteupDifficulty,
} from "../types";
import {
  countWords,
  normaliseTags,
  readingTime,
  splitMarkdownSections,
} from "../logic";
import styles from "./WriteupComposer.module.css";

/** Props accepted by {@link WriteupComposer}. */
export interface WriteupComposerProps {
  /** Called with the completed draft payload. */
  onCreate: (payload: WriteupCreatePayload) => void;
  /** Called when the composer is dismissed. */
  onCancel: () => void;
  /** Disable submission while the request is in flight. */
  busy?: boolean;
}

const INITIAL_BODY = `## The idea

Describe the vulnerability and why it matters.

## Step by step

Explain the exploitation with code and reasoning.
`;

/**
 * Render the writeup creation form with a side-by-side live preview.
 *
 * @param props - The component props.
 * @returns The composer element.
 */
export function WriteupComposer({
  onCreate,
  onCancel,
  busy = false,
}: WriteupComposerProps) {
  const [challengeId, setChallengeId] = useState("");
  const [authorId, setAuthorId] = useState("member-1");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [body, setBody] = useState(INITIAL_BODY);
  const [category, setCategory] = useState<WriteupCategory>("crypto");
  const [difficulty, setDifficulty] = useState<WriteupDifficulty>("medium");
  const [tags, setTags] = useState("");

  const words = countWords(body);
  const valid =
    challengeId.trim().length > 0 &&
    title.trim().length >= 3 &&
    summary.trim().length >= 10 &&
    words > 0;
  const sections = splitMarkdownSections(body);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!valid) return;
    onCreate({
      challenge_id: challengeId.trim(),
      author_id: authorId.trim() || "member-1",
      title: title.trim(),
      summary: summary.trim(),
      body: body.trim(),
      category,
      difficulty,
      tags: normaliseTags(tags.split(",")),
    });
  };

  return (
    <section className={styles.composer} aria-label="Write a new writeup">
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>
            <PenLine size={18} aria-hidden="true" /> New writeup
          </h2>
          <p className={styles.subtitle}>
            Document a solved challenge for the team library.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
      </div>

      <form className={styles.layout} onSubmit={submit}>
        <div className={styles.fields}>
          <div className={styles.row}>
            <Input
              label="Challenge ID"
              placeholder="challenge-42"
              value={challengeId}
              onChange={(event) => setChallengeId(event.target.value)}
              required
            />
            <Input
              label="Author"
              value={authorId}
              onChange={(event) => setAuthorId(event.target.value)}
            />
          </div>
          <Input
            label="Title"
            placeholder="A clear, descriptive title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            minLength={3}
            maxLength={160}
            required
          />
          <Textarea
            label="Summary"
            placeholder="One or two sentences that explain the solution."
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
            rows={2}
            maxLength={400}
            required
          />
          <div className={styles.row}>
            <Select
              label="Category"
              value={category}
              onChange={(event) =>
                setCategory(event.target.value as WriteupCategory)
              }
              options={CATEGORIES.map((item) => ({
                value: item,
                label: CATEGORY_LABELS[item],
              }))}
            />
            <Select
              label="Difficulty"
              value={difficulty}
              onChange={(event) =>
                setDifficulty(event.target.value as WriteupDifficulty)
              }
              options={DIFFICULTIES.map((item) => ({
                value: item,
                label: item[0].toUpperCase() + item.slice(1),
              }))}
            />
          </div>
          <Input
            label="Tags"
            placeholder="crypto, aes, nonce-reuse"
            value={tags}
            onChange={(event) => setTags(event.target.value)}
            hint="Comma separated. Duplicates and hashes are removed automatically."
          />
          <Textarea
            label="Body (Markdown)"
            value={body}
            onChange={(event) => setBody(event.target.value)}
            rows={14}
            className={styles.markdownInput}
          />
          <div className={styles.footer}>
            <span className={styles.counter}>
              {words} words · {readingTime(body)} min read
            </span>
            <Button
              type="submit"
              icon={<Sparkles size={15} />}
              disabled={!valid}
              loading={busy}
            >
              Create draft
            </Button>
          </div>
        </div>

        <aside className={styles.preview} aria-label="Live preview">
          <p className={styles.previewLabel}>
            <Eye size={14} aria-hidden="true" /> Live preview
          </p>
          <h3 className={styles.previewTitle}>{title || "Untitled writeup"}</h3>
          <p className={styles.previewSummary}>
            {summary || "The summary appears here as you type."}
          </p>
          {sections.map((section) => (
            <div key={section.anchor} className={styles.previewSection}>
              {section.anchor !== "introduction" ? (
                <h4 className={styles.previewHeading}>{section.title}</h4>
              ) : null}
              {section.content
                .split(/\n\s*\n/)
                .filter(Boolean)
                .map((block, index) => (
                  <p key={index} className={styles.previewParagraph}>
                    {block}
                  </p>
                ))}
            </div>
          ))}
        </aside>
      </form>
    </section>
  );
}
