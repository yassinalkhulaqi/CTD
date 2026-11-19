import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "./app/AppShell";
import { buildRoutes } from "./app/routes";
import { ConnectionBadge } from "./components/realtime/ConnectionBadge";
import { ThemeToggle } from "./components/ui";
import { LoginPage } from "./features/auth/LoginPage";
import { fetchAuthConfig } from "./features/auth/api";
import { useAuth } from "./features/auth/useAuth";
import { RealtimeProvider } from "./realtime/RealtimeProvider";
import "./App.css";

/**
 * Root application component.
 *
 * The router, the theme provider and the authentication gate are assembled
 * here so the rest of the application only deals with routing and data.
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

  const routes = buildRoutes();

  return (
    <RealtimeProvider>
      <BrowserRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <div className="app-shell">
          <header className="app-shell__header">
            <span className="app-shell__brand">
              <span className="app-shell__mark" aria-hidden="true">
                CTF
              </span>
              CTF Team Dashboard
            </span>
            <div className="app-shell__headerActions">
              <span className="app-shell__status" data-status={status}>
                {status === "authenticated" ? "live" : "open mode"}
              </span>
              <ConnectionBadge />
              <ThemeToggle />
            </div>
          </header>
          <Routes>
            <Route element={<AppShell />}>
              {routes.map((route) => (
                <Route
                  key={route.path}
                  path={route.path}
                  element={route.element}
                />
              ))}
            </Route>
          </Routes>
        </div>
      </BrowserRouter>
    </RealtimeProvider>
  );
}
