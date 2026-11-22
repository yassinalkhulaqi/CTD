import { useState } from "react";
import { Button, Input, Kbd } from "../../../components/ui";
import styles from "./SkipLinkDemo.module.css";

export interface SkipLinkDemoProps {
  targetId?: string;
}

export function SkipLinkDemo({
  targetId = "a11y-main-content",
}: SkipLinkDemoProps) {
  const [activated, setActivated] = useState(false);

  function moveFocus(): void {
    const target = document.getElementById(targetId);
    target?.focus();
    setActivated(true);
  }

  return (
    <div className={styles.wrapper}>
      <a
        className={styles.skipLink}
        href={`#${targetId}`}
        onClick={() => setActivated(true)}
      >
        Skip to main content
      </a>
      <div className={styles.demo}>
        <div className={styles.intro}>
          <span className={styles.eyebrow}>Skip link demo</span>
          <p>
            Press Tab from the top of the page to reveal the skip link, then use
            Enter to jump past this toolbar.
          </p>
        </div>
        <div className={styles.controls}>
          <Input label="Demo search" hideLabel placeholder="Tab stop one" />
          <Button variant="secondary" size="sm" onClick={moveFocus}>
            Move focus to main
          </Button>
          <Kbd>Tab</Kbd>
        </div>
        <p className={styles.status} role="status" aria-live="polite">
          {activated
            ? "Focus moved to the main accessibility content."
            : "Waiting for skip link activation."}
        </p>
      </div>
    </div>
  );
}
