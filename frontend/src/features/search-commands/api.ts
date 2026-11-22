/** Typed API adapter for the search and command endpoints. */

import {
  buildQuery,
  del,
  get,
  post,
  type RequestOptions,
} from "../../api/client";
import type {
  Command,
  CommandExecution,
  CommandInput,
  CommandList,
  IndexRequest,
  IndexResponse,
  SearchQuery,
  SearchResponse,
  SearchStats,
} from "./types";

/** The search resource endpoints. */
export const searchApi = {
  /** Execute a search query against the index. */
  search(
    query: SearchQuery,
    options?: RequestOptions,
  ): Promise<SearchResponse> {
    const search = buildQuery({
      q: query.q,
      limit: query.limit,
      kind: query.kinds?.join(","),
      tag: query.tags?.join(","),
    });
    return get<SearchResponse>(`/api/search${search}`, options);
  },

  /** Upsert custom documents and optionally rebuild from repositories. */
  index(
    payload: IndexRequest,
    options?: RequestOptions,
  ): Promise<IndexResponse> {
    return post<IndexResponse>("/api/search/index", payload, options);
  },

  /** List commands, optionally filtered by query and group. */
  commands(
    query = "",
    group?: string,
    options?: RequestOptions,
  ): Promise<CommandList> {
    const search = buildQuery({ q: query, group });
    return get<CommandList>(`/api/search/commands${search}`, options);
  },

  /** Register a new command. */
  register(payload: CommandInput, options?: RequestOptions): Promise<Command> {
    return post<Command>("/api/search/commands", payload, options);
  },

  /** Execute a command and receive its descriptor. */
  execute(
    commandId: string,
    arguments_ = "",
    options?: RequestOptions,
  ): Promise<CommandExecution> {
    return post<CommandExecution>(
      `/api/search/commands/${encodeURIComponent(commandId)}/execute`,
      { arguments: arguments_ },
      options,
    );
  },

  /** Return aggregate index statistics. */
  stats(options?: RequestOptions): Promise<SearchStats> {
    return get<SearchStats>("/api/search/stats", options);
  },

  /** Remove a document from the index. */
  remove(documentId: string, options?: RequestOptions): Promise<void> {
    return del<void>(
      `/api/search/documents/${encodeURIComponent(documentId)}`,
      options,
    );
  },
};
