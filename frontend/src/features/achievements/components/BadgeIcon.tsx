/**
 * Map a badge icon token onto a lucide icon component.
 */

import {
  Award,
  Brain,
  Calendar,
  Crown,
  Flame,
  Gem,
  Grid,
  HelpCircle,
  Layers,
  Lightbulb,
  Lock,
  Moon,
  Shield,
  Sparkles,
  Swords,
  Target,
  Trophy,
  type LucideIcon,
} from "lucide-react";

/** Icons keyed by the tokens stored in the badge catalogue. */
const ICONS: Record<string, LucideIcon> = {
  award: Award,
  bolt: Flame,
  brain: Brain,
  calendar: Calendar,
  "calendar-days": Calendar,
  "circle-help": HelpCircle,
  crosshair: Target,
  crown: Crown,
  flame: Flame,
  gem: Gem,
  grid: Grid,
  "grid-2x2": Grid,
  layers: Layers,
  lightbulb: Lightbulb,
  lock: Lock,
  moon: Moon,
  "question-mark": HelpCircle,
  shield: Shield,
  sparkles: Sparkles,
  star: Sparkles,
  sun: Sparkles,
  swords: Swords,
  target: Target,
  trophy: Trophy,
};

/** Props accepted by {@link BadgeIcon}. */
export interface BadgeIconProps {
  /** Token stored on the badge definition. */
  token: string;
  /** Icon size in pixels. */
  size?: number;
  /** Additional class name. */
  className?: string;
}

/**
 * Render the icon associated with a badge token.
 *
 * @param props - The component props.
 * @returns The icon element.
 */
export function BadgeIcon({ token, size = 28, className }: BadgeIconProps) {
  const Icon = ICONS[token] ?? Trophy;
  return <Icon size={size} className={className} aria-hidden="true" />;
}
