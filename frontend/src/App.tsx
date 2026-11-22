import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "./app/AppShell";
import { buildRoutes } from "./app/routes";
import { ShieldCheck } from "lucide-react";
import { Spinner } from "./components/ui";
import { LoginPage } from "./features/auth/LoginPage";
import { fetchAuthConfig } from "./features/auth/api";
import { useAuth } from "./features/auth/useAuth";
import { RealtimeProvider } from "./realtime/RealtimeProvider";
import styles from "./App.module.css";

/**
 * Root application component.
 *
 * The router, the theme provider and the authentication gate are assembled
 * here so the rest of the application only deals with routing and data.
 */
export function App() {
  const { isAuthenticated } = useAuth();
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
    return (
      <main className={styles.boot} aria-busy="true" aria-live="polite">
        <div className={styles.bootCard}>
          <span className={styles.bootMark} aria-hidden="true">
            <ShieldCheck size={20} />
          </span>
          <div className={styles.bootText}>
            <span className={styles.bootName}>CTF Team Dashboard</span>
            <span className={styles.bootMeta}>Preparing your workspace…</span>
          </div>
          <Spinner size={16} label="Loading the dashboard" />
        </div>
      </main>
    );
  }

  if (authEnabled && !isAuthenticated) {
    return <LoginPage />;
  }

  const routes = buildRoutes();

  return (
    <RealtimeProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route element={<AppShell />}>
            {routes.map((route) => (
              <Route key={route.path} path={route.path} element={route.element} />
            ))}
          </Route>
        </Routes>
      </BrowserRouter>
    </RealtimeProvider>
  );
}
