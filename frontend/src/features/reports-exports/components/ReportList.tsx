import { FileClock, FileText } from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../../components/ui";
import { FORMAT_LABELS, formatBytes, formatDate } from "../reportModel";
import type { ExportJob, Report } from "../types";
import styles from "./ReportList.module.css";

export interface ReportListProps {
  reports: Report[];
  selectedId: string | null;
  exports?: ExportJob[];
  onSelect: (report: Report) => void;
  loading?: boolean;
}

export function ReportList({
  reports,
  selectedId,
  exports = [],
  onSelect,
  loading = false,
}: ReportListProps) {
  return (
    <Card
      as="section"
      aria-labelledby="report-list-title"
      className={styles.card}
    >
      <CardHeader
        actions={
          <Badge tone="neutral" outline>
            {reports.length}
          </Badge>
        }
      >
        <CardTitle id="report-list-title" level={3}>
          Saved reports
        </CardTitle>
      </CardHeader>
      <CardContent className={styles.content}>
        {loading ? (
          <Skeleton lines={4} />
        ) : reports.length === 0 ? (
          <EmptyState
            icon={<FileText size={20} />}
            title="No reports yet"
            description="Create a draft from a template and it will appear here."
          />
        ) : (
          <Table aria-label="Saved reports">
            <TableHead>
              <tr>
                <TableHeaderCell>Report</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell>Scope</TableHeaderCell>
                <TableHeaderCell>Created</TableHeaderCell>
              </tr>
            </TableHead>
            <TableBody>
              {reports.map((report) => (
                <TableRow
                  key={report.id}
                  selected={report.id === selectedId}
                  onActivate={() => onSelect(report)}
                  aria-label={`Open report ${report.title}`}
                  tabIndex={0}
                >
                  <TableCell>
                    <span className={styles.title}>{report.title}</span>
                    <span className={styles.id}>{report.id}</span>
                  </TableCell>
                  <TableCell>
                    <Badge tone={report.is_final ? "success" : "warning"} dot>
                      {report.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{report.scope_id}</TableCell>
                  <TableCell className={styles.date}>
                    {formatDate(report.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {exports.length > 0 ? (
          <div className={styles.exports}>
            <p className={styles.exportsTitle}>
              <FileClock size={13} aria-hidden="true" /> Recent exports
            </p>
            <ul>
              {exports.slice(0, 4).map((job) => (
                <li key={job.id}>
                  <Badge tone="info" outline>
                    {FORMAT_LABELS[job.format]}
                  </Badge>
                  <span className={styles.exportReport}>{job.report_id}</span>
                  <span className={styles.exportSize}>
                    {formatBytes(job.byte_size)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
