import { useRef, useState } from "react";
import { Button } from "../../../components/ui";
import styles from "../PreferencesPage.module.css";

interface Props {
  onExport: () => Promise<string>;
  onImport: (text: string) => Promise<void>;
}

export function ImportExport({ onExport, onImport }: Props) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function handleExport() {
    setBusy(true);
    setMsg("");
    try {
      const json = await onExport();
      const blob = new Blob([json], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "preferences.json";
      a.click();
      URL.revokeObjectURL(url);
      setMsg("Exported preferences.json");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setMsg("");
    try {
      const text = await file.text();
      await onImport(text);
      setMsg("Imported configuration");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div className={styles.importExport}>
      <div className={styles.importExportActions}>
        <Button
          variant="secondary"
          onClick={() => void handleExport()}
          disabled={busy}
        >
          Export JSON
        </Button>
        <Button
          variant="secondary"
          onClick={() => fileRef.current?.click()}
          disabled={busy}
        >
          Import JSON
        </Button>
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          className={styles.hiddenInput}
          onChange={(e) => void handleFile(e.target.files?.[0])}
          aria-label="Import preferences JSON"
        />
      </div>
      {msg ? (
        <p className={styles.importMsg} role="status">
          {msg}
        </p>
      ) : null}
    </div>
  );
}
