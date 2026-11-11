import { useTheme } from "./hooks/useTheme";
import "./App.css";

/**
 * Root application shell.
 *
 * The full dashboard experience is assembled in the feature branches that
 * follow; this shell establishes the theme provider and the page frame.
 */
export function App() {
  const [theme] = useTheme();

  return (
    <div className="app-shell" data-theme={theme}>
      <header className="app-shell__header">
        <span className="app-shell__brand">CTF Team Dashboard</span>
      </header>
      <main className="app-shell__main">
        <h1>Competition overview</h1>
        <p>The dashboard modules are being assembled branch by branch.</p>
      </main>
    </div>
  );
}
