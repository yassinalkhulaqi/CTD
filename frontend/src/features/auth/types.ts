/**
 * Authentication types shared by the auth feature.
 */

import type { MemberRole } from "../../types";

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  role: MemberRole;
  team_id: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

export interface LoginResponse {
  user: AuthUser;
  tokens: TokenPair;
  permissions: string[];
}

export interface Principal {
  user_id: string;
  username: string;
  role: MemberRole;
  team_id: string | null;
  auth_method: string;
  permissions: string[];
}

export interface ApiKey {
  id: string;
  user_id: string;
  name: string;
  prefix: string;
  masked: string;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface AuthConfig {
  enabled: boolean;
  access_token_ttl_seconds: number;
  permissions: string[];
}

/** The well known permission strings exposed by the API. */
export const PERMISSIONS = {
  dashboardView: "dashboard:view",
  statsView: "stats:view",
  teamView: "team:view",
  teamManage: "team:manage",
  memberView: "member:view",
  memberManage: "member:manage",
  challengeView: "challenge:view",
  challengeCreate: "challenge:create",
  challengeUpdate: "challenge:update",
  challengeDelete: "challenge:delete",
  solveView: "solve:view",
  solveCreate: "solve:create",
  solveDelete: "solve:delete",
  apiKeyManage: "api_key:manage",
  auditView: "audit:view",
} as const;

/** The role names understood by the API. */
export const ROLES = ["viewer", "analyst", "lead", "admin"] as const;

export type RoleName = (typeof ROLES)[number];
