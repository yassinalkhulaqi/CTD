/** The routed writeups library page. */

import { useCallback, useEffect, useMemo, useState } from "react";
import { BookOpen, FilePlus2, Star, Trophy, Users } from "lucide-react";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Skeleton,
  StatCard,
} from "../../components/ui";
import {
  addReview,
  bookmarksFor,
  createWriteup,
  deleteWriteup,
  getWriteup,
  listReviews,
  publishWriteup,
  rateWriteup,
  submitWriteup,
  toggleBookmark,
  withdrawWriteup,
} from "./api";
import { tagFrequency } from "./logic";
import { useWriteupLibrary, useWriteupStats } from "./hooks";
import type {
  LibraryFilters,
  ReviewPayload,
  Writeup,
  WriteupCreatePayload,
  WriteupReview,
} from "./types";
import { DEFAULT_FILTERS } from "./types";
import { BookmarkButton } from "./components/BookmarkButton";
import { PublishBar, type WorkflowAction } from "./components/PublishBar";
import { ReviewPanel } from "./components/ReviewPanel";
import { WriteupCard } from "./components/WriteupCard";
import { WriteupComposer } from "./components/WriteupComposer";
import { WriteupFilters } from "./components/WriteupFilters";
import { WriteupReader } from "./components/WriteupReader";
import styles from "./WriteupsPage.module.css";

const MEMBER_ID = "member-1";
const PAGE_SIZE = 24;

/** A transient status message shown above the page content. */
interface Notice {
  tone: "success" | "error";
  message: string;
}

/**
 * Render the complete writeups library: filters, grid, reader and workflow.
 *
 * @returns The page element.
 */
export function WriteupsPage() {
  const [filters, setFilters] = useState<LibraryFilters>({
    ...DEFAULT_FILTERS,
  });
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Writeup | null>(null);
  const [reviews, setReviews] = useState<WriteupReview[]>([]);
  const [bookmarks, setBookmarks] = useState<Set<string>>(new Set());
  const [composerOpen, setComposerOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);

  const library = useWriteupLibrary(filters, page);
  const stats = useWriteupStats();
  const refetchLibrary = library.refetch;
  const refetchStats = stats.refetch;

  useEffect(() => {
    bookmarksFor(MEMBER_ID)
      .then((items) => setBookmarks(new Set(items.map((item) => item.id))))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setReviews([]);
      return;
    }
    let active = true;
    getWriteup(selectedId)
      .then((item) => {
        if (active) setDetail(item);
      })
      .catch(() => {
        if (active)
          setNotice({ tone: "error", message: "Could not open that writeup." });
      });
    listReviews(selectedId)
      .then((items) => {
        if (active) setReviews(items);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [selectedId]);

  const applyWriteup = useCallback(
    (updated: Writeup) => {
      setDetail((current) => (current?.id === updated.id ? updated : current));
      refetchLibrary();
      refetchStats();
    },
    [refetchLibrary, refetchStats],
  );

  const report = useCallback((tone: Notice["tone"], message: string) => {
    setNotice({ tone, message });
  }, []);

  const availableTags = useMemo(
    () => tagFrequency(library.data?.items ?? []),
    [library.data?.items],
  );
  const totalPages = Math.max(
    1,
    Math.ceil((library.data?.total ?? 0) / PAGE_SIZE),
  );

  const changeFilters = (next: LibraryFilters) => {
    setFilters(next);
    setPage(0);
  };

  const handleBookmark = async (writeup: Writeup) => {
    const previous = new Set(bookmarks);
    const next = new Set(bookmarks);
    if (next.has(writeup.id)) next.delete(writeup.id);
    else next.add(writeup.id);
    setBookmarks(next);
    try {
      await toggleBookmark(writeup.id, MEMBER_ID);
      refetchStats();
    } catch {
      setBookmarks(previous);
      report("error", "The bookmark could not be updated.");
    }
  };

  const handleRate = async (score: number) => {
    if (!detail) return;
    setBusy(true);
    try {
      applyWriteup(await rateWriteup(detail.id, MEMBER_ID, score));
      report("success", `Thanks — your ${score}-star rating was recorded.`);
    } catch {
      report("error", "Your rating could not be saved.");
    } finally {
      setBusy(false);
    }
  };

  const runWorkflow = async (action: WorkflowAction) => {
    if (!detail) return;
    setBusy(true);
    try {
      const updated =
        action === "submit"
          ? await submitWriteup(detail.id)
          : action === "publish"
            ? await publishWriteup(detail.id)
            : await withdrawWriteup(detail.id);
      applyWriteup(updated);
      setReviews(await listReviews(updated.id));
      const verb =
        action === "submit"
          ? "submitted"
          : action === "publish"
            ? "published"
            : "withdrawn";
      report("success", `Writeup ${verb}.`);
    } catch (error) {
      report(
        "error",
        error instanceof Error ? error.message : "Workflow action failed.",
      );
    } finally {
      setBusy(false);
    }
  };

  const handleReview = async (payload: ReviewPayload) => {
    if (!detail) return;
    setBusy(true);
    try {
      await addReview(detail.id, payload);
      setReviews(await listReviews(detail.id));
      refetchStats();
      report("success", "Review submitted.");
    } catch (error) {
      report(
        "error",
        error instanceof Error ? error.message : "Review failed.",
      );
    } finally {
      setBusy(false);
    }
  };

  const handleCreate = async (payload: WriteupCreatePayload) => {
    setBusy(true);
    try {
      const created = await createWriteup(payload);
      setComposerOpen(false);
      setSelectedId(created.id);
      refetchStats();
      refetchLibrary();
      report("success", "Draft created. Add a review before publishing.");
    } catch (error) {
      report(
        "error",
        error instanceof Error
          ? error.message
          : "Could not create the writeup.",
      );
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!detail) return;
    setBusy(true);
    try {
      await deleteWriteup(detail.id);
      setSelectedId(null);
      setBookmarks((current) => {
        const next = new Set(current);
        next.delete(detail.id);
        return next;
      });
      refetchLibrary();
      refetchStats();
      report("success", "Writeup deleted.");
    } catch {
      report("error", "The writeup could not be deleted.");
    } finally {
      setBusy(false);
    }
  };

  const canPublish = reviews.some((review) => review.approved);
  const statsData = stats.data;
  const items = library.data?.items ?? [];

  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>Knowledge · Writeups</p>
          <h1 className={styles.h1}>The writeups library</h1>
          <p className={styles.lede}>
            A curated collection of solved-challenge writeups. Rate the best
            explanations, review drafts and keep the team's hard-won knowledge
            in one place.
          </p>
        </div>
        <Button
          size="lg"
          icon={<FilePlus2 size={16} />}
          onClick={() => setComposerOpen((open) => !open)}
        >
          {composerOpen ? "Close composer" : "Write a writeup"}
        </Button>
      </header>

      {notice ? (
        <div
          className={
            notice.tone === "success"
              ? styles.noticeSuccess
              : styles.noticeError
          }
          role="status"
          onClick={() => setNotice(null)}
        >
          {notice.message}
        </div>
      ) : null}

      <section className={styles.stats} aria-label="Library statistics">
        <StatCard
          label="Published"
          value={statsData?.published ?? <Skeleton width={40} height={28} />}
          icon={<BookOpen size={16} />}
          accent="#6366f1"
          meta={`of ${statsData?.total ?? 0} total writeups`}
        />
        <StatCard
          label="In review"
          value={statsData?.in_review ?? <Skeleton width={40} height={28} />}
          icon={<Users size={16} />}
          accent="#f59e0b"
          meta="awaiting a verdict"
        />
        <StatCard
          label="Ratings"
          value={
            statsData?.total_ratings ?? <Skeleton width={40} height={28} />
          }
          icon={<Star size={16} />}
          accent="#f59e0b"
          meta="community scores"
        />
        <StatCard
          label="Top score"
          value={
            statsData?.top_rated[0] ? (
              statsData.top_rated[0].bayesian_score.toFixed(2)
            ) : (
              <Skeleton width={40} height={28} />
            )
          }
          icon={<Trophy size={16} />}
          accent="#34d399"
          meta="Bayesian rating"
        />
      </section>

      {composerOpen ? (
        <WriteupComposer
          busy={busy}
          onCancel={() => setComposerOpen(false)}
          onCreate={(payload) => void handleCreate(payload)}
        />
      ) : null}

      {library.error ? (
        <ErrorState
          title="The library could not be loaded"
          message={library.error.message}
          onRetry={library.refetch}
        />
      ) : null}

      {!library.error ? (
        <WriteupFilters
          filters={filters}
          onChange={changeFilters}
          tags={availableTags}
          resultCount={library.data?.total ?? 0}
        />
      ) : null}

      {library.loading && items.length === 0 && !library.error ? (
        <div className={styles.grid} aria-label="Loading writeups">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className={styles.skeletonCard}>
              <Skeleton width="45%" height={12} />
              <Skeleton width="90%" height={24} />
              <Skeleton lines={3} />
            </div>
          ))}
        </div>
      ) : null}

      {!library.loading && !library.error && items.length === 0 ? (
        <EmptyState
          icon={<BookOpen size={24} />}
          title="No writeups match these filters"
          description="Try another category or clear the search to see the full library."
          action={
            <Button
              variant="secondary"
              size="sm"
              onClick={() => changeFilters({ ...DEFAULT_FILTERS })}
            >
              Clear filters
            </Button>
          }
        />
      ) : null}

      {items.length > 0 ? (
        <div className={styles.grid}>
          {items.map((writeup) => (
            <WriteupCard
              key={writeup.id}
              writeup={writeup}
              bookmarked={bookmarks.has(writeup.id)}
              active={selectedId === writeup.id}
              onOpen={(item) => setSelectedId(item.id)}
              onBookmark={(item) => void handleBookmark(item)}
            />
          ))}
        </div>
      ) : null}

      {totalPages > 1 ? (
        <nav className={styles.pagination} aria-label="Library pages">
          <Button
            variant="secondary"
            size="sm"
            disabled={page === 0}
            onClick={() => setPage((value) => Math.max(0, value - 1))}
          >
            Previous
          </Button>
          <span>
            Page {page + 1} of {totalPages}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={page + 1 >= totalPages}
            onClick={() => setPage((value) => value + 1)}
          >
            Next
          </Button>
        </nav>
      ) : null}

      {selectedId && detail ? (
        <section className={styles.readingSection} aria-label="Writeup reader">
          <div className={styles.readingHeader}>
            <h2 className={styles.readingTitle}>Reading view</h2>
            <div className={styles.readingControls}>
              <Badge tone="accent" outline>
                {detail.category}
              </Badge>
              <BookmarkButton
                bookmarked={bookmarks.has(detail.id)}
                onToggle={() => void handleBookmark(detail)}
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedId(null)}
              >
                Back to library
              </Button>
            </div>
          </div>
          <div className={styles.readingLayout}>
            <WriteupReader
              writeup={detail}
              bookmarked={bookmarks.has(detail.id)}
              onRate={(score) => void handleRate(score)}
              onBookmark={() => void handleBookmark(detail)}
              onClose={() => setSelectedId(null)}
            />
            <aside className={styles.sidebar}>
              <PublishBar
                writeup={detail}
                canPublish={canPublish}
                busy={busy}
                onAction={(action) => void runWorkflow(action)}
              />
              <ReviewPanel
                writeup={detail}
                reviews={reviews}
                reviewerId={MEMBER_ID}
                busy={busy}
                onReview={(payload) => void handleReview(payload)}
              />
              <Button
                variant="ghost"
                size="sm"
                disabled={busy}
                onClick={() => void handleDelete()}
              >
                Delete this writeup
              </Button>
            </aside>
          </div>
        </section>
      ) : null}
    </div>
  );
}

export default WriteupsPage;
