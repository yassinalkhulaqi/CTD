/**
 * Typed API adapter for the report studio.
 */

import { buildQuery, get, patch, post } from "../../api/client";
import type {
  ExportJob,
  Report,
  ReportFormat,
  ReportPreview,
  ReportStats,
  ReportStatus,
  ReportTemplate,
  SectionConfig,
} from "./types";

/** Request options shared by every adapter method. */
interface CallOptions {
  signal?: AbortSignal;
}

/** Payload used to create a template. */
export interface TemplateCreatePayload {
  name: string;
  sections: SectionConfig[];
  format: ReportFormat;
  scope: "team" | "event" | "global";
}

/** Payload used to create a report. */
export interface ReportCreatePayload {
  template_id: string;
  title: string;
  scope_id: string;
  data?: Record<string, unknown>;
}

/**
 * Encode a report identifier for use in a URL.
 *
 * @param id - The identifier.
 * @returns The encoded identifier.
 */
function pathId(id: string): string {
  return encodeURIComponent(id);
}

/** Endpoints of the report studio. */
export const reportsApi = {
  /**
   * List every saved template.
   *
   * @param options - Request options.
   * @returns The templates, newest first.
   */
  listTemplates(options: CallOptions = {}): Promise<ReportTemplate[]> {
    return get<ReportTemplate[]>("/api/reports/templates", options);
  },

  /**
   * Create a template.
   *
   * @param payload - The name, sections, format and scope.
   * @returns The created template.
   */
  createTemplate(payload: TemplateCreatePayload): Promise<ReportTemplate> {
    return post<ReportTemplate>("/api/reports/templates", payload);
  },

  /**
   * List reports with optional filters.
   *
   * @param filters - Status filter and result limit.
   * @param options - Request options.
   * @returns The matching reports.
   */
  listReports(
    filters: { status?: ReportStatus; limit?: number } = {},
    options: CallOptions = {},
  ): Promise<Report[]> {
    return get<Report[]>(
      `/api/reports${buildQuery({ status: filters.status, limit: filters.limit })}`,
      options,
    );
  },

  /**
   * Read one report.
   *
   * @param reportId - The report identifier.
   * @param options - Request options.
   * @returns The report and its data snapshot.
   */
  getReport(reportId: string, options: CallOptions = {}): Promise<Report> {
    return get<Report>(`/api/reports/${pathId(reportId)}`, options);
  },

  /**
   * Create a draft report.
   *
   * @param payload - The template, title, scope and optional snapshot.
   * @returns The created report.
   */
  createReport(payload: ReportCreatePayload): Promise<Report> {
    return post<Report>("/api/reports", payload);
  },

  /**
   * Replace the data snapshot of a draft report.
   *
   * @param reportId - The report identifier.
   * @param data - The new snapshot.
   * @returns The updated report.
   */
  updateSnapshot(
    reportId: string,
    data: Record<string, unknown>,
  ): Promise<Report> {
    return patch<Report>(`/api/reports/${pathId(reportId)}/data`, { data });
  },

  /**
   * Finalise a draft report.
   *
   * @param reportId - The report identifier.
   * @returns The finalised report.
   */
  finalise(reportId: string): Promise<Report> {
    return post<Report>(`/api/reports/${pathId(reportId)}/finalise`);
  },

  /**
   * Render and persist an export.
   *
   * @param reportId - The report identifier.
   * @param format - The requested serialisation format.
   * @returns The created export job.
   */
  exportReport(reportId: string, format: ReportFormat): Promise<ExportJob> {
    return post<ExportJob>(`/api/reports/${pathId(reportId)}/export`, {
      format,
    });
  },

  /**
   * Render a preview without persisting anything.
   *
   * @param reportId - The report identifier.
   * @param format - An optional format override.
   * @param options - Request options.
   * @returns The rendered preview.
   */
  preview(
    reportId: string,
    format?: ReportFormat,
    options: CallOptions = {},
  ): Promise<ReportPreview> {
    const query = buildQuery({ format });
    return get<ReportPreview>(
      `/api/reports/${pathId(reportId)}/preview${query}`,
      options,
    );
  },

  /**
   * List recent export jobs.
   *
   * @param limit - The maximum number of jobs.
   * @param options - Request options.
   * @returns The export jobs, newest first.
   */
  listExports(limit = 100, options: CallOptions = {}): Promise<ExportJob[]> {
    return get<ExportJob[]>(
      `/api/reports/exports${buildQuery({ limit })}`,
      options,
    );
  },

  /**
   * Read the studio counters.
   *
   * @param options - Request options.
   * @returns The aggregate statistics.
   */
  stats(options: CallOptions = {}): Promise<ReportStats> {
    return get<ReportStats>("/api/reports/stats", options);
  },
};
