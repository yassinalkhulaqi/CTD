import { useEffect, useState } from "react";
import { ComponentShowcase } from "./components/ComponentShowcase";
import { StateShowcase } from "./components/StateShowcase";
import { ThemeToggle } from "./components/ui";
import { LoginPage } from "./features/auth/LoginPage";
import { fetchAuthConfig } from "./features/auth/api";
import { useAuth } from "./features/auth/useAuth";
import "./App.css";

/**
 * Root application shell.
 *
 * The full dashboard experience is assembled in the feature branches that
 * follow; this shell wires the authentication gate established by the auth
 * branch so the dashboard is only exposed to authenticated operators.
 */
export function App() {
  const { isAuthenticated, status } = useAuth();
  const [authEnabled, setAuthEnabled] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetchAuthConfig()
      .then((config) => {
        if (!cancelled) setAuthEnabled(config.enabled);
      })
      .catch(() => {
        if (!cancelled) setAuthEnabled(false);
      })
      .finally(() => {
        if (!cancelled) setChecked(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!checked) {
    return <main className="app-shell__main">Loading the dashboard…</main>;
  }

  if (authEnabled && !isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <span className="app-shell__brand">
          <span className="app-shell__mark" aria-hidden="true">
            CTF
          </span>
          CTF Team Dashboard
        </span>
        <ThemeToggle />
      </header>
      <main className="app-shell__main">
        {status === "authenticated" ? <ComponentShowcase /> : <StateShowcase />}
      </main>
    </div>
  );
}
