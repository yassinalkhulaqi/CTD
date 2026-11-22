import { AlertTriangle, Eye, FileSearch } from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  SegmentedControl,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../../components/ui";
import {
  FORMAT_LABELS,
  FORMAT_ORDER,
  excerpt,
  formatDate,
} from "../reportModel";
import type { ReportFormat, ReportPreview, RenderedSection } from "../types";
import printStyles from "../ReportsPage.print.module.css";
import styles from "./ReportPreview.module.css";

export interface ReportPreviewProps {
  preview: ReportPreview | null;
  format: ReportFormat;
  onFormatChange: (format: ReportFormat) => void;
  loading?: boolean;
  title?: string;
}

const FORMAT_OPTIONS = FORMAT_ORDER.map((format) => ({
  value: format,
  label: FORMAT_LABELS[format],
}));

export function ReportPreview({
  preview,
  format,
  onFormatChange,
  loading = false,
  title,
}: ReportPreviewProps) {
  return (
    <Card
      as="section"
      aria-labelledby="report-preview-title"
      className={printStyles.printSurface}
    >
      <CardHeader
        actions={
          <SegmentedControl
            options={FORMAT_OPTIONS}
            value={format}
            onValueChange={onFormatChange}
            label="Preview format"
          />
        }
      >
        <CardTitle id="report-preview-title" level={3}>
          <Eye size={16} aria-hidden="true" /> Live preview
        </CardTitle>
      </CardHeader>
      <CardContent className={styles.content}>
        {loading ? (
          <div className={styles.loading} aria-busy="true" aria-live="polite">
            <Skeleton height={28} width="60%" />
            <Skeleton lines={5} />
          </div>
        ) : !preview ? (
          <EmptyState
            icon={<FileSearch size={20} />}
            title="Nothing to preview yet"
            description="Choose a template and create a report to see the rendered document here."
          />
        ) : (
          <article className={styles.document}>
            <header className={styles.documentHeader}>
              <p className={styles.eyebrow}>
                {FORMAT_LABELS[preview.format]} preview
              </p>
              <h1 className={styles.documentTitle}>{title ?? preview.title}</h1>
              <p className={styles.documentMeta}>
                Generated {formatDate(preview.generated_at)} ·{" "}
                {preview.section_count} sections · {preview.total_rows} rows
              </p>
            </header>
            {Object.keys(preview.summary).length > 0 ? (
              <dl className={styles.summary} aria-label="Summary counts">
                {Object.entries(preview.summary).map(([key, value]) => (
                  <div key={key} className={styles.summaryItem}>
                    <dt>{key}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
            {preview.has_warnings ? (
              <div className={styles.warnings} role="status">
                <AlertTriangle size={14} aria-hidden="true" />
                <span>
                  {preview.warnings.length} placeholder
                  {preview.warnings.length === 1 ? "" : "s"} could not be
                  resolved.
                </span>
                <span className={styles.warningList}>
                  {preview.warnings.map((warning) => (
                    <Badge key={warning} tone="warning" outline>
                      {warning}
                    </Badge>
                  ))}
                </span>
              </div>
            ) : null}
            {preview.is_empty ? (
              <p className={styles.emptyDocument}>
                All sections are empty in this snapshot.
              </p>
            ) : (
              preview.sections.map((section) => (
                <PreviewSection key={section.id} section={section} />
              ))
            )}
          </article>
        )}
      </CardContent>
    </Card>
  );
}

function PreviewSection({ section }: { section: RenderedSection }) {
  return (
    <section
      className={styles.section}
      aria-labelledby={`preview-${section.id}`}
    >
      <h2 id={`preview-${section.id}`}>{section.title}</h2>
      {section.warnings.length > 0 ? (
        <p className={styles.sectionWarning}>
          <AlertTriangle size={12} aria-hidden="true" />
          Missing: {section.warnings.join(", ")}
        </p>
      ) : null}
      {section.kind === "table" ? (
        section.rows.length > 0 ? (
          <Table sticky={false}>
            <TableHead>
              <tr>
                {section.columns.map((column) => (
                  <TableHeaderCell key={column}>{column}</TableHeaderCell>
                ))}
              </tr>
            </TableHead>
            <TableBody>
              {section.rows.map((row, rowIndex) => (
                <TableRow key={rowIndex}>
                  {row.map((cell, cellIndex) => (
                    <TableCell key={cellIndex}>{cell || "—"}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className={styles.placeholder}>
            No rows available for this section.
          </p>
        )
      ) : null}
      {section.kind === "list" ? (
        section.items.length > 0 ? (
          <ul className={styles.list}>
            {section.items.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className={styles.placeholder}>
            No items available for this section.
          </p>
        )
      ) : null}
      {section.kind === "metrics" ? (
        section.metrics.length > 0 ? (
          <dl className={styles.metrics}>
            {section.metrics.map(([label, value]) => (
              <div key={label} className={styles.metric}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className={styles.placeholder}>
            No metrics available for this section.
          </p>
        )
      ) : null}
      {section.kind === "text" ? (
        section.text ? (
          <p className={styles.text}>{excerpt(section.text, 1200)}</p>
        ) : (
          <p className={styles.placeholder}>This section has no body text.</p>
        )
      ) : null}
    </section>
  );
}
