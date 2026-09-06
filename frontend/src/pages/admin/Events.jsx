import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import AdminLayout from "../../components/AdminLayout";
import "../../components/AdminLayout.css";

/**
 * admin/Events.jsx — Section 5.4:
 * Admin view of all events with the ability to deactivate them.
 *
 * This page is ADMIN ONLY and intentionally uses:
 *
 *     GET  /api/admin/events
 *     POST /api/admin/events/<event_id>/deactivate
 *
 * Buyer-facing event browsing must use a separate Events.jsx page
 * that calls:
 *
 *     GET /api/events
 */
export default function AdminEvents() {
  const { token } = useAuth();

  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function fetchEvents() {
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/admin/events", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await res.json();

      if (!res.ok) {
        setEvents([]);
        setError(data.error || "Could not load events.");
        return;
      }

      setEvents(Array.isArray(data) ? data : []);
    } catch (err) {
      setEvents([]);
      setError("Couldn't reach the server.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) {
      fetchEvents();
    }
  }, [token]);

  async function handleDeactivate(eventId) {
    if (!window.confirm("Deactivate this event?")) {
      return;
    }

    try {
      const res = await fetch(
        `/api/admin/events/${eventId}/deactivate`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Could not deactivate event.");
        return;
      }

      await fetchEvents();
    } catch (err) {
      setError("Couldn't reach the server.");
    }
  }

  return (
    <AdminLayout>
      <div className="admin-page__header">
        <h1>Events</h1>
        <p>
          All events created by sellers across the platform.
        </p>
      </div>

      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p>Loading…</p>
      ) : events.length === 0 ? (
        <p>No events found.</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Venue</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {events.map((event) => (
              <tr key={event._id}>
                <td>{event.name}</td>

                <td>{event.venue}</td>

                <td>
                  <span
                    className={`admin-table__badge admin-table__badge--${(
                      event.status || ""
                    ).toLowerCase()}`}
                  >
                    {event.status}
                  </span>
                </td>

                <td className="admin-table__actions">
                  {event.status === "ACTIVE" && (
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() =>
                        handleDeactivate(event._id)
                      }
                    >
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </AdminLayout>
  );
}