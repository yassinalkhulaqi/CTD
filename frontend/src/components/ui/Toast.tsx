/**
 * Toast notifications with a provider and a headless hook.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";
import { cn } from "../../lib/utils";
import styles from "./Toast.module.css";

/** The severity of a toast notification. */
export type ToastTone = "info" | "success" | "warning" | "error";

/** A toast notification. */
export interface Toast {
  /** Unique identifier of the toast. */
  id: string;
  /** The severity of the toast. */
  tone: ToastTone;
  /** The headline of the toast. */
  title: string;
  /** Optional supporting copy. */
  description?: string;
  /** Milliseconds before the toast is dismissed automatically. */
  duration: number;
}

/** Options accepted when pushing a toast. */
export interface ToastOptions {
  /** The severity of the toast. */
  tone?: ToastTone;
  /** Optional supporting copy. */
  description?: string;
  /** Milliseconds before the toast is dismissed automatically. */
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  push: (title: string, options?: ToastOptions) => string;
  dismiss: (id: string) => void;
  clear: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

/**
 * Read the toast context.
 *
 * @returns The toast context.
 * @throws When used outside of a {@link ToastProvider}.
 */
export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used inside a <ToastProvider>");
  }
  return context;
}

const TONE_ICONS: Record<ToastTone, ReactNode> = {
  info: <Info size={16} aria-hidden="true" />,
  success: <CheckCircle2 size={16} aria-hidden="true" />,
  warning: <AlertTriangle size={16} aria-hidden="true" />,
  error: <XCircle size={16} aria-hidden="true" />,
};

/** Props accepted by {@link ToastProvider}. */
export interface ToastProviderProps {
  /** The application tree the provider wraps. */
  children: ReactNode;
  /** The maximum number of visible toasts. */
  max?: number;
  /** The default lifetime of a toast in milliseconds. */
  defaultDuration?: number;
}

/**
 * Provide the toast context to the application tree.
 *
 * @param props - The component props.
 * @returns The provider element.
 */
export function ToastProvider({
  children,
  max = 4,
  defaultDuration = 5000,
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counter = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (title: string, options: ToastOptions = {}) => {
      counter.current += 1;
      const id = `toast-${counter.current}`;
      const toast: Toast = {
        id,
        tone: options.tone ?? "info",
        title,
        description: options.description,
        duration: options.duration ?? defaultDuration,
      };
      setToasts((current) => [...current, toast].slice(-max));
      if (toast.duration > 0) {
        window.setTimeout(() => dismiss(id), toast.duration);
      }
      return id;
    },
    [defaultDuration, dismiss, max],
  );

  const clear = useCallback(() => setToasts([]), []);

  const value = useMemo<ToastContextValue>(
    () => ({ toasts, push, dismiss, clear }),
    [toasts, push, dismiss, clear],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastViewport />
    </ToastContext.Provider>
  );
}

/**
 * Render the toast viewport.
 *
 * @returns The viewport element.
 */
export function ToastViewport() {
  const { toasts, dismiss } = useToast();

  if (typeof document === "undefined") return null;

  return createPortal(
    <div className={styles.viewport} role="region" aria-label="Notifications">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(styles.toast, styles[`toast-${toast.tone}`])}
          role={toast.tone === "error" ? "alert" : "status"}
          aria-live={toast.tone === "error" ? "assertive" : "polite"}
        >
          <span className={styles.toastIcon}>{TONE_ICONS[toast.tone]}</span>
          <div className={styles.toastBody}>
            <p className={styles.toastTitle}>{toast.title}</p>
            {toast.description ? (
              <p className={styles.toastDescription}>{toast.description}</p>
            ) : null}
          </div>
          <button
            type="button"
            className={styles.toastClose}
            onClick={() => dismiss(toast.id)}
            aria-label="Dismiss notification"
          >
            <X size={14} aria-hidden="true" />
          </button>
        </div>
      ))}
    </div>,
    document.body,
  );
}

/**
 * Run a callback when the component unmounts, used to cancel pending timers.
 *
 * @param callback - The cleanup callback.
 */
export function useUnmount(callback: () => void): void {
  const ref = useRef(callback);
  ref.current = callback;

  useEffect(
    () => () => {
      ref.current();
    },
    [],
  );
}
