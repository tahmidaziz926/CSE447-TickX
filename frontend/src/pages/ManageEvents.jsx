import { useState, useEffect } from "react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import "./Events.css";
import "./ManageEvents.css";

/**
 * ManageEvents.jsx — Section 3.3: seller views/updates/deactivates
 * their own events. Uses GET /api/events/mine (seller-scoped listing).
 */
export default function ManageEvents() {
  const { isAuthenticated, role, logout, token } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchMyEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchMyEvents() {
    setLoading(true);
    try {
      const res = await fetch("/api/events/mine", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setEvents(res.ok ? data : []);
    } catch {
      setError("Couldn't load your events.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeactivate(eventId) {
    if (!window.confirm("Deactivate this event? Buyers will no longer be able to see or purchase it.")) {
      return;
    }
    try {
      const res = await fetch(`/api/events/${eventId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        fetchMyEvents();
      }
    } catch {
      setError("Couldn't deactivate the event.");
    }
  }

  return (
    <>
      <Navbar isAuthenticated={isAuthenticated} userRole={role} onLogout={logout} />

      <main className="events-page">
        <div className="manage-events__header">
          <div>
            <h1>Your events</h1>
            <p>Manage the events you've created.</p>
          </div>
          <a href="/dashboard/events/create" className="btn btn-primary">
            + Create event
          </a>
        </div>

        {error && <p className="field-error" role="alert">{error}</p>}

        {loading ? (
          <p className="events-page__status">Loading…</p>
        ) : events.length === 0 ? (
          <p className="events-page__status">You haven't created any events yet.</p>
        ) : (
          <div className="manage-events__list">
            {events.map((event) => (
              <div key={event._id} className="ticket-card manage-events__row">
                <div>
                  <span className={`manage-events__status manage-events__status--${event.status.toLowerCase()}`}>
                    {event.status}
                  </span>
                  <h3>{event.name}</h3>
                  <p className="event-card__meta">{event.venue} · ৳{event.ticket_price}</p>
                </div>
                <div className="manage-events__actions">
                  <a href={`/dashboard/events/${event._id}/edit`} className="btn btn-ghost">Edit</a>
                  {event.status === "ACTIVE" && (
                    <button className="btn btn-ghost" onClick={() => handleDeactivate(event._id)}>
                      Deactivate
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </>
  );
}