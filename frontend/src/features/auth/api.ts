/**
 * Authentication API client.
 */

import { del, get, post } from "../../api";
import type { ApiKey, AuthConfig, AuthUser, LoginResponse, Principal, TokenPair } from "./types";

/**
 * Authenticate with a username and password.
 *
 * @param username - The username or email of the account.
 * @param password - The plain text password.
 * @returns The login response including the issued tokens.
 */
export function login(username: string, password: string): Promise<LoginResponse> {
  return post<LoginResponse>("/api/auth/login", { username, password });
}

/**
 * Exchange a refresh token for a new token pair.
 *
 * @param refreshToken - The stored refresh token.
 * @returns The refreshed token pair.
 */
export function refreshSession(refreshToken: string): Promise<TokenPair> {
  return post<TokenPair>("/api/auth/refresh", { refresh_token: refreshToken });
}

/**
 * Revoke the session bound to a refresh token.
 *
 * @param refreshToken - The stored refresh token.
 */
export function logout(refreshToken: string): Promise<void> {
  return del<void>("/api/auth/logout", {
    json: { refresh_token: refreshToken },
  });
}

/**
 * Return the profile of the authenticated caller.
 *
 * @returns The current principal.
 */
export function fetchPrincipal(): Promise<Principal> {
  return get<Principal>("/api/auth/me");
}

/**
 * Return the authentication capabilities of the server.
 *
 * @returns The server auth configuration.
 */
export function fetchAuthConfig(): Promise<AuthConfig> {
  return get<AuthConfig>("/api/auth/config");
}

/**
 * Return the API keys owned by a user.
 *
 * @param userId - The owner of the keys.
 * @returns The list of API keys.
 */
export function fetchApiKeys(userId: string): Promise<ApiKey[]> {
  return get<ApiKey[]>(`/api/auth/api-keys?user_id=${encodeURIComponent(userId)}`);
}

/**
 * Create a new API key.
 *
 * @param userId - The owner of the key.
 * @param name - A human readable label.
 * @param scopes - Optional permission scopes.
 * @returns The created key including its one time plaintext value.
 */
export function createApiKey(
  userId: string,
  name: string,
  scopes: string[] = [],
): Promise<{ key: ApiKey; plaintext: string }> {
  return post<{ key: ApiKey; plaintext: string }>("/api/auth/api-keys", {
    user_id: userId,
    name,
    scopes,
  });
}

/**
 * Revoke an API key.
 *
 * @param keyId - The identifier of the key.
 * @param userId - The owner of the key.
 */
export function revokeApiKey(keyId: string, userId: string): Promise<void> {
  return del<void>(`/api/auth/api-keys/${encodeURIComponent(keyId)}?user_id=${encodeURIComponent(userId)}`);
}

/**
 * Register a new dashboard account.
 *
 * @param username - The desired username.
 * @param email - The account email address.
 * @param password - The plain text password.
 * @returns The created user.
 */
export function register(username: string, email: string, password: string): Promise<AuthUser> {
  return post<AuthUser>("/api/auth/register", { username, email, password });
}
