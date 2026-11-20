/** Global command palette with grouped commands and keyboard navigation. */

import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { createPortal } from "react-dom";
import { CornerDownLeft, Search, X } from "lucide-react";
import { filterCommands, groupCommands } from "../searchUtils";
import type { Command } from "../types";
import { Highlight } from "./Highlight";
import { ShortcutBadge } from "./ShortcutBadge";
import styles from "./CommandPalette.module.css";

/** Props accepted by {@link CommandPalette}. */
export interface CommandPaletteProps {
  /** Whether the palette is visible. */
  open: boolean;
  /** The available commands. */
  commands: Command[];
  /** Invoked when the palette requests to close. */
  onClose: () => void;
  /** Invoked when a command is selected. */
  onExecute: (command: Command) => void;
}

/**
 * Render the modal command palette as a portal on the document body.
 *
 * @param props - The component props.
 * @returns The palette element, or `null` when closed.
 */
export function CommandPalette({
  open,
  commands,
  onClose,
  onExecute,
}: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const titleId = useId();

  const filtered = useMemo(
    () => filterCommands(commands, query),
    [commands, query],
  );
  const grouped = useMemo(() => groupCommands(filtered), [filtered]);
  const flat = useMemo(() => Object.values(grouped).flat(), [grouped]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActiveIndex(0);
    inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  if (!open) return null;

  function execute(command: Command | undefined) {
    if (!command) return;
    onExecute(command);
    onClose();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => (flat.length ? (index + 1) % flat.length : 0));
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) =>
        flat.length ? (index - 1 + flat.length) % flat.length : 0,
      );
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      execute(flat[activeIndex]);
    }
  }

  return createPortal(
    <div
      className={styles.overlay}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={handleKeyDown}
      >
        <h2 className={styles.srOnly} id={titleId}>
          Command palette
        </h2>
        <div className={styles.inputRow}>
          <Search size={18} aria-hidden="true" className={styles.searchIcon} />
          <input
            ref={inputRef}
            className={styles.input}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search commands or type a filter…"
            aria-label="Search commands"
            autoComplete="off"
            spellCheck={false}
          />
          <ShortcutBadge shortcut="Esc" />
          <button
            type="button"
            className={styles.close}
            onClick={onClose}
            aria-label="Close command palette"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        <div className={styles.results} role="listbox" aria-label="Commands">
          {flat.length === 0 ? (
            <p className={styles.noMatches}>No commands match “{query}”.</p>
          ) : (
            Object.entries(grouped).map(([group, items]) => (
              <section className={styles.group} key={group}>
                <h3 className={styles.groupLabel}>{group}</h3>
                {items.map((command) => {
                  const index = flat.indexOf(command);
                  return (
                    <button
                      type="button"
                      role="option"
                      aria-selected={index === activeIndex}
                      data-index={index}
                      key={command.id}
                      className={
                        index === activeIndex
                          ? styles.optionActive
                          : styles.option
                      }
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => execute(command)}
                    >
                      <span className={styles.optionText}>
                        <span className={styles.name}>
                          <Highlight text={command.name} query={query} />
                        </span>
                        <span className={styles.description}>
                          <Highlight text={command.description} query={query} />
                        </span>
                      </span>
                      <ShortcutBadge shortcut={command.shortcut} />
                      {index === activeIndex ? (
                        <CornerDownLeft size={14} aria-hidden="true" />
                      ) : null}
                    </button>
                  );
                })}
              </section>
            ))
          )}
        </div>

        <footer className={styles.footer}>
          <span>
            <kbd>↑</kbd>
            <kbd>↓</kbd> navigate
          </span>
          <span>
            <kbd>Enter</kbd> run
          </span>
          <span>
            <kbd>Esc</kbd> close
          </span>
          <span className={styles.count}>{flat.length} commands</span>
        </footer>
      </div>
    </div>,
    document.body,
  );
}
