/**
 * Domain types of the onboarding tour feature.
 *
 * The shapes mirror the typed API schemas so the UI never has to guess at the
 * payload it receives.
 */

/** The role a wizard step plays in the journey. */
export type StepKind = "welcome" | "setup" | "guide" | "review";

/** The derived state of a wizard step for one user. */
export type StepState =
  "locked" | "available" | "active" | "complete" | "skipped";

/** The visual tone of a generated welcome note. */
export type WelcomeTone = "info" | "success" | "tip";

/** A semantic colour token shared by badges and CSS modules. */
export type StateTone = "neutral" | "info" | "accent" | "success" | "warning";

/** A single ordered step of the setup wizard. */
export interface OnboardingStep {
  id: string;
  slug: string;
  title: string;
  description: string;
  target: string;
  order: number;
  completion_key: string;
  kind: StepKind;
  estimated_seconds: number;
  required: boolean;
  hint: string;
  icon: string;
  created_at: string;
  state: StepState | null;
  is_current: boolean;
  target_kind: string;
  duration_label: string;
}

/** A persisted progress record. */
export interface ProgressRecord {
  user_id: string;
  step_id: string;
  completed_at: string;
  skipped: boolean;
  status_label: string;
}

/** A checklist item, including its derived display status. */
export interface ChecklistItem {
  id: string;
  label: string;
  detail: string;
  target: string;
  done: boolean;
  status: string;
}

/** The writable fields of a checklist item. */
export interface ChecklistItemInput {
  id: string;
  label: string;
  detail?: string;
  target?: string;
  done?: boolean;
}

/** A full setup checklist with derived counters. */
export interface Checklist {
  user_id: string;
  items: ChecklistItem[];
  completed: number;
  total: number;
  percent: number;
  updated_at: string;
}

/** The state of the resume banner. */
export interface ResumeState {
  can_resume: boolean;
  next_step_slug: string | null;
  percent: number;
  last_activity_at: string | null;
  message: string;
}

/** A generated note shown on the wizard landing screen. */
export interface WelcomeNote {
  id: string;
  user_id: string;
  title: string;
  body: string;
  tone: WelcomeTone;
  word_count: number;
  reading_seconds: number;
  created_at: string;
}

/** The aggregate progress payload consumed by the wizard. */
export interface ProgressSummary {
  user_id: string;
  status: "not-started" | "in-progress" | "complete" | "no-catalogue";
  total: number;
  completed: number;
  skipped: number;
  remaining: number;
  percent: number;
  checklist_percent: number;
  steps: OnboardingStep[];
  records: ProgressRecord[];
  next_step: OnboardingStep | null;
  checklist: Checklist;
  resume: ResumeState;
  welcome_note: WelcomeNote;
}

/** The response returned after completing or skipping a step. */
export interface StepActionResponse {
  step: OnboardingStep;
  message: string;
  finished: boolean;
  progress: ProgressSummary;
}

/** The response returned after resetting onboarding state. */
export interface ResetResponse {
  user_id: string;
  removed_progress: number;
  removed_checklist: boolean;
  message: string;
  checklist: Checklist;
  progress: ProgressSummary;
}

/** The result of validating a spotlight target. */
export interface TargetCheckResponse {
  target: string;
  valid: boolean;
  kind: string;
  reason: string;
  label: string;
}

/** A step paired with its position in the tour. */
export interface TourFrame {
  step: OnboardingStep;
  index: number;
  total: number;
  isFirst: boolean;
  isLast: boolean;
}
