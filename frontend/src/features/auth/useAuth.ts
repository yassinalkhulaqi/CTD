/**
 * React hook exposing the authentication state of the dashboard.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, configureAuth } from "../../api";
import * as authApi from "./api";
import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  hasValidAccessToken,
  readUser,
  setTokenPair,
  writeUser,
} from "./tokenStorage";
import type { AuthUser, Principal } from "./types";

/** The lifecycle of an authentication attempt. */
export type AuthStatus =
  "idle" | "loading" | "authenticated" | "anonymous" | "error";

/** The value returned by {@link useAuth}. */
export interface AuthState {
  status: AuthStatus;
  user: AuthUser | null;
  principal: Principal | null;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<boolean>;
  can: (permission: string) => boolean;
  isAuthenticated: boolean;
}

let refreshInFlight: Promise<boolean> | null = null;

configureAuth(
  () => getAccessToken(),
  () => refreshSessionOnce(),
);

/**
 * Refresh the session once and share the result between callers.
 *
 * @returns ``true`` when the session was refreshed successfully.
 */
export function refreshSessionOnce(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;

  const refreshToken = getRefreshToken();
  if (!refreshToken) return Promise.resolve(false);

  refreshInFlight = authApi
    .refreshSession(refreshToken)
    .then((tokens) => {
      setTokenPair(tokens);
      return true;
    })
    .catch(() => {
      clearSession();
      return false;
    })
    .finally(() => {
      refreshInFlight = null;
    });

  return refreshInFlight;
}

/**
 * Manage the authentication state of the dashboard.
 *
 * @returns The authentication state and the actions used to change it.
 */
export function useAuth(): AuthState {
  const [status, setStatus] = useState<AuthStatus>("idle");
  const [user, setUser] = useState<AuthUser | null>(() => readUser<AuthUser>());
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const loadPrincipal = useCallback(async () => {
    try {
      const current = await authApi.fetchPrincipal();
      if (!mounted.current) return;
      setPrincipal(current);
      setStatus("authenticated");
    } catch (caught) {
      if (!mounted.current) return;
      if (caught instanceof ApiError && caught.isUnauthorized) {
        clearSession();
        setStatus("anonymous");
      } else {
        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to load the session",
        );
        setStatus("error");
      }
    }
  }, []);

  useEffect(() => {
    void (async () => {
      const refreshed = await refreshSessionOnce();
      if (!mounted.current) return;
      if (!refreshed && !hasValidAccessToken()) {
        setStatus("anonymous");
        return;
      }
      await loadPrincipal();
    })();
  }, [loadPrincipal]);

  const login = useCallback(async (username: string, password: string) => {
    setStatus("loading");
    setError(null);
    try {
      const response = await authApi.login(username, password);
      setTokenPair(response.tokens);
      writeUser(response.user);
      if (!mounted.current) return;
      setUser(response.user);
      setStatus("authenticated");
    } catch (caught) {
      if (!mounted.current) return;
      const message =
        caught instanceof Error ? caught.message : "Unable to sign in";
      setError(message);
      setStatus("error");
      throw caught instanceof Error ? caught : new Error(message);
    }
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    clearSession();
    if (!mounted.current) return;
    setUser(null);
    setPrincipal(null);
    setStatus("anonymous");
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch {
        // The local session is already cleared; the server side revocation is
        // best effort so a network failure must not block the sign out.
      }
    }
  }, []);

  const refresh = useCallback(async () => {
    const refreshed = await refreshSessionOnce();
    if (refreshed) await loadPrincipal();
    return refreshed;
  }, [loadPrincipal]);

  const can = useCallback(
    (permission: string) => {
      if (!principal) return false;
      return principal.permissions.includes(permission);
    },
    [principal],
  );

  return useMemo(
    () => ({
      status,
      user,
      principal,
      error,
      login,
      logout,
      refresh,
      can,
      isAuthenticated: status === "authenticated" && principal !== null,
    }),
    [status, user, principal, error, login, logout, refresh, can],
  );
}
