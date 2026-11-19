/**
 * The routed notes workspace screen.
 */

import { FileText, Pin, Plus, Search } from "lucide-react";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Input,
  Skeleton,
} from "../../components/ui";
import { cn } from "../../lib/utils";
import { NoteEditor } from "./components/NoteEditor";
import { NoteMetaBar } from "./components/NoteMetaBar";
import { NotePreview } from "./components/NotePreview";
import { RevisionTimeline } from "./components/RevisionTimeline";
import { TagFilter } from "./components/TagFilter";
import { TemplatePicker } from "./components/TemplatePicker";
import { useNotesWorkspace } from "./hooks";
import { countWords, readingMinutes } from "./logic";
import styles from "./NotesPage.module.css";

/**
 * Render the notes workspace page.
 *
 * @returns The page element.
 */
export function NotesPage() {
  const workspace = useNotesWorkspace();

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Notes workspace</h1>
          <p className={styles.subtitle}>
            Capture, structure and revisit the details that solve challenges.
          </p>
        </div>
        <div className={styles.headerStats}>
          {workspace.summary ? (
            <>
              <Badge tone="accent">{workspace.summary.total_notes} notes</Badge>
              <Badge tone="info">
                {workspace.summary.total_revisions} revisions
              </Badge>
              <Badge tone="neutral">
                {workspace.summary.total_words} words
              </Badge>
            </>
          ) : null}
          <Button icon={<Plus size={14} />} onClick={() => workspace.newNote()}>
            New note
          </Button>
        </div>
      </header>

      <div className={styles.toolbar}>
        <Input
          label="Search notes"
          hideLabel
          icon={<Search size={14} />}
          placeholder="Search titles, text and tags…"
          value={workspace.query}
          onChange={(event) => workspace.setQuery(event.target.value)}
          className={styles.search}
        />
        <TagFilter
          tags={workspace.availableTags}
          activeTags={workspace.activeTags}
          onToggle={workspace.toggleTag}
          onClear={workspace.clearTags}
        />
      </div>

      {workspace.error ? (
        <ErrorState
          title="The notes workspace could not be loaded"
          message={workspace.error}
          onRetry={workspace.reload}
        />
      ) : null}

      {workspace.loading ? (
        <div className={styles.loading} aria-label="Loading notes">
          <Skeleton lines={4} height={18} />
          <Skeleton height={280} />
        </div>
      ) : workspace.notes.length === 0 ? (
        <EmptyState
          icon={<FileText size={22} />}
          title="No notes yet"
          description="Start a note to collect observations, commands and insights for a challenge."
          action={
            <Button
              icon={<Plus size={14} />}
              onClick={() => workspace.newNote()}
            >
              Create your first note
            </Button>
          }
        />
      ) : (
        <div className={styles.workspace}>
          <aside className={styles.rail} aria-label="Saved notes">
            <p className={styles.railTitle}>
              Saved notes ({workspace.visibleNotes.length})
            </p>
            <div className={styles.railList}>
              {workspace.visibleNotes.map((note) => (
                <button
                  key={note.id}
                  type="button"
                  className={cn(
                    styles.noteCard,
                    note.id === workspace.selectedNote?.id &&
                      styles.noteCardActive,
                  )}
                  onClick={() => workspace.selectNote(note.id)}
                >
                  <span className={styles.noteCardTop}>
                    <strong>{note.title}</strong>
                    {note.pinned ? (
                      <Pin
                        size={12}
                        aria-label="Pinned"
                        className={styles.pinIcon}
                      />
                    ) : null}
                  </span>
                  <span className={styles.noteExcerpt}>{note.excerpt}</span>
                  <span className={styles.noteMeta}>
                    {note.challenge_id} · v{note.version}
                  </span>
                  <span className={styles.noteTags}>
                    {note.tags.slice(0, 3).map((tag) => (
                      <span key={tag}>#{tag}</span>
                    ))}
                  </span>
                </button>
              ))}
              {workspace.visibleNotes.length === 0 ? (
                <p className={styles.noMatches}>
                  No notes match the current filters.
                </p>
              ) : null}
            </div>
          </aside>

          <section className={styles.editorPane} aria-label="Note editor">
            <NoteMetaBar
              wordCount={countWords(workspace.draft.body)}
              readingTime={readingMinutes(workspace.draft.body)}
              version={workspace.selectedNote?.version ?? 0}
              saveState={workspace.saveState}
              updatedAt={workspace.selectedNote?.updated_at}
              pinned={workspace.draft.pinned}
            />
            <TemplatePicker
              templates={workspace.templates}
              onApply={workspace.applyTemplate}
            />
            <NoteEditor
              draft={workspace.draft}
              onChange={workspace.updateDraft}
              onSave={workspace.save}
              onPin={() => {
                if (workspace.selectedNote)
                  workspace.togglePin(workspace.selectedNote.id);
              }}
              onDelete={() => {
                if (workspace.selectedNote)
                  workspace.removeNote(workspace.selectedNote.id);
              }}
              isNew={!workspace.selectedNote}
              saving={workspace.saveState === "saving"}
              error={workspace.error}
            />
          </section>

          <section className={styles.previewPane} aria-label="Note preview">
            <NotePreview
              note={workspace.selectedNote}
              title={
                workspace.previewRevision
                  ? (workspace.selectedNote?.title ?? "")
                  : workspace.draft.title
              }
              body={workspace.previewRevision?.body ?? workspace.draft.body}
              revision={workspace.previewRevision}
              onClearRevision={workspace.clearRevisionPreview}
            />
          </section>

          <aside className={styles.timelinePane}>
            <RevisionTimeline
              revisions={workspace.revisions}
              selectedId={workspace.previewRevision?.id}
              onSelect={workspace.selectRevision}
            />
          </aside>
        </div>
      )}
    </main>
  );
}
