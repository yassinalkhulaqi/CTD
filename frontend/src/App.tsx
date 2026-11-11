import { useEffect, useState } from "react";
import { LoginPage } from "./features/auth/LoginPage";
import { fetchAuthConfig } from "./features/auth/api";
import { useAuth } from "./features/auth/useAuth";

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
        <span className="app-shell__brand">CTF Team Dashboard</span>
      </header>
      <main className="app-shell__main">
        <h1>Competition overview</h1>
        <p>
          {status === "authenticated"
            ? "The dashboard modules are being assembled branch by branch."
            : "The dashboard is running in open mode."}
        </p>
      </main>
    </div>
  );
}
