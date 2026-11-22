import { useState } from "react";
import { Check, ChevronDown, Download, FileDown, Loader2 } from "lucide-react";
import {
  Badge,
  Button,
  Menu,
  MenuDivider,
  MenuItem,
  Popover,
} from "../../../components/ui";
import {
  FORMAT_HINTS,
  FORMAT_LABELS,
  FORMAT_ORDER,
  formatBytes,
} from "../reportModel";
import type { ExportJob, ReportFormat } from "../types";
import styles from "./ExportMenu.module.css";

export interface ExportMenuProps {
  onExport: (format: ReportFormat) => void;
  disabled?: boolean;
  busy?: boolean;
  activeFormat?: ReportFormat;
  lastExport?: ExportJob | null;
}

export function ExportMenu({
  onExport,
  disabled = false,
  busy = false,
  activeFormat = "markdown",
  lastExport,
}: ExportMenuProps) {
  const [open, setOpen] = useState(false);

  return (
    <Popover
      open={open}
      onClose={() => setOpen(false)}
      align="end"
      trigger={
        <Button
          variant="secondary"
          icon={
            busy ? (
              <Loader2 size={15} className={styles.spinner} />
            ) : (
              <Download size={15} />
            )
          }
          trailingIcon={<ChevronDown size={14} />}
          disabled={disabled || busy}
          aria-expanded={open}
          onClick={() => setOpen((current) => !current)}
        >
          Export report
        </Button>
      }
    >
      <Menu open={open} width={288} aria-label="Export formats">
        <p className={styles.title}>Choose a format</p>
        {FORMAT_ORDER.map((format) => (
          <MenuItem
            key={format}
            icon={
              format === activeFormat ? (
                <Check size={14} />
              ) : (
                <FileDown size={14} />
              )
            }
            active={format === activeFormat}
            aria-pressed={format === activeFormat}
            onClick={() => {
              onExport(format);
              setOpen(false);
            }}
          >
            <span className={styles.item}>
              <span className={styles.itemLabel}>{FORMAT_LABELS[format]}</span>
              <span className={styles.itemHint}>{FORMAT_HINTS[format]}</span>
            </span>
          </MenuItem>
        ))}
        {lastExport ? (
          <>
            <MenuDivider />
            <div className={styles.lastExport}>
              <span className={styles.lastTitle}>Last export</span>
              <Badge tone="success" outline>
                {FORMAT_LABELS[lastExport.format]}
              </Badge>
              <span className={styles.lastMeta}>
                {formatBytes(lastExport.byte_size)} · {lastExport.line_count}{" "}
                lines
              </span>
            </div>
          </>
        ) : null}
      </Menu>
    </Popover>
  );
}
