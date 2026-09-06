import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import AdminLayout from "../../components/AdminLayout";
import "../../components/AdminLayout.css";

/**
 * admin/Events.jsx — Section 5.4: view all events, deactivate
 * inappropriate/invalid ones.
 */
export default function AdminEvents() {
  const { token } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  async function fetchEvents() {
    setLoading(true);
    const res = await fetch("/api/admin/events", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    setEvents(res.ok ? data : []);
    setLoading(false);
  }

  useEffect(() => { fetchEvents(); }, [token]);

  async function handleDeactivate(eventId) {
    if (!window.confirm("Deactivate this event?")) return;
    await fetch(`/api/admin/events/${eventId}/deactivate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchEvents();
  }

  return (
    <AdminLayout>
      <div className="admin-page__header">
        <h1>Events</h1>
        <p>All events created by sellers across the platform.</p>
      </div>

      {loading ? (
        <p>Loading…</p>
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
            {events.map((e) => (
              <tr key={e._id}>
                <td>{e.name}</td>
                <td>{e.venue}</td>
                <td>
                  <span className={`admin-table__badge admin-table__badge--${e.status.toLowerCase()}`}>
                    {e.status}
                  </span>
                </td>
                <td className="admin-table__actions">
                  {e.status === "ACTIVE" && (
                    <button className="btn btn-ghost" onClick={() => handleDeactivate(e._id)}>
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