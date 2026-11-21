import { useMemo, useState } from "react";
import {
  ArrowDownToLine,
  FileBarChart2,
  FileText,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ErrorState,
  StatCard,
} from "../../components/ui";
import { reportsApi } from "./api";
import { ExportMenu } from "./components/ExportMenu";
import { ReportBuilder } from "./components/ReportBuilder";
import { ReportList } from "./components/ReportList";
import { ReportPreview } from "./components/ReportPreview";
import { TemplatePicker } from "./components/TemplatePicker";
import { useReportCatalog, useReportDraft } from "./hooks";
import {
  FORMAT_LABELS,
  buildCreatePayload,
  buildLocalPreview,
  statsSentence,
} from "./reportModel";
import type { ExportJob, Report, ReportFormat, ReportTemplate } from "./types";
import printStyles from "./ReportsPage.print.module.css";
import styles from "./ReportsPage.module.css";

const SAMPLE_SNAPSHOT: Record<string, unknown> = {
  event: "Regional CTF",
  score: 1240,
  rank: 3,
  challenges: [
    { title: "Warmup", points: 100, category: "intro" },
    { title: "Pipeline", points: 250, category: "web" },
    { title: "Cipher", points: 400, category: "crypto" },
  ],
  members: ["Ada", "Lin", "Kai", "Mira"],
  metrics: { solved: 18, attempts: 24, accuracy: 75 },
};

interface Notice {
  tone: "success" | "error";
  text: string;
}

export function ReportsPage() {
  const catalog = useReportCatalog();
  const builder = useReportDraft(catalog.templates);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [format, setFormat] = useState<ReportFormat>("markdown");
  const [busy, setBusy] = useState(false);
  const [lastExport, setLastExport] = useState<ExportJob | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  const snapshot = useMemo<Record<string, unknown>>(
    () => ({
      ...SAMPLE_SNAPSHOT,
      team: selectedReport?.scope_id || builder.draft.scopeId || "team",
      ...(selectedReport?.data ?? {}),
    }),
    [selectedReport, builder.draft.scopeId],
  );

  const preview = useMemo(
    () => buildLocalPreview(builder.draft, snapshot, format),
    [builder.draft, snapshot, format],
  );

  function showError(caught: unknown, fallback: string): void {
    setNotice({
      tone: "error",
      text: caught instanceof Error ? caught.message : fallback,
    });
  }

  async function handleCreate(): Promise<void> {
    if (Object.keys(builder.errors).length > 0) {
      setNotice({
        tone: "error",
        text: "Fix the highlighted fields before creating a report.",
      });
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      const created = await reportsApi.createReport(
        buildCreatePayload(builder.draft, snapshot),
      );
      setSelectedReport(created);
      setNotice({
        tone: "success",
        text: `Draft ${created.id} created with a captured snapshot.`,
      });
      await catalog.refresh();
    } catch (caught) {
      showError(caught, "Unable to create the report");
    } finally {
      setBusy(false);
    }
  }

  async function handleFinalise(): Promise<void> {
    if (!selectedReport) return;
    setBusy(true);
    setNotice(null);
    try {
      const finalised = await reportsApi.finalise(selectedReport.id);
      setSelectedReport(finalised);
      setNotice({
        tone: "success",
        text: `${finalised.title} is final and ready to export.`,
      });
      await catalog.refresh();
    } catch (caught) {
      showError(caught, "Unable to finalise the report");
    } finally {
      setBusy(false);
    }
  }

  async function handleExport(nextFormat: ReportFormat): Promise<void> {
    if (!selectedReport) return;
    setFormat(nextFormat);
    setBusy(true);
    setNotice(null);
    try {
      const job = await reportsApi.exportReport(selectedReport.id, nextFormat);
      setLastExport(job);
      setNotice({
        tone: "success",
        text: `${FORMAT_LABELS[job.format]} export ready: ${job.extension.toUpperCase()} · ${job.line_count} lines.`,
      });
      await catalog.refresh();
    } catch (caught) {
      showError(caught, "Unable to export the report");
    } finally {
      setBusy(false);
    }
  }

  function handleSelectTemplate(template: ReportTemplate): void {
    setSelectedReport(null);
    setLastExport(null);
    setNotice(null);
    builder.selectTemplate(template);
  }

  function handleSelectReport(report: Report): void {
    setSelectedReport(report);
    setLastExport(null);
    setNotice(null);
    builder.loadReport(report);
  }

  if (catalog.error) {
    return (
      <div className={styles.page}>
        <ErrorState
          title="Report studio unavailable"
          message={catalog.error}
          onRetry={() => void catalog.refresh()}
        />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={`${styles.header} ${printStyles.printHidden}`}>
        <div className={styles.heading}>
          <span className={styles.icon} aria-hidden="true">
            <FileBarChart2 size={20} />
          </span>
          <div>
            <h1>Report studio</h1>
            <p>
              Compose structured reports from live dashboard data, preview every
              section and export the result.
            </p>
          </div>
        </div>
        <div className={styles.headerActions}>
          {catalog.stats ? (
            <Badge tone="accent" outline>
              {statsSentence(catalog.stats)}
            </Badge>
          ) : null}
          <Button
            variant="ghost"
            size="sm"
            icon={<RefreshCw size={14} />}
            disabled={catalog.loading}
            onClick={() => void catalog.refresh()}
          >
            Refresh
          </Button>
          <ExportMenu
            disabled={!selectedReport?.is_final}
            busy={busy}
            activeFormat={format}
            lastExport={lastExport}
            onExport={(nextFormat) => void handleExport(nextFormat)}
          />
        </div>
      </header>

      {notice ? (
        <div
          className={
            notice.tone === "error" ? styles.noticeError : styles.noticeSuccess
          }
          role={notice.tone === "error" ? "alert" : "status"}
        >
          {notice.tone === "success" ? (
            <Sparkles size={14} />
          ) : (
            <ArrowDownToLine size={14} />
          )}
          {notice.text}
        </div>
      ) : null}

      <section
        className={`${styles.stats} ${printStyles.printHidden}`}
        aria-label="Studio summary"
      >
        <StatCard
          label="Templates"
          value={catalog.stats?.templates ?? 0}
          meta="reusable layouts"
          icon={<FileText size={16} />}
          loading={catalog.loading}
        />
        <StatCard
          label="Reports"
          value={catalog.stats?.reports ?? 0}
          meta={`${catalog.stats?.final_reports ?? 0} finalised`}
          icon={<FileBarChart2 size={16} />}
          loading={catalog.loading}
        />
        <StatCard
          label="Exports"
          value={catalog.stats?.exports ?? 0}
          meta="generated artifacts"
          icon={<ArrowDownToLine size={16} />}
          loading={catalog.loading}
        />
      </section>

      <div className={`${styles.templateBar} ${printStyles.printHidden}`}>
        <TemplatePicker
          templates={catalog.templates}
          selectedId={builder.draft.templateId}
          onSelect={handleSelectTemplate}
          loading={catalog.loading}
          disabled={Boolean(selectedReport?.is_final)}
        />
      </div>

      <div className={styles.workspace}>
        <div className={`${styles.editorColumn} ${printStyles.printHidden}`}>
          <ReportBuilder
            draft={builder.draft}
            errors={builder.errors}
            selectedReport={selectedReport}
            busy={busy}
            onTitleChange={builder.setTitle}
            onScopeChange={builder.setScope}
            onAddSection={builder.addSection}
            onPatchSection={builder.patchSection}
            onToggleSection={builder.toggle}
            onMoveSection={builder.move}
            onRemoveSection={builder.remove}
            onCreate={() => void handleCreate()}
            onFinalise={() => void handleFinalise()}
          />
        </div>
        <div className={styles.previewColumn}>
          <ReportPreview
            preview={preview}
            title={builder.draft.title || undefined}
            format={format}
            onFormatChange={setFormat}
          />
          <div className={printStyles.printHidden}>
            <ReportList
              reports={catalog.reports}
              exports={catalog.exports}
              selectedId={selectedReport?.id ?? null}
              onSelect={handleSelectReport}
              loading={catalog.loading}
            />
          </div>
        </div>
      </div>

      <Card className={styles.footerCard}>
        <CardHeader>
          <CardTitle level={3}>Rendering notes</CardTitle>
        </CardHeader>
        <CardContent className={styles.footerContent}>
          <p>
            Placeholders use <code>{"{{ key || fallback }}"}</code> syntax.
            Table sections read a list of records from the named snapshot key;
            list and metrics sections accept lists and mappings. Finalise a
            report to unlock exports.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
