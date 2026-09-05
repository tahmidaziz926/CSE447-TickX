import { useState } from "react";
import Navbar from "../components/Navbar";
import "./AuthPage.css";

/**
 * Register.jsx — Buyer/Seller registration.
 * Sends personal_info fields that the backend RSA-encrypts before
 * storage (Section 1.1/1.2 of the requirements).
 */
export default function Register() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    role: "BUYER",
    name: "",
    phone: "",
    address: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (form.password !== form.confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.email,
          password: form.password,
          role: form.role,
          personal_info: {
            name: form.name,
            phone: form.phone,
            address: form.address,
          },
        }),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Registration failed. Try again.");
        return;
      }

      window.location.href = "/login";
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
        <div className="ticket-card auth-card auth-card--wide">
          <h1>Create your account</h1>
          <p className="auth-card__sub">
            Join TixCrypt to buy tickets or sell events securely.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="role-toggle" role="radiogroup" aria-label="Account type">
              {["BUYER", "SELLER"].map((r) => (
                <button
                  type="button"
                  key={r}
                  role="radio"
                  aria-checked={form.role === r}
                  className={`role-toggle__option ${form.role === r ? "role-toggle__option--active" : ""}`}
                  onClick={() => update("role", r)}
                >
                  {r === "BUYER" ? "I'm attending events" : "I'm selling events"}
                </button>
              ))}
            </div>

            <div className="field">
              <label htmlFor="name">Full name</label>
              <input
                id="name"
                value={form.name}
                onChange={(e) => update("name", e.target.value)}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="reg-email">Email</label>
              <input
                id="reg-email"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="phone">Phone number</label>
              <input
                id="phone"
                type="tel"
                value={form.phone}
                onChange={(e) => update("phone", e.target.value)}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="address">
                {form.role === "SELLER" ? "Organization address" : "Address"}
              </label>
              <input
                id="address"
                value={form.address}
                onChange={(e) => update("address", e.target.value)}
                required
              />
            </div>

            <div className="field-row">
              <div className="field">
                <label htmlFor="reg-password">Password</label>
                <input
                  id="reg-password"
                  type="password"
                  autoComplete="new-password"
                  value={form.password}
                  onChange={(e) => update("password", e.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="confirm-password">Confirm password</label>
                <input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  value={form.confirmPassword}
                  onChange={(e) => update("confirmPassword", e.target.value)}
                  required
                />
              </div>
            </div>

            {error && <p className="field-error" role="alert">{error}</p>}

            {form.role === "SELLER" && (
              <p className="auth-card__notice">
                Seller accounts require admin approval before you can publish events.
              </p>
            )}

            <button type="submit" className="btn btn-primary auth-card__submit" disabled={loading}>
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p className="auth-card__footer">
            Already have an account? <a href="/login">Log in</a>
          </p>
        </div>
      </main>
    </>
  );
}