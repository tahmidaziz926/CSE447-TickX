import { useState, useEffect } from "react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import "./Events.css";

/**
 * Events.jsx — buyer-facing event browsing (Section 2.2).
 * Public: no login required to browse, matching the requirements
 * ("Buyers can view events published by approved sellers").
 */
export default function Events() {
  const { isAuthenticated, role, logout } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");

  useEffect(() => {
    fetchEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchEvents() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.set("name", search);
      if (category) params.set("category", category);

      const res = await fetch(`/api/events?${params.toString()}`);
      const data = await res.json();
      setEvents(res.ok ? data : []);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }

  function handleSearchSubmit(e) {
    e.preventDefault();
    fetchEvents();
  }

  return (
    <>
      <Navbar isAuthenticated={isAuthenticated} userRole={role} onLogout={logout} />

      <main className="events-page">
        <div className="events-page__header">
          <h1>Browse events</h1>
          <p>Find your next event — every listing is integrity-verified.</p>
        </div>

        <form className="events-page__search" onSubmit={handleSearchSubmit}>
          <input
            type="text"
            placeholder="Search by event name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All categories</option>
            <option value="Music">Music</option>
            <option value="Sports">Sports</option>
            <option value="Theatre">Theatre</option>
            <option value="Conference">Conference</option>
          </select>
          <button type="submit" className="btn btn-primary">Search</button>
        </form>

        {loading ? (
          <p className="events-page__status">Loading events…</p>
        ) : events.length === 0 ? (
          <p className="events-page__status">No events found.</p>
        ) : (
          <div className="events-page__grid">
            {events.map((event) => (
              <a
                key={event._id}
                href={`/events/${event._id}`}
                className="ticket-card event-card"
              >
                <span className="event-card__category">{event.category}</span>
                <h3>{event.name}</h3>
                <p className="event-card__meta">{event.venue}</p>
                <p className="event-card__meta">
                  {new Date(event.date_time).toLocaleDateString(undefined, {
                    dateStyle: "medium",
                  })}
                </p>
                <p className="event-card__price">৳{event.ticket_price}</p>
              </a>
            ))}
          </div>
        )}
      </main>
    </>
  );
}