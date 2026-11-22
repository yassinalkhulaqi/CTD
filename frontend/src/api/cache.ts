/**
 * A small query cache with stale-while-revalidate semantics.
 *
 * The cache is intentionally framework agnostic so it can be unit tested in
 * isolation and reused by both the query and the mutation hooks.
 */

/** An immutable view of a cache entry. */
export interface CacheSnapshot<T = unknown> {
  /** The cached value. */
  data: T | undefined;
  /** The error of the last failure. */
  error: unknown;
  /** The timestamp of the last successful fetch. */
  updatedAt: number;
  /** The timestamp of the last failure. */
  erroredAt: number;
}

/** A cache entry holding the last known value of a query. */
export interface CacheEntry<T = unknown> {
  /** The cached value. */
  data: T | undefined;
  /** The timestamp of the last successful fetch. */
  updatedAt: number;
  /** The timestamp of the last failure. */
  erroredAt: number;
  /** The error of the last failure. */
  error: unknown;
  /** The listeners notified when the entry changes. */
  listeners: Set<() => void>;
  /** The immutable snapshot handed to the subscribers. */
  snapshot: CacheSnapshot<T>;
}

/** Options controlling the behaviour of the cache. */
export interface QueryCacheOptions {
  /** The time after which an entry is considered stale, in milliseconds. */
  staleTime?: number;
  /** The maximum number of entries kept in the cache. */
  maxEntries?: number;
}

/** The default stale time of a cache entry. */
export const DEFAULT_STALE_TIME = 15_000;

export class QueryCache {
  private readonly entries = new Map<string, CacheEntry>();
  private readonly staleTime: number;
  private readonly maxEntries: number;

  constructor(options: QueryCacheOptions = {}) {
    this.staleTime = options.staleTime ?? DEFAULT_STALE_TIME;
    this.maxEntries = options.maxEntries ?? 200;
  }

  /**
   * Return the entry stored for a key.
   *
   * @param key - The cache key.
   * @returns The entry, if present.
   */
  get<T>(key: string): CacheEntry<T> | undefined {
    return this.entries.get(key) as CacheEntry<T> | undefined;
  }

  /**
   * Store a value for a key.
   *
   * @param key - The cache key.
   * @param data - The value to store.
   */
  set<T>(key: string, data: T): void {
    const existing = this.entries.get(key);
    const updatedAt = Date.now();
    if (existing) {
      existing.data = data;
      existing.updatedAt = updatedAt;
      existing.erroredAt = 0;
      existing.error = undefined;
      existing.snapshot = {
        data,
        error: undefined,
        updatedAt,
        erroredAt: 0,
      };
    } else {
      this.entries.set(key, {
        data,
        updatedAt,
        erroredAt: 0,
        error: undefined,
        listeners: new Set(),
        snapshot: { data, error: undefined, updatedAt, erroredAt: 0 },
      });
    }
    this.prune();
  }

  /**
   * Record a failure for a key without discarding the last known value.
   *
   * @param key - The cache key.
   * @param error - The failure.
   */
  setError(key: string, error: unknown): void {
    const erroredAt = Date.now();
    const entry = this.entries.get(key);
    if (entry) {
      entry.error = error;
      entry.erroredAt = erroredAt;
      entry.snapshot = {
        data: entry.data,
        error,
        updatedAt: entry.updatedAt,
        erroredAt,
      };
    } else {
      this.entries.set(key, {
        data: undefined,
        updatedAt: 0,
        erroredAt,
        error,
        listeners: new Set(),
        snapshot: { data: undefined, error, updatedAt: 0, erroredAt },
      });
    }
  }

  /**
   * Return whether an entry exists and is still fresh.
   *
   * @param key - The cache key.
   * @returns `true` when the entry is fresh.
   */
  isFresh(key: string): boolean {
    const entry = this.entries.get(key);
    if (!entry || entry.updatedAt === 0) return false;
    return Date.now() - entry.updatedAt < this.staleTime;
  }

  /**
   * Remove an entry from the cache.
   *
   * @param key - The cache key.
   */
  invalidate(key: string): void {
    this.entries.delete(key);
  }

  /**
   * Remove every entry whose key starts with the given prefix.
   *
   * @param prefix - The key prefix.
   * @returns The number of removed entries.
   */
  invalidatePrefix(prefix: string): number {
    let removed = 0;
    for (const key of [...this.entries.keys()]) {
      if (key.startsWith(prefix)) {
        this.entries.delete(key);
        removed += 1;
      }
    }
    return removed;
  }

  /**
   * Remove every entry from the cache.
   */
  clear(): void {
    this.entries.clear();
  }

  /**
   * Register a listener notified when an entry changes.
   *
   * @param key - The cache key.
   * @param listener - The listener.
   * @returns A function removing the listener.
   */
  subscribe(key: string, listener: () => void): () => void {
    const entry = this.entries.get(key) ?? {
      data: undefined,
      updatedAt: 0,
      erroredAt: 0,
      error: undefined,
      listeners: new Set<() => void>(),
      snapshot: {
        data: undefined,
        error: undefined,
        updatedAt: 0,
        erroredAt: 0,
      },
    };
    this.entries.set(key, entry);
    entry.listeners.add(listener);
    return () => {
      entry.listeners.delete(listener);
    };
  }

  /**
   * Notify every listener of an entry.
   *
   * @param key - The cache key.
   */
  notify(key: string): void {
    const entry = this.entries.get(key);
    if (!entry) return;
    for (const listener of entry.listeners) listener();
  }

  /**
   * Return the number of entries in the cache.
   *
   * @returns The size of the cache.
   */
  get size(): number {
    return this.entries.size;
  }

  /**
   * Return every key currently stored in the cache.
   *
   * @returns The cache keys.
   */
  keys(): string[] {
    return [...this.entries.keys()];
  }

  private prune(): void {
    if (this.entries.size <= this.maxEntries) return;
    const ordered = [...this.entries.entries()].sort(
      ([, left], [, right]) => left.updatedAt - right.updatedAt,
    );
    const excess = this.entries.size - this.maxEntries;
    for (let index = 0; index < excess; index += 1) {
      const entry = ordered[index];
      if (entry) this.entries.delete(entry[0]);
    }
  }
}

/** The application wide query cache. */
export const queryCache = new QueryCache();

/**
 * Build a stable cache key from a name and parameters.
 *
 * @param name - The name of the query.
 * @param params - The parameters of the query.
 * @returns The cache key.
 */
export function queryKey(name: string, params?: unknown): string {
  if (params === undefined) return name;
  return `${name}:${stableStringify(params)}`;
}

/**
 * Serialise a value into a deterministic JSON string.
 *
 * @param value - The value to serialise.
 * @returns The deterministic representation.
 */
export function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object")
    return JSON.stringify(value) ?? "null";
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(",")}]`;
  }
  const entries = Object.entries(value as Record<string, unknown>)
    .filter(([, item]) => item !== undefined)
    .sort(([left], [right]) => (left < right ? -1 : 1));
  return `{${entries
    .map(([key, item]) => `${JSON.stringify(key)}:${stableStringify(item)}`)
    .join(",")}}`;
}
