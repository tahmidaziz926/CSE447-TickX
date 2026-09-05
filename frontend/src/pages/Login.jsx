import { useState } from "react";
import Navbar from "../components/Navbar";
import "./AuthPage.css";

/**
 * Login.jsx — Step 1 of the auth flow (password check).
 * On success, the backend sends an OTP and this page hands off
 * to OtpVerify.jsx with the returned user_id.
 */
export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Something went wrong. Try again.");
        return;
      }

      // Hand off to OTP step
      window.location.href = `/otp-verify?user_id=${data.user_id}`;
    } catch (err) {
      setError("Couldn't reach the server. Check your connection.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Navbar isAuthenticated={false} />

      <main className="auth-page">
        <div className="ticket-card auth-card">
          <h1>Welcome back</h1>
          <p className="auth-card__sub">Log in to manage your tickets and events.</p>

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && <p className="field-error" role="alert">{error}</p>}

            <button type="submit" className="btn btn-primary auth-card__submit" disabled={loading}>
              {loading ? "Checking…" : "Continue"}
            </button>
          </form>

          <p className="auth-card__footer">
            New to TixCrypt? <a href="/register">Create an account</a>
          </p>
        </div>
      </main>
    </>
  );
}