import { Button } from "../../../components/ui";
import type { SaveState } from "../types";
import styles from "../PreferencesPage.module.css";

interface Props {
  dirty: boolean;
  saveState: SaveState;
  onSave: () => Promise<void>;
  onReset: () => Promise<void>;
}

export function SaveBar({ dirty, saveState, onSave, onReset }: Props) {
  if (!dirty && saveState.status === "idle") return null;
  return (
    <div className={styles.saveBar} role="status" aria-live="polite">
      <span className={styles.saveMsg}>
        {saveState.status === "saving"
          ? "Saving..."
          : saveState.status === "error"
            ? saveState.message
            : dirty
              ? "Unsaved changes"
              : saveState.message}
      </span>
      <div className={styles.saveActions}>
        <Button
          variant="ghost"
          onClick={() => void onReset()}
          disabled={saveState.status === "saving"}
        >
          Reset
        </Button>
        <Button
          variant="primary"
          onClick={() => void onSave()}
          disabled={!dirty || saveState.status === "saving"}
        >
          Save changes
        </Button>
      </div>
    </div>
  );
}
