/** Routed visualisation gallery with chart switching and table fallback. */

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import {
  Badge,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../components/ui";
import { BarChart } from "./components/BarChart";
import { ChartCard } from "./components/ChartCard";
import { LineChart } from "./components/LineChart";
import { RadarChart } from "./components/RadarChart";
import { SankeyDiagram } from "./components/SankeyDiagram";
import { Sparkline } from "./components/Sparkline";
import { formatValue } from "./geometry";
import { useInterfaceTheme, useVisualizations } from "./hooks";
import { CHART_TYPE_OPTIONS, samplePoints } from "./samples";
import type { ChartGeometry, ChartType } from "./types";
import styles from "./VisualizationsPage.module.css";

function renderChart(geometry: ChartGeometry) {
  switch (geometry.chart_type) {
    case "bar":
      return <BarChart geometry={geometry} />;
    case "line":
      return <LineChart geometry={geometry} />;
    case "radar":
      return <RadarChart geometry={geometry} />;
    case "sankey":
      return <SankeyDiagram geometry={geometry} />;
    case "sparkline":
      return <Sparkline geometry={geometry} />;
  }
}

function DataTable({ geometry }: { geometry: ChartGeometry }) {
  if (geometry.data.length === 0) {
    return (
      <EmptyState
        title="No observations yet"
        description="Ingest sample data to populate the table."
      />
    );
  }
  return (
    <Table aria-label="Chart source data">
      <TableHead>
        <TableRow>
          <TableHeaderCell>Label</TableHeaderCell>
          <TableHeaderCell>Series</TableHeaderCell>
          <TableHeaderCell>Category</TableHeaderCell>
          <TableHeaderCell align="right">Value</TableHeaderCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {geometry.data.map((datum, index) => (
          <TableRow key={`${datum.series}-${datum.label}-${index}`}>
            <TableCell>
              <span
                className={styles.aggregateSwatch}
                style={{ background: datum.color }}
                aria-hidden="true"
              />
              {datum.label}
            </TableCell>
            <TableCell>{datum.series}</TableCell>
            <TableCell>{datum.category}</TableCell>
            <TableCell align="right">{formatValue(datum.value)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/** Page component mounted at `/visualizations`. */
export function VisualizationsPage() {
  const theme = useInterfaceTheme();
  const view = useVisualizations(theme);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const handleRefresh = () => {
    setActionError(null);
    setNotice(null);
    void view.refresh();
  };

  const handleCreateSamples = async (): Promise<void> => {
    setActionError(null);
    setNotice(null);
    try {
      await view.createSamples();
      setNotice("Sample gallery created.");
    } catch (cause) {
      setActionError(
        cause instanceof Error ? cause.message : "Could not create samples",
      );
    }
  };

  const handleTypeChange = async (chartType: ChartType): Promise<void> => {
    if (!view.selected) return;
    setActionError(null);
    setNotice(null);
    try {
      await view.update(view.selected.id, { chart_type: chartType });
      setNotice(`Switched to ${chartType} chart.`);
    } catch (cause) {
      setActionError(
        cause instanceof Error ? cause.message : "Could not switch chart type",
      );
    }
  };

  const handleIngest = async (): Promise<void> => {
    if (!view.selected) return;
    setActionError(null);
    setNotice(null);
    try {
      await view.ingest(
        view.selected.id,
        samplePoints(view.selected.chart_type),
      );
      setNotice("Sample observations ingested.");
    } catch (cause) {
      setActionError(
        cause instanceof Error ? cause.message : "Could not ingest data",
      );
    }
  };

  const error = actionError ?? view.error;
  const geometry = view.geometry;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Analysis</p>
          <h1 className={styles.title}>Visualizations</h1>
          <p className={styles.subtitle}>
            Explore team performance with responsive charts, normalised flows
            and an accessible data table fallback.
          </p>
        </div>
        <div className={styles.headerActions}>
          <Badge tone="accent" dot>
            {view.specs.length} charts
          </Badge>
          <Button
            icon={<RefreshCw size={15} />}
            variant="secondary"
            onClick={handleRefresh}
          >
            Refresh
          </Button>
        </div>
      </header>

      {error ? (
        <ErrorState
          title="Visualisations unavailable"
          message={error}
          onRetry={handleRefresh}
          retryLabel="Retry"
        />
      ) : null}
      {notice ? (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      ) : null}

      {view.loading ? (
        <div className={styles.loading} role="status">
          <Spinner label="Loading visualisations" />
          <span>Loading charts…</span>
        </div>
      ) : view.specs.length === 0 ? (
        <Card className={styles.emptyCard}>
          <CardContent>
            <EmptyState
              title="No charts yet"
              description="Create a gallery of sample visualisations to explore the available renderers."
              action={
                <Button onClick={() => void handleCreateSamples()}>
                  Create sample gallery
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className={styles.layout}>
          <aside className={styles.gallery} aria-label="Chart gallery">
            <h2 className={styles.galleryTitle}>Gallery</h2>
            <div className={styles.galleryList}>
              {view.specs.map((spec) => (
                <ChartCard
                  key={spec.id}
                  spec={spec}
                  selected={spec.id === view.selected?.id}
                  onSelect={view.select}
                />
              ))}
            </div>
          </aside>

          <section className={styles.detail} aria-label="Chart detail">
            <Card>
              <CardHeader className={styles.detailHeader}>
                <div>
                  <CardTitle>
                    {view.selected?.title ?? "Select a chart"}
                  </CardTitle>
                  <CardDescription>
                    {geometry
                      ? `${geometry.mark_count} marks · ${geometry.scale} scale · ${geometry.theme} palette`
                      : "Computing geometry…"}
                  </CardDescription>
                </div>
                <ButtonGroup
                  className={styles.switcher}
                  role="group"
                  aria-label="Chart type switcher"
                >
                  {CHART_TYPE_OPTIONS.map((option) => (
                    <Button
                      key={option.value}
                      size="sm"
                      variant={
                        view.selected?.chart_type === option.value
                          ? "primary"
                          : "ghost"
                      }
                      aria-pressed={view.selected?.chart_type === option.value}
                      title={option.hint}
                      onClick={() => void handleTypeChange(option.value)}
                    >
                      {option.label}
                    </Button>
                  ))}
                </ButtonGroup>
              </CardHeader>
              <CardContent>
                <div className={styles.toolbar}>
                  <div className={styles.toolbarGroup}>
                    <ButtonGroup attached aria-label="View mode">
                      <Button
                        size="sm"
                        variant={
                          view.viewMode === "chart" ? "primary" : "ghost"
                        }
                        aria-pressed={view.viewMode === "chart"}
                        onClick={() => view.setViewMode("chart")}
                      >
                        Chart view
                      </Button>
                      <Button
                        size="sm"
                        variant={
                          view.viewMode === "table" ? "primary" : "ghost"
                        }
                        aria-pressed={view.viewMode === "table"}
                        onClick={() => view.setViewMode("table")}
                      >
                        Table view
                      </Button>
                    </ButtonGroup>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => void handleIngest()}
                    >
                      Add sample data
                    </Button>
                  </div>
                  <Badge outline>{view.selected?.palette ?? "aurora"}</Badge>
                </div>

                {view.analysisLoading || !geometry ? (
                  <div className={styles.loading} role="status">
                    <Spinner label="Computing chart geometry" />
                    <span>Computing geometry…</span>
                  </div>
                ) : (
                  <div className={styles.chartArea}>
                    {view.viewMode === "table" ? (
                      <DataTable geometry={geometry} />
                    ) : (
                      (renderChart(geometry) ?? (
                        <EmptyState title="Unsupported chart type" />
                      ))
                    )}
                  </div>
                )}

                {view.aggregate && view.viewMode === "chart" ? (
                  <div
                    className={styles.aggregate}
                    aria-label="Category aggregation"
                  >
                    {view.aggregate.rows.slice(0, 6).map((row) => (
                      <div className={styles.aggregateItem} key={row.category}>
                        <span className={styles.aggregateCategory}>
                          <span
                            className={styles.aggregateSwatch}
                            style={{ background: row.color }}
                            aria-hidden="true"
                          />
                          {row.category}
                        </span>
                        <span className={styles.aggregateValue}>
                          {row.display}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </section>
        </div>
      )}
    </div>
  );
}
