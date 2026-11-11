/**
 * Theme switcher control wired to the global theme hook.
 */

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme, type Theme } from "../../hooks/useTheme";
import { cn } from "../../lib/utils";
import { SegmentedControl, type SegmentOption } from "./Tabs";
import styles from "./ThemeToggle.module.css";

const OPTIONS: SegmentOption<Theme>[] = [
  { value: "light", label: "Light", icon: <Sun size={13} /> },
  { value: "dark", label: "Dark", icon: <Moon size={13} /> },
  { value: "system", label: "Auto", icon: <Monitor size={13} /> },
];

/** Props accepted by {@link ThemeToggle}. */
export interface ThemeToggleProps {
  /** Additional class applied to the container. */
  className?: string;
}

/**
 * Render the light, dark and system theme switcher.
 *
 * @param props - The component props.
 * @returns The control element.
 */
export function ThemeToggle({ className }: ThemeToggleProps) {
  const [theme, setTheme] = useTheme();

  return (
    <div className={cn(styles.toggle, className)}>
      <SegmentedControl
        options={OPTIONS}
        value={theme}
        onValueChange={setTheme}
        label="Colour theme"
      />
    </div>
  );
}
