/**
 * Sign in screen for the dashboard.
 */

import { useState, type FormEvent } from "react";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "./useAuth";
import styles from "./LoginPage.module.css";

/** Props accepted by {@link LoginPage}. */
export interface LoginPageProps {
  /** Called after a successful sign in. */
  onSuccess?: () => void;
  /** Optional message shown above the form. */
  notice?: string;
}

/**
 * Render the authentication screen.
 *
 * @param props - The component props.
 * @returns The login screen element.
 */
export function LoginPage({ onSuccess, notice }: LoginPageProps) {
  const { login, error, status } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const busy = status === "loading";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    if (!username.trim() || !password) return;
    try {
      await login(username.trim(), password);
      onSuccess?.();
    } catch {
      // The error is surfaced through the auth state.
    }
  }

  return (
    <main className={styles.login}>
      <section className={styles.login__card} aria-labelledby="login-title">
        <div className={styles.login__brand}>
          <span className={styles.login__mark} aria-hidden="true">
            CTF
          </span>
          <div>
            <h1 className={styles.login__title} id="login-title">
              Team Dashboard
            </h1>
            <p className={styles.login__subtitle}>Sign in to track the competition</p>
          </div>
        </div>

        {notice ? (
          <p className={styles.login__error} role="status">
            <ShieldAlert size={16} aria-hidden="true" />
            {notice}
          </p>
        ) : null}

        <form className={styles.login__form} onSubmit={handleSubmit} noValidate>
          <div className={styles.login__field}>
            <label className={styles.login__label} htmlFor="login-username">
              Username or email
            </label>
            <input
              className={styles.login__input}
              id="login-username"
              name="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              aria-invalid={submitted && !username.trim() ? true : undefined}
            />
          </div>

          <div className={styles.login__field}>
            <label className={styles.login__label} htmlFor="login-password">
              Password
            </label>
            <input
              className={styles.login__input}
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              aria-invalid={submitted && !password ? true : undefined}
            />
          </div>

          {error ? (
            <p className={styles.login__error} role="alert">
              <ShieldAlert size={16} aria-hidden="true" />
              {error}
            </p>
          ) : null}

          <button className={styles.login__submit} type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className={styles.login__footer}>
          Access is restricted to registered team members. Contact your team lead to obtain
          credentials.
        </p>
      </section>
    </main>
  );
}
