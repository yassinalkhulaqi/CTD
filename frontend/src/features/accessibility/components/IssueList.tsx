import { useState } from "react";
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
  Input,
  Switch,
} from "../../../components/ui";
import { filterIssues, severityTone } from "../a11y";
import { useIssueFilters } from "../hooks";
import { SEVERITY_OPTIONS, type A11yIssue } from "../types";
import styles from "./IssueList.module.css";

export interface IssueListProps {
  issues: A11yIssue[];
  onResolve: (issueId: string) => Promise<A11yIssue>;
  onReload?: () => void;
  loading?: boolean;
}

export function IssueList({
  issues,
  onResolve,
  onReload,
  loading = false,
}: IssueListProps) {
  const { filters, setSeverity, setQuery, toggleResolved, reset } =
    useIssueFilters();
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const visible = filterIssues(issues, filters);
  const openCount = issues.filter((issue) => !issue.is_resolved).length;

  async function resolve(issueId: string): Promise<void> {
    setResolvingId(issueId);
    setError(null);
    try {
      await onResolve(issueId);
      onReload?.();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to resolve issue",
      );
    } finally {
      setResolvingId(null);
    }
  }

  return (
    <Card as="section" className={styles.card} aria-labelledby="issues-title">
      <CardHeader
        actions={
          <Badge tone={openCount > 0 ? "warning" : "success"}>
            {openCount} open
          </Badge>
        }
      >
        <CardTitle id="issues-title">Issue list</CardTitle>
        <CardDescription>
          Filter by severity, then resolve items as the interface is corrected.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className={styles.controls}>
          <ButtonGroup
            className={styles.filters}
            aria-label="Filter by severity"
          >
            {SEVERITY_OPTIONS.map((option) => (
              <Button
                key={option.value}
                size="sm"
                variant={
                  filters.severity === option.value ? "primary" : "subtle"
                }
                aria-pressed={filters.severity === option.value}
                onClick={() => setSeverity(option.value)}
              >
                {option.label}
              </Button>
            ))}
          </ButtonGroup>
          <Input
            label="Search issues"
            hideLabel
            placeholder="Search description or rule"
            value={filters.query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <Switch checked={filters.includeResolved} onChange={toggleResolved}>
            Show resolved
          </Switch>
          <Button size="sm" variant="ghost" onClick={reset}>
            Reset
          </Button>
        </div>

        {error ? (
          <p className={styles.error} role="alert">
            {error}
          </p>
        ) : null}

        {loading ? (
          <div className={styles.loading} role="status">
            Loading accessibility issues…
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            title="No matching issues"
            description="Adjust the filters or run another audit to populate this list."
          />
        ) : (
          <ul className={styles.list}>
            {visible.map((issue) => (
              <li className={styles.item} key={issue.id}>
                <div className={styles.itemHeader}>
                  <Badge tone={severityTone(issue.severity)} dot>
                    {issue.severity}
                  </Badge>
                  <code className={styles.rule}>{issue.rule_id}</code>
                  <span className={styles.path}>{issue.path}</span>
                </div>
                <p className={styles.description}>{issue.description}</p>
                {issue.suggestion ? (
                  <p className={styles.suggestion}>{issue.suggestion}</p>
                ) : null}
                <div className={styles.itemFooter}>
                  <time dateTime={issue.detected_at}>
                    {new Date(issue.detected_at).toLocaleDateString()}
                  </time>
                  {issue.is_resolved ? (
                    <Badge tone="success">Resolved</Badge>
                  ) : (
                    <Button
                      size="sm"
                      variant="secondary"
                      loading={resolvingId === issue.id}
                      onClick={() => void resolve(issue.id)}
                    >
                      Resolve
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
