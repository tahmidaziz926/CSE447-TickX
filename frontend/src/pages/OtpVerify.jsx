import { useState, useRef } from "react";
import Navbar from "../components/Navbar";
import "./AuthPage.css";

/**
 * OtpVerify.jsx — Step 2 of the auth flow.
 * Reads user_id from the URL (?user_id=...) set by Login.jsx, and on
 * success stores the returned session token and redirects in.
 *
 * For this project, the OTP is printed to the Flask console (see
 * auth/otp.py) instead of sent via real SMS/email.
 */
export default function OtpVerify() {
  const [digits, setDigits] = useState(["", "", "", "", "", ""]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const inputsRef = useRef([]);

  const params = new URLSearchParams(window.location.search);
  const userId = params.get("user_id");

  function handleChange(index, value) {
    if (!/^\d?$/.test(value)) return; // digits only, max 1 char
    const next = [...digits];
    next[index] = value;
    setDigits(next);

    if (value && index < 5) {
      inputsRef.current[index + 1]?.focus();
    }
  }

  function handleKeyDown(index, e) {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    const code = digits.join("");
    if (code.length !== 6) {
      setError("Enter the full 6-digit code.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/auth/otp/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, code }),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Invalid or expired code.");
        return;
      }

      localStorage.setItem("session_token", data.session_token);
      localStorage.setItem("role", data.role);
      window.location.href = "/";
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
          <h1>Verify it's you</h1>
          <p className="auth-card__sub">
            Enter the 6-digit code sent for your account.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="otp-inputs">
              {digits.map((digit, i) => (
                <input
                  key={i}
                  ref={(el) => (inputsRef.current[i] = el)}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  className="otp-inputs__box"
                  value={digit}
                  onChange={(e) => handleChange(i, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(i, e)}
                  aria-label={`Digit ${i + 1}`}
                />
              ))}
            </div>

            {error && <p className="field-error" role="alert">{error}</p>}

            <button type="submit" className="btn btn-primary auth-card__submit" disabled={loading}>
              {loading ? "Verifying…" : "Verify"}
            </button>
          </form>

          <p className="auth-card__footer">
            Didn't get a code? <a href="/login">Try logging in again</a>
          </p>
        </div>
      </main>
    </>
  );
}