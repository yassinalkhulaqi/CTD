import type {
  A11yIssue,
  ContrastLevel,
  FocusOrderEntry,
  IssueFilters,
  Shortcut,
  ShortcutConflict,
} from "./types";

type RGB = [number, number, number];

export interface ContrastEvaluation {
  valid: boolean;
  foreground: string;
  background: string;
  ratio: number;
  passesAa: boolean;
  passesAaa: boolean;
  level: ContrastLevel;
  suggestion: string;
  error?: string;
}

export interface FocusTrapState {
  entries: FocusOrderEntry[];
  index: number;
}

const HEX_COLOUR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;
const RGB_COLOUR = /^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/i;

const COLOUR_ALIASES: Record<string, string> = {
  black: "#000000",
  white: "#ffffff",
  gray: "#808080",
  grey: "#808080",
  red: "#ff0000",
  green: "#008000",
  blue: "#0000ff",
  yellow: "#ffff00",
  orange: "#ffa500",
  navy: "#000080",
};

const KEY_ALIASES: Record<string, string> = {
  control: "ctrl",
  option: "alt",
  cmd: "meta",
  command: "meta",
  windows: "meta",
  esc: "escape",
  return: "enter",
  del: "delete",
  spacebar: "space",
  plus: "+",
};

const MODIFIER_ORDER = ["ctrl", "alt", "shift", "meta"];
const GLOBAL_SCOPES = new Set(["global", "*", "all"]);

const DISPLAY_NAMES: Record<string, string> = {
  ctrl: "Ctrl",
  alt: "Alt",
  shift: "Shift",
  meta: "Meta",
  escape: "Esc",
  enter: "Enter",
  delete: "Del",
  space: "Space",
  "+": "+",
};

const GENERIC_LABELS = new Set([
  "button",
  "click here",
  "here",
  "link",
  "ok",
  "submit",
  "text field",
  "untitled",
]);

export function parseColor(input: string): RGB {
  const raw = input.trim().toLowerCase();
  const value = COLOUR_ALIASES[raw] ?? raw;
  if (HEX_COLOUR.test(value)) {
    const digits = value.slice(1);
    const expanded =
      digits.length === 3
        ? digits
            .split("")
            .map((digit) => digit + digit)
            .join("")
        : digits;
    return [
      parseInt(expanded.slice(0, 2), 16),
      parseInt(expanded.slice(2, 4), 16),
      parseInt(expanded.slice(4, 6), 16),
    ];
  }
  const match = RGB_COLOUR.exec(value);
  if (match) {
    const channels: RGB = [
      Number(match[1]),
      Number(match[2]),
      Number(match[3]),
    ];
    if (channels.every((channel) => channel >= 0 && channel <= 255)) {
      return channels;
    }
  }
  throw new Error(`${input} is not a supported colour`);
}

export function normaliseColor(input: string): string {
  const [red, green, blue] = parseColor(input);
  return `#${red.toString(16).padStart(2, "0")}${green.toString(16).padStart(2, "0")}${blue
    .toString(16)
    .padStart(2, "0")}`;
}

function linearise(channel: number): number {
  const value = channel / 255;
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(colour: string | RGB): number {
  const [red, green, blue] =
    typeof colour === "string" ? parseColor(colour) : colour;
  return (
    0.2126 * linearise(red) +
    0.7152 * linearise(green) +
    0.0722 * linearise(blue)
  );
}

export function contrastRatio(foreground: string, background: string): number {
  const first = relativeLuminance(foreground);
  const second = relativeLuminance(background);
  const lighter = Math.max(first, second);
  const darker = Math.min(first, second);
  return Math.round(((lighter + 0.05) / (darker + 0.05)) * 100) / 100;
}

export function contrastThresholds(largeText: boolean): [number, number] {
  return largeText ? [3, 4.5] : [4.5, 7];
}

export function classifyContrast(
  ratio: number,
  largeText: boolean,
): ContrastLevel {
  const [aa, aaa] = contrastThresholds(largeText);
  if (ratio >= aaa) return "aaa";
  if (ratio >= aa) return "aa";
  return "fail";
}

export function contrastSuggestion(
  foreground: string,
  background: string,
  largeText: boolean,
  ratio = contrastRatio(foreground, background),
): string {
  const [aa] = contrastThresholds(largeText);
  if (ratio >= aa) {
    return `This pair meets WCAG AA at ${ratio.toFixed(2)}:1; preserve it in the theme.`;
  }
  const direction =
    relativeLuminance(foreground) >= relativeLuminance(background)
      ? "darken the foreground or lighten the background"
      : "lighten the foreground or darken the background";
  const size = largeText ? "large text" : "body text";
  return `Reach at least ${aa.toFixed(1)}:1 for ${size}: ${direction}.`;
}

export function evaluateContrast(
  foreground: string,
  background: string,
  largeText: boolean,
): ContrastEvaluation {
  try {
    const first = normaliseColor(foreground);
    const second = normaliseColor(background);
    const ratio = contrastRatio(first, second);
    const [aa, aaa] = contrastThresholds(largeText);
    return {
      valid: true,
      foreground: first,
      background: second,
      ratio,
      passesAa: ratio >= aa,
      passesAaa: ratio >= aaa,
      level: classifyContrast(ratio, largeText),
      suggestion: contrastSuggestion(first, second, largeText, ratio),
    };
  } catch (error) {
    return {
      valid: false,
      foreground,
      background,
      ratio: 0,
      passesAa: false,
      passesAaa: false,
      level: "fail",
      suggestion:
        "Enter a hex colour, an rgb() expression or a supported colour name.",
      error: error instanceof Error ? error.message : "Invalid colour",
    };
  }
}

export function parseShortcut(raw: string): string[] {
  const compact = raw.trim().replace(/\s*\+\s*/g, "+");
  if (!compact) throw new Error("shortcut keys must not be empty");
  return compact.split(/\s+/).map((token) => {
    const parts = token
      .split("+")
      .map((part) => part.trim().toLowerCase())
      .filter(Boolean)
      .map((part) => KEY_ALIASES[part] ?? part);
    const modifiers: string[] = [];
    let key = "";
    for (const part of parts) {
      if (MODIFIER_ORDER.includes(part)) {
        if (modifiers.includes(part)) {
          throw new Error(`duplicate modifier ${part} in shortcut`);
        }
        modifiers.push(part);
      } else if (key) {
        throw new Error(`shortcut step ${token} has multiple keys`);
      } else {
        key = part;
      }
    }
    if (!key) throw new Error(`shortcut step ${token} has no key`);
    const ordered = MODIFIER_ORDER.filter((modifier) =>
      modifiers.includes(modifier),
    );
    return [...ordered, key].join("+");
  });
}

export function canonicalShortcut(raw: string): string {
  return parseShortcut(raw).join(" ");
}

export function displayShortcut(raw: string): string {
  return parseShortcut(raw)
    .map((step) =>
      step
        .split("+")
        .map((part) => DISPLAY_NAMES[part] ?? part.toUpperCase())
        .join("+"),
    )
    .join(" ");
}

function isGlobalScope(scope: string): boolean {
  return GLOBAL_SCOPES.has(scope.trim().toLowerCase());
}

export function shortcutsConflict(left: Shortcut, right: Shortcut): boolean {
  if (left.canonical_keys !== right.canonical_keys) return false;
  return (
    isGlobalScope(left.scope) ||
    isGlobalScope(right.scope) ||
    left.scope === right.scope
  );
}

export function findShortcutConflicts(
  shortcuts: Shortcut[],
): ShortcutConflict[] {
  const conflicts: ShortcutConflict[] = [];
  for (let index = 0; index < shortcuts.length; index += 1) {
    for (let other = index + 1; other < shortcuts.length; other += 1) {
      const left = shortcuts[index];
      const right = shortcuts[other];
      if (!shortcutsConflict(left, right)) continue;
      conflicts.push({
        description: `${left.display_keys} is bound to ${left.action} and ${right.action}`,
        left_id: left.id,
        right_id: right.id,
        keys: left.canonical_keys,
      });
    }
  }
  return conflicts;
}

export function createFocusTrap(
  entries: FocusOrderEntry[],
  index = 0,
): FocusTrapState {
  const ordered = [...entries].sort(
    (left, right) =>
      left.order - right.order || left.id.localeCompare(right.id),
  );
  const safeIndex =
    ordered.length === 0 ? 0 : Math.max(0, Math.min(index, ordered.length - 1));
  return { entries: ordered, index: safeIndex };
}

export function currentFocus(state: FocusTrapState): FocusOrderEntry | null {
  return state.entries[state.index] ?? null;
}

export function moveFocus(
  state: FocusTrapState,
  direction: "next" | "previous",
  wrap = true,
): FocusTrapState {
  if (state.entries.length === 0) return state;
  const delta = direction === "next" ? 1 : -1;
  const target = state.index + delta;
  if (!wrap && (target < 0 || target >= state.entries.length)) return state;
  return {
    ...state,
    index: (target + state.entries.length) % state.entries.length,
  };
}

export function focusAt(state: FocusTrapState, id: string): FocusTrapState {
  const index = state.entries.findIndex((entry) => entry.id === id);
  return index === -1 ? state : { ...state, index };
}

const SEVERITY_RANK: Record<A11yIssue["severity"], number> = {
  critical: 3,
  warning: 2,
  info: 1,
};

export function sortIssues(issues: A11yIssue[]): A11yIssue[] {
  return [...issues].sort((left, right) => {
    const severity =
      SEVERITY_RANK[right.severity] - SEVERITY_RANK[left.severity];
    if (severity !== 0) return severity;
    const resolved = Number(left.is_resolved) - Number(right.is_resolved);
    if (resolved !== 0) return resolved;
    return right.detected_at.localeCompare(left.detected_at);
  });
}

export function filterIssues(
  issues: A11yIssue[],
  filters: IssueFilters,
): A11yIssue[] {
  const query = filters.query.trim().toLowerCase();
  return sortIssues(
    issues.filter((issue) => {
      if (filters.severity !== "all" && issue.severity !== filters.severity)
        return false;
      if (!filters.includeResolved && issue.is_resolved) return false;
      if (!query) return true;
      return [
        issue.description,
        issue.path,
        issue.rule_id,
        issue.suggestion,
      ].some((value) => value.toLowerCase().includes(query));
    }),
  );
}

export function severityTone(
  severity: A11yIssue["severity"],
): "info" | "warning" | "danger" {
  return severity === "critical" ? "danger" : severity;
}

export function suggestAriaLabel(
  text: string,
  context = "",
  action = "",
): string {
  const description = text.trim().replace(/\s+/g, " ");
  const scope = context.trim().replace(/\s+/g, " ");
  const verb = action.trim().replace(/\s+/g, " ");
  let suggestion: string;
  if (!description || GENERIC_LABELS.has(description.toLowerCase())) {
    if (verb && scope) suggestion = `${verb} ${scope}`;
    else if (scope) suggestion = `Open ${scope}`;
    else if (verb) suggestion = `${verb} control`;
    else suggestion = "Describe this control";
  } else {
    suggestion = description;
    if (scope && !suggestion.toLowerCase().includes(scope.toLowerCase())) {
      suggestion = `${suggestion} for ${scope}`;
    }
    if (verb && !suggestion.toLowerCase().includes(verb.toLowerCase())) {
      suggestion = `${verb} ${suggestion}`;
    }
  }
  suggestion = suggestion.replace(/\s+/g, " ").replace(/[ .]+$/, "");
  if (!suggestion) return "Describe this control";
  if (suggestion.length > 160) suggestion = `${suggestion.slice(0, 159)}…`;
  return suggestion.charAt(0).toUpperCase() + suggestion.slice(1);
}

export function formatRatio(ratio: number): string {
  return `${ratio.toFixed(2)}:1`;
}
