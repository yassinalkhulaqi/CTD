/** Typed API adapter for the writeups library. */

import { buildQuery, del, get, patch, post } from "../../api/client";
import type {
  BookmarkResult,
  LibraryFilters,
  ReviewPayload,
  Writeup,
  WriteupCreatePayload,
  WriteupList,
  WriteupReview,
  WriteupStats,
  WriteupUpdatePayload,
} from "./types";

const BASE = "/api/writeups";

/**
 * List writeups with filters and pagination.
 *
 * @param filters - Active library filters.
 * @param offset - Result offset.
 * @param limit - Maximum page size.
 * @param signal - Optional abort signal.
 * @returns The matching page of writeups.
 */
export function listWriteups(
  filters: LibraryFilters,
  offset = 0,
  limit = 24,
  signal?: AbortSignal,
): Promise<WriteupList> {
  const query = buildQuery({
    status: filters.status === "all" ? undefined : filters.status,
    category: filters.category === "all" ? undefined : filters.category,
    tag: filters.tag || undefined,
    search: filters.search || undefined,
    sort: filters.sort,
    offset,
    limit,
  });
  return get<WriteupList>(`${BASE}${query}`, { signal });
}

/**
 * Fetch a single writeup.
 *
 * @param id - The writeup identifier.
 * @param trackView - Whether the server should count a view.
 * @returns The writeup.
 */
export function getWriteup(id: string, trackView = true): Promise<Writeup> {
  const query = buildQuery({ track_view: trackView });
  return get<Writeup>(`${BASE}/${encodeURIComponent(id)}${query}`);
}

/**
 * Create a draft writeup.
 *
 * @param payload - The writeup fields.
 * @returns The created writeup.
 */
export function createWriteup(payload: WriteupCreatePayload): Promise<Writeup> {
  return post<Writeup>(BASE, payload);
}

/**
 * Edit a writeup.
 *
 * @param id - The writeup identifier.
 * @param payload - The fields to change.
 * @returns The updated writeup.
 */
export function updateWriteup(
  id: string,
  payload: WriteupUpdatePayload,
): Promise<Writeup> {
  return patch<Writeup>(`${BASE}/${encodeURIComponent(id)}`, payload);
}

/**
 * Delete a writeup.
 *
 * @param id - The writeup identifier.
 */
export function deleteWriteup(id: string): Promise<void> {
  return del<void>(`${BASE}/${encodeURIComponent(id)}`);
}

/**
 * Submit a draft for review.
 *
 * @param id - The writeup identifier.
 * @returns The updated writeup.
 */
export function submitWriteup(id: string): Promise<Writeup> {
  return post<Writeup>(`${BASE}/${encodeURIComponent(id)}/submit`);
}

/**
 * Publish an approved writeup.
 *
 * @param id - The writeup identifier.
 * @returns The updated writeup.
 */
export function publishWriteup(id: string): Promise<Writeup> {
  return post<Writeup>(`${BASE}/${encodeURIComponent(id)}/publish`);
}

/**
 * Withdraw a published writeup back to drafts.
 *
 * @param id - The writeup identifier.
 * @returns The updated writeup.
 */
export function withdrawWriteup(id: string): Promise<Writeup> {
  return post<Writeup>(`${BASE}/${encodeURIComponent(id)}/withdraw`);
}

/**
 * Submit or change a member's rating.
 *
 * @param id - The writeup identifier.
 * @param memberId - The rating member.
 * @param score - A score between one and five.
 * @returns The updated writeup.
 */
export function rateWriteup(
  id: string,
  memberId: string,
  score: number,
): Promise<Writeup> {
  return post<Writeup>(`${BASE}/${encodeURIComponent(id)}/rate`, {
    member_id: memberId,
    score,
  });
}

/**
 * Toggle a member's bookmark.
 *
 * @param id - The writeup identifier.
 * @param memberId - The bookmarking member.
 * @returns The new bookmark state.
 */
export function toggleBookmark(
  id: string,
  memberId: string,
): Promise<BookmarkResult> {
  return post<BookmarkResult>(`${BASE}/${encodeURIComponent(id)}/bookmark`, {
    member_id: memberId,
  });
}

/**
 * Return bookmarked writeups for a member.
 *
 * @param memberId - The member identifier.
 * @returns The bookmarked writeups.
 */
export function bookmarksFor(memberId: string): Promise<Writeup[]> {
  return get<Writeup[]>(`${BASE}/bookmarks/${encodeURIComponent(memberId)}`);
}

/**
 * Return library statistics.
 *
 * @returns The aggregate statistics.
 */
export function getStats(): Promise<WriteupStats> {
  return get<WriteupStats>(`${BASE}/stats`);
}

/**
 * Return writeups authored by a member.
 *
 * @param authorId - The author identifier.
 * @returns Their writeups.
 */
export function mine(authorId: string): Promise<Writeup[]> {
  const query = buildQuery({ author_id: authorId });
  return get<Writeup[]>(`${BASE}/mine${query}`);
}

/**
 * Return the highest rated published writeups.
 *
 * @param limit - Maximum number of results.
 * @returns The top rated writeups.
 */
export function topRated(limit = 10): Promise<Writeup[]> {
  const query = buildQuery({ limit });
  return get<Writeup[]>(`${BASE}/top${query}`);
}

/**
 * Return the review timeline of a writeup.
 *
 * @param id - The writeup identifier.
 * @returns The reviews in chronological order.
 */
export function listReviews(id: string): Promise<WriteupReview[]> {
  return get<WriteupReview[]>(`${BASE}/${encodeURIComponent(id)}/reviews`);
}

/**
 * Add a peer review.
 *
 * @param id - The writeup identifier.
 * @param payload - The review verdict and comment.
 * @returns The created review.
 */
export function addReview(
  id: string,
  payload: ReviewPayload,
): Promise<WriteupReview> {
  return post<WriteupReview>(
    `${BASE}/${encodeURIComponent(id)}/reviews`,
    payload,
  );
}
