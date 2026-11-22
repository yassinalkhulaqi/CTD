import type { ReactNode } from "react";
import {
  FilePlus2,
  ListPlus,
  Lock,
  Plus,
  Save,
  Table2,
  Type,
  BarChart3,
} from "lucide-react";
import {
  Badge,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
  Input,
} from "../../../components/ui";
import type { DraftErrors, Report, ReportDraft, SectionKind } from "../types";
import { SectionEditor, type SectionEditorProps } from "./SectionEditor";
import styles from "./ReportBuilder.module.css";

export interface ReportBuilderProps {
  draft: ReportDraft;
  errors: DraftErrors;
  selectedReport: Report | null;
  busy?: boolean;
  onTitleChange: (title: string) => void;
  onScopeChange: (scopeId: string) => void;
  onAddSection: (kind: SectionKind) => void;
  onPatchSection: SectionEditorProps["onPatch"];
  onToggleSection: (id: string) => void;
  onMoveSection: (id: string, direction: -1 | 1) => void;
  onRemoveSection: (id: string) => void;
  onCreate: () => void;
  onFinalise: () => void;
}

const ADD_ACTIONS: Array<{
  kind: SectionKind;
  label: string;
  icon: ReactNode;
}> = [
  { kind: "text", label: "Text", icon: <Type size={14} /> },
  { kind: "table", label: "Table", icon: <Table2 size={14} /> },
  { kind: "list", label: "List", icon: <ListPlus size={14} /> },
  { kind: "metrics", label: "Metrics", icon: <BarChart3 size={14} /> },
];

export function ReportBuilder({
  draft,
  errors,
  selectedReport,
  busy = false,
  onTitleChange,
  onScopeChange,
  onAddSection,
  onPatchSection,
  onToggleSection,
  onMoveSection,
  onRemoveSection,
  onCreate,
  onFinalise,
}: ReportBuilderProps) {
  const hasTemplate = draft.templateId.length > 0;
  const isFinal = selectedReport?.is_final ?? false;

  return (
    <Card as="section" aria-labelledby="report-builder-title">
      <CardHeader
        actions={
          selectedReport ? (
            <Badge tone={isFinal ? "success" : "warning"} dot>
              {isFinal ? "Final" : "Draft"}
            </Badge>
          ) : (
            <Badge tone="neutral" outline>
              Unsaved
            </Badge>
          )
        }
      >
        <CardTitle id="report-builder-title" level={3}>
          Report builder
        </CardTitle>
      </CardHeader>
      <CardContent className={styles.content}>
        <div className={styles.meta}>
          <Input
            label="Report title"
            value={draft.title}
            error={errors.title}
            disabled={!hasTemplate || isFinal}
            placeholder="Quarterly operations report"
            onChange={(event) => onTitleChange(event.target.value)}
          />
          <Input
            label="Scope"
            value={draft.scopeId}
            error={errors.scopeId}
            disabled={!hasTemplate || isFinal}
            placeholder="Team or event identifier"
            onChange={(event) => onScopeChange(event.target.value)}
          />
        </div>
        <div className={styles.sectionsHeader}>
          <span className={styles.sectionsLabel}>Sections</span>
          <ButtonGroup attached aria-label="Add a section">
            {ADD_ACTIONS.map((action) => (
              <Button
                key={action.kind}
                size="sm"
                variant="secondary"
                icon={action.icon}
                disabled={!hasTemplate || busy}
                onClick={() => onAddSection(action.kind)}
              >
                {action.label}
              </Button>
            ))}
          </ButtonGroup>
        </div>
        {errors.sections ? (
          <p className={styles.validation} role="alert">
            {errors.sections}
          </p>
        ) : null}
        <SectionEditor
          sections={draft.sections}
          onToggle={onToggleSection}
          onPatch={onPatchSection}
          onMove={onMoveSection}
          onRemove={onRemoveSection}
          disabled={!hasTemplate || isFinal || busy}
        />
      </CardContent>
      <CardFooter className={styles.footer}>
        <Button
          icon={<FilePlus2 size={15} />}
          disabled={!hasTemplate || busy || isFinal}
          loading={busy}
          loadingLabel="Creating report"
          onClick={onCreate}
        >
          {selectedReport ? "Create another draft" : "Create draft report"}
        </Button>
        <Button
          variant="secondary"
          icon={isFinal ? <Lock size={15} /> : <Save size={15} />}
          disabled={!selectedReport || isFinal || busy}
          onClick={onFinalise}
        >
          {isFinal ? "Finalised" : "Finalise report"}
        </Button>
        {selectedReport ? (
          <span className={styles.reportHint}>
            <Plus size={12} /> Editing report {selectedReport.id}
          </span>
        ) : (
          <span className={styles.reportHint}>
            <Plus size={12} /> Preview refreshes as you edit
          </span>
        )}
      </CardFooter>
    </Card>
  );
}
