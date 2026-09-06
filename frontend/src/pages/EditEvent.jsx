import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import "./AuthPage.css";
import "./CreateEvent.css";

/**
 * EditEvent.jsx — Section 3.3: seller updates own event.
 * ManageEvents.jsx already links here (/dashboard/events/:id/edit) —
 * this page was referenced but never built until now.
 * Backend PUT /api/events/<id> already exists (events/routes.py) and
 * re-signs the event with ECC if critical fields changed.
 */
export default function EditEvent() {
  const { eventId } = useParams();
  const { isAuthenticated, role, logout, token } = useAuth();
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    async function fetchEvent() {
      try {
        const res = await fetch(`/api/events/${eventId}`);
        const data = await res.json();
        if (!res.ok) {
          setError(data.error || "Event not found.");
          return;
        }
        setForm({
          name: data.name,
          category: data.category,
          date_time: data.date_time,
          venue: data.venue,
          description: data.description || "",
          ticket_price: data.ticket_price,
          total_seats: data.total_seats,
        });
      } catch {
        setError("Couldn't reach the server.");
      } finally {
        setLoading(false);
      }
    }
    fetchEvent();
  }, [eventId]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const res = await fetch(`/api/events/${eventId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...form,
          ticket_price: parseFloat(form.ticket_price),
          total_seats: parseInt(form.total_seats, 10),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Couldn't update event.");
        return;
      }
      setSuccess(true);
      setTimeout(() => { window.location.href = "/dashboard/events"; }, 1000);
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
        <div className="ticket-card auth-card auth-card--wide">
          <h1>Edit event</h1>
          <p className="auth-card__sub">
            Changing name, category, date, venue, or price re-signs the event with your ECC key.
          </p>

          {loading ? (
            <p>Loading…</p>
          ) : success ? (
            <p className="create-event__success">Event updated — redirecting…</p>
          ) : !form ? (
            <p className="field-error">{error}</p>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="field">
                <label htmlFor="name">Event name</label>
                <input id="name" value={form.name} onChange={(e) => update("name", e.target.value)} required />
              </div>

              <div className="field-row">
                <div className="field">
                  <label htmlFor="category">Category</label>
                  <select id="category" value={form.category} onChange={(e) => update("category", e.target.value)}>
                    <option>Music</option>
                    <option>Sports</option>
                    <option>Theatre</option>
                    <option>Conference</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="date_time">Date &amp; time</label>
                  <input id="date_time" type="datetime-local" value={form.date_time} onChange={(e) => update("date_time", e.target.value)} required />
                </div>
              </div>

              <div className="field">
                <label htmlFor="venue">Venue</label>
                <input id="venue" value={form.venue} onChange={(e) => update("venue", e.target.value)} required />
              </div>

              <div className="field">
                <label htmlFor="description">Description</label>
                <input id="description" value={form.description} onChange={(e) => update("description", e.target.value)} />
              </div>

              <div className="field-row">
                <div className="field">
                  <label htmlFor="ticket_price">Ticket price</label>
                  <input id="ticket_price" type="number" min="0" step="0.01" value={form.ticket_price} onChange={(e) => update("ticket_price", e.target.value)} required />
                </div>
                <div className="field">
                  <label htmlFor="total_seats">Total seats</label>
                  <input id="total_seats" type="number" min="1" value={form.total_seats} onChange={(e) => update("total_seats", e.target.value)} required />
                </div>
              </div>

              {error && <p className="field-error" role="alert">{error}</p>}

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