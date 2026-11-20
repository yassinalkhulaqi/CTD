/** Live preview of a layout under the selected writing direction. */

import { ArrowLeftRight, ArrowRight } from "lucide-react";
import { Badge } from "../../../components/ui";
import { DirectionBadge } from "./DirectionBadge";
import styles from "./LocalePreview.module.css";
import type { Locale } from "../types";

/** Props accepted by {@link LocalePreview}. */
export interface LocalePreviewProps {
  /** The locale to preview, or `null` for an empty state. */
  locale: Locale | null;
  /** Optional translated sample string. */
  translatedSample?: string;
}

const DEFAULT_SAMPLE = "Capture the flag, solve the puzzle, share the writeup.";

/**
 * Render a sample interface with the locale's direction applied.
 *
 * @param props - The preview props.
 * @returns The preview element.
 */
export function LocalePreview({
  locale,
  translatedSample,
}: LocalePreviewProps) {
  const direction = locale?.direction ?? "ltr";
  const code = locale?.code ?? "en";
  const text = translatedSample ?? DEFAULT_SAMPLE;

  return (
    <div className={styles.preview} data-direction={direction}>
      <div className={styles.header}>
        <div className={styles.headingGroup}>
          <ArrowLeftRight size={16} aria-hidden="true" />
          <h3 className={styles.heading}>Layout preview</h3>
        </div>
        <DirectionBadge direction={direction} code={code} />
      </div>
      <div className={styles.canvas} dir={direction} lang={code}>
        <div className={styles.toolbar}>
          <span className={styles.brand}>CTF Dashboard</span>
          <span className={styles.spacer} />
          <span className={styles.avatar} aria-hidden="true">
            AD
          </span>
        </div>
        <div className={styles.body}>
          <p className={styles.label}>Challenge brief</p>
          <p className={styles.text}>{text}</p>
          <div className={styles.actions}>
            <span className={styles.primary}>
              {direction === "rtl" ? "إرسال" : "Submit"}
            </span>
            <span className={styles.secondary}>
              {direction === "rtl" ? "إلغاء" : "Cancel"}
            </span>
          </div>
        </div>
      </div>
      <p className={styles.note}>
        <ArrowRight size={13} aria-hidden="true" />
        The preview mirrors alignment, ordering and reading flow for {code}.
      </p>
      {locale ? (
        <div className={styles.meta}>
          <Badge tone="neutral">{locale.plural_rules}</Badge>
          <Badge tone="neutral">{locale.canonical_code}</Badge>
        </div>
      ) : null}
    </div>
  );
}
