import { useState, useEffect } from "react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import "./AuthPage.css";

/**
 * Profile.jsx — Sections 2.1/3.1: view and update profile.
 * Works for both BUYER and SELLER (same fields, same backend logic).
 */
export default function Profile() {
  const { isAuthenticated, role, logout, token } = useAuth();
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({ name: "", phone: "", address: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    async function fetchProfile() {
      try {
        const res = await fetch("/api/auth/profile", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (!res.ok) {
          setError(data.error || "Couldn't load profile.");
          return;
        }
        setProfile(data);
        setForm({ name: data.name || "", phone: data.phone || "", address: data.address || "" });
      } catch {
        setError("Couldn't reach the server.");
      } finally {
        setLoading(false);
      }
    }
    fetchProfile();
  }, [token]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    setSuccess(false);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const res = await fetch("/api/auth/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Couldn't update profile.");
        return;
      }
      setProfile(data);
      setSuccess(true);
    } catch {
      setError("Couldn't reach the server.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Navbar isAuthenticated={isAuthenticated} userRole={role} onLogout={logout} />

      <main className="auth-page">
        <div className="ticket-card auth-card">
          <h1>Your profile</h1>
          <p className="auth-card__sub">
            Personal info is RSA-encrypted at rest and integrity-protected with a MAC.
          </p>

          {loading ? (
            <p>Loading…</p>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="field">
                <label>Email</label>
                <input value={profile?.email || ""} disabled />
              </div>
              <div className="field">
                <label htmlFor="name">Full name</label>
                <input id="name" value={form.name} onChange={(e) => update("name", e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="phone">Phone number</label>
                <input id="phone" value={form.phone} onChange={(e) => update("phone", e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="address">Address</label>
                <input id="address" value={form.address} onChange={(e) => update("address", e.target.value)} />
              </div>

              {error && <p className="field-error" role="alert">{error}</p>}
              {success && <p className="auth-card__notice">Profile updated successfully.</p>}

              <button type="submit" className="btn btn-primary auth-card__submit" disabled={saving}>
                {saving ? "Saving…" : "Save changes"}
              </button>
            </form>
          )}
        </div>
      </main>
    </>
  );
}