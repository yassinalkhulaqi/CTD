/**
 * Secure, namespaced storage for the session tokens.
 *
 * The refresh token is kept in `localStorage` so the session survives a page
 * reload, while the short lived access token lives in memory only.
 */

import type { TokenPair } from "./types";

const REFRESH_KEY = "ctfd.auth.refresh";
const USER_KEY = "ctfd.auth.user";

let accessToken: string | null = null;
let accessTokenExpiry: number | null = null;

/**
 * Return the in-memory access token.
 *
 * @returns The access token or `null` when the user is signed out.
 */
export function getAccessToken(): string | null {
  return accessToken;
}

/**
 * Store the access token together with its expiry timestamp.
 *
 * @param token - The issued token pair.
 */
export function setTokenPair(token: TokenPair): void {
  accessToken = token.access_token;
  accessTokenExpiry = Date.now() + token.expires_in * 1000;
  writeRefreshToken(token.refresh_token);
}

/**
 * Clear the in-memory access token.
 */
export function clearAccessToken(): void {
  accessToken = null;
  accessTokenExpiry = null;
}

/**
 * Return whether the access token is still usable.
 *
 * @param skewMs - Safety margin applied to the expiry check.
 * @returns ``True`` when a valid access token is held.
 */
export function hasValidAccessToken(skewMs = 5_000): boolean {
  if (!accessToken || !accessTokenExpiry) return false;
  return accessTokenExpiry - skewMs > Date.now();
}

/**
 * Return the persisted refresh token.
 *
 * @returns The refresh token or `null`.
 */
export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

/**
 * Persist the refresh token.
 *
 * @param token - The refresh token to persist.
 */
export function writeRefreshToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(REFRESH_KEY, token);
}

/**
 * Remove the persisted refresh token.
 */
export function clearRefreshToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(REFRESH_KEY);
}

/**
 * Persist the authenticated user profile.
 *
 * @param user - The serialised user profile.
 */
export function writeUser(user: unknown): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * Read the persisted user profile.
 *
 * @returns The parsed user profile or `null`.
 */
export function readUser<T>(): T | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

/**
 * Remove every persisted credential.
 */
export function clearSession(): void {
  clearAccessToken();
  clearRefreshToken();
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(USER_KEY);
  }
}
