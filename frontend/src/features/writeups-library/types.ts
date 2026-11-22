/** Domain types and view models for the writeups library. */

export type WriteupStatus = "draft" | "review" | "published";
export type ReviewVerdict = "approve" | "request_changes";
export type WriteupCategory =
  "web" | "crypto" | "pwn" | "reverse" | "forensics" | "osint" | "misc";
export type WriteupDifficulty =
  "trivial" | "easy" | "medium" | "hard" | "insane";
export type SortKey = "date" | "rating" | "views" | "title";

/** A heading in a writeup's table of contents. */
export interface TocEntry {
  level: number;
  title: string;
  anchor: string;
}

/** A heading delimited slice of the markdown body. */
export interface MarkdownSection {
  level: number;
  title: string;
  anchor: string;
  content: string;
}

/** A writeup returned by the API. */
export interface Writeup {
  id: string;
  challenge_id: string;
  author_id: string;
  title: string;
  slug: string;
  summary: string;
  body: string;
  category: WriteupCategory;
  difficulty: WriteupDifficulty;
  tags: string[];
  status: WriteupStatus;
  excerpt: string;
  word_count: number;
  reading_minutes: number;
  average_rating: number;
  bayesian_score: number;
  rating_sum: number;
  rating_count: number;
  views: number;
  created_at: string;
  published_at: string | null;
  toc: TocEntry[];
}

/** A peer review returned by the API. */
export interface WriteupReview {
  id: string;
  writeup_id: string;
  reviewer_id: string;
  verdict: ReviewVerdict;
  comment: string;
  approved: boolean;
  created_at: string;
}

/** A paginated library response. */
export interface WriteupList {
  items: Writeup[];
  total: number;
  offset: number;
  limit: number;
}

/** One category aggregate. */
export interface CategoryStat {
  category: WriteupCategory;
  total: number;
  published: number;
  in_review: number;
  publication_rate: number;
  average_score: number;
}

/** One status aggregate. */
export interface StatusStat {
  status: WriteupStatus;
  count: number;
  share: number;
}

/** Library wide statistics. */
export interface WriteupStats {
  total: number;
  published: number;
  drafts: number;
  in_review: number;
  total_views: number;
  total_ratings: number;
  bookmarks: number;
  publication_rate: number;
  average_views: number;
  by_category: CategoryStat[];
  by_status: StatusStat[];
  top_rated: Writeup[];
}

/** Result returned after toggling a bookmark. */
export interface BookmarkResult {
  writeup_id: string;
  member_id: string;
  bookmarked: boolean;
  count: number;
}

/** Filters applied to the library grid. */
export interface LibraryFilters {
  status: WriteupStatus | "all";
  category: WriteupCategory | "all";
  sort: SortKey;
  search: string;
  tag: string;
}

/** Payload used when creating a writeup. */
export interface WriteupCreatePayload {
  challenge_id: string;
  author_id: string;
  title: string;
  summary: string;
  body: string;
  category: WriteupCategory;
  difficulty: WriteupDifficulty;
  tags: string[];
}

/** Partial payload used when editing a writeup. */
export type WriteupUpdatePayload = Partial<
  Pick<
    WriteupCreatePayload,
    | "challenge_id"
    | "title"
    | "summary"
    | "body"
    | "category"
    | "difficulty"
    | "tags"
  >
>;

/** Payload used when recording a review. */
export interface ReviewPayload {
  reviewer_id: string;
  verdict: ReviewVerdict;
  comment: string;
}

/** All categories understood by the library. */
export const CATEGORIES: WriteupCategory[] = [
  "web",
  "crypto",
  "pwn",
  "reverse",
  "forensics",
  "osint",
  "misc",
];

/** All difficulty tiers understood by the library. */
export const DIFFICULTIES: WriteupDifficulty[] = [
  "trivial",
  "easy",
  "medium",
  "hard",
  "insane",
];

/** Human readable labels for every category. */
export const CATEGORY_LABELS: Record<WriteupCategory, string> = {
  web: "Web",
  crypto: "Crypto",
  pwn: "Binary",
  reverse: "Reverse",
  forensics: "Forensics",
  osint: "OSINT",
  misc: "Misc",
};

/** Human readable labels for every status. */
export const STATUS_LABELS: Record<WriteupStatus, string> = {
  draft: "Draft",
  review: "In review",
  published: "Published",
};

/** Default filter configuration for the library. */
export const DEFAULT_FILTERS: LibraryFilters = {
  status: "published",
  category: "all",
  sort: "date",
  search: "",
  tag: "",
};
