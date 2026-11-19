/**
 * Overlay primitives: modal dialogs, drawers and tooltips.
 */

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";
import { IconButton } from "./Button";
import styles from "./Overlay.module.css";

/** Props accepted by {@link Modal}. */
export interface ModalProps {
  /** Whether the dialog is visible. */
  open: boolean;
  /** Called when the dialog requests to be closed. */
  onClose: () => void;
  /** The dialog title. */
  title?: ReactNode;
  /** The dialog description. */
  description?: ReactNode;
  /** The dialog body. */
  children?: ReactNode;
  /** The footer region of the dialog. */
  footer?: ReactNode;
  /** The width of the dialog. */
  size?: "sm" | "md" | "lg" | "xl";
  /** Hide the close button. */
  hideClose?: boolean;
  /** Prevent closing by clicking the backdrop. */
  persistent?: boolean;
}

/**
 * Trap the focus inside a container while it is open.
 *
 * @param container - The element that holds the focusable content.
 * @param active - Whether the trap is enabled.
 */
function useFocusTrap(
  container: React.RefObject<HTMLElement | null>,
  active: boolean,
): void {
  useEffect(() => {
    if (!active || !container.current) return;

    const selector =
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

    const focusables = () => {
      const node = container.current;
      if (!node) return [] as HTMLElement[];
      return Array.from(node.querySelectorAll<HTMLElement>(selector)).filter(
        (element) => element.offsetParent !== null,
      );
    };

    const previous = document.activeElement as HTMLElement | null;
    const first = focusables()[0];
    first?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) return;
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      if (event.shiftKey && document.activeElement === firstItem) {
        event.preventDefault();
        lastItem.focus();
      } else if (!event.shiftKey && document.activeElement === lastItem) {
        event.preventDefault();
        firstItem.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previous?.focus?.();
    };
  }, [container, active]);
}

/**
 * Render a modal dialog rendered in a portal.
 *
 * @param props - The component props.
 * @returns The dialog element, or `null` when closed.
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = "md",
  hideClose = false,
  persistent = false,
}: ModalProps) {
  const titleId = useId();
  const descriptionId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(panelRef, open);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !persistent) onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose, persistent]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div
      className={styles.backdrop}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !persistent) onClose();
      }}
    >
      <div
        ref={panelRef}
        className={cn(styles.modal, styles[`modal-${size}`])}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        aria-describedby={description ? descriptionId : undefined}
      >
        {title || !hideClose ? (
          <header className={styles.modalHeader}>
            <div>
              {title ? (
                <h2 className={styles.modalTitle} id={titleId}>
                  {title}
                </h2>
              ) : null}
              {description ? (
                <p className={styles.modalDescription} id={descriptionId}>
                  {description}
                </p>
              ) : null}
            </div>
            {hideClose ? null : (
              <IconButton
                icon={<X size={16} />}
                label="Close dialog"
                onClick={onClose}
              />
            )}
          </header>
        ) : null}

        <div className={styles.modalBody}>{children}</div>

        {footer ? (
          <footer className={styles.modalFooter}>{footer}</footer>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}

/** Props accepted by {@link Drawer}. */
export interface DrawerProps {
  /** Whether the drawer is visible. */
  open: boolean;
  /** Called when the drawer requests to be closed. */
  onClose: () => void;
  /** The drawer title. */
  title?: ReactNode;
  /** The drawer body. */
  children?: ReactNode;
  /** The footer region of the drawer. */
  footer?: ReactNode;
  /** Which edge the drawer slides in from. */
  side?: "left" | "right" | "bottom";
  /** The width of the drawer. */
  width?: number;
}

/**
 * Render a drawer panel sliding in from the edge of the viewport.
 *
 * @param props - The component props.
 * @returns The drawer element, or `null` when closed.
 */
export function Drawer({
  open,
  onClose,
  title,
  children,
  footer,
  side = "right",
  width = 420,
}: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(panelRef, open);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div
      className={styles.backdrop}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className={cn(styles.drawer, styles[`drawer-${side}`])}
        style={side === "bottom" ? undefined : { width }}
        role="dialog"
        aria-modal="true"
      >
        <header className={styles.drawerHeader}>
          <h2 className={styles.modalTitle}>{title}</h2>
          <IconButton
            icon={<X size={16} />}
            label="Close panel"
            onClick={onClose}
          />
        </header>
        <div className={styles.drawerBody}>{children}</div>
        {footer ? (
          <footer className={styles.drawerFooter}>{footer}</footer>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}

/** Props accepted by {@link Tooltip}. */
export interface TooltipProps {
  /** The tooltip content. */
  content: ReactNode;
  /** The element the tooltip is attached to. */
  children: ReactNode;
  /** Where the tooltip is rendered relative to the anchor. */
  side?: "top" | "bottom" | "left" | "right";
  /** Delay before the tooltip appears, in milliseconds. */
  delay?: number;
}

/**
 * Render a hover and focus tooltip.
 *
 * @param props - The component props.
 * @returns The wrapped element.
 */
export function Tooltip({
  content,
  children,
  side = "top",
  delay = 250,
}: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const timer = useRef<number | null>(null);

  const show = useCallback(() => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setVisible(true), delay);
  }, [delay]);

  const hide = useCallback(() => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    setVisible(false);
  }, []);

  useEffect(
    () => () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    },
    [],
  );

  return (
    <span
      className={styles.tooltipAnchor}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {visible ? (
        <span
          className={cn(styles.tooltip, styles[`tooltip-${side}`])}
          role="tooltip"
        >
          {content}
        </span>
      ) : null}
    </span>
  );
}

/** Props accepted by {@link Popover}. */
export interface PopoverProps {
  /** The trigger element. */
  trigger: ReactNode;
  /** The popover body. */
  children: ReactNode;
  /** Whether the popover is visible. */
  open: boolean;
  /** Called when the popover requests to be closed. */
  onClose: () => void;
  /** Which edge the popover is aligned to. */
  align?: "start" | "center" | "end";
}

/**
 * Render an anchored popover panel.
 *
 * @param props - The component props.
 * @returns The popover element.
 */
export function Popover({
  trigger,
  children,
  open,
  onClose,
  align = "start",
}: PopoverProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(event.target as Node)) onClose();
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);

  return (
    <div className={styles.popoverAnchor} ref={containerRef}>
      {trigger}
      {open ? (
        <div
          className={cn(styles.popover, styles[`popover-${align}`])}
          role="dialog"
        >
          {children}
        </div>
      ) : null}
    </div>
  );
}

/** Props accepted by {@link Menu}. */
export interface MenuProps extends HTMLAttributes<HTMLDivElement> {
  /** Whether the menu is visible. */
  open: boolean;
  /** The menu items. */
  children: ReactNode;
  /** The width of the menu. */
  width?: number;
}

/**
 * Render a dropdown menu panel.
 *
 * @param props - The component props.
 * @returns The menu element.
 */
export function Menu({
  open,
  children,
  width = 200,
  className,
  ...rest
}: MenuProps) {
  if (!open) return null;
  return (
    <div
      className={cn(styles.menu, className)}
      style={{ width }}
      role="menu"
      {...rest}
    >
      {children}
    </div>
  );
}

/** Props accepted by {@link MenuItem}. */
export interface MenuItemProps extends HTMLAttributes<HTMLButtonElement> {
  /** The icon rendered before the label. */
  icon?: ReactNode;
  /** Whether the item is destructive. */
  danger?: boolean;
  /** Whether the item is currently active. */
  active?: boolean;
}

/**
 * Render a single entry of a {@link Menu}.
 *
 * @param props - The component props.
 * @returns The menu item element.
 */
export function MenuItem({
  icon,
  danger = false,
  active = false,
  className,
  children,
  ...rest
}: MenuItemProps) {
  return (
    <button
      type="button"
      role="menuitem"
      className={cn(
        styles.menuItem,
        danger && styles.menuItemDanger,
        active && styles.menuItemActive,
        className,
      )}
      {...rest}
    >
      {icon ? (
        <span className={styles.menuIcon} aria-hidden="true">
          {icon}
        </span>
      ) : null}
      <span className={styles.menuLabel}>{children}</span>
    </button>
  );
}

/**
 * Render a separator between groups of menu items.
 *
 * @param props - The component props.
 * @returns The separator element.
 */
export function MenuDivider({
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(styles.menuDivider, className)}
      role="separator"
      {...rest}
    />
  );
}
