import { useState, useEffect } from "react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import "./Events.css";

/**
 * Events.jsx — Buyer-facing event browser.
 *
 * Uses:
 *     GET /api/events
 *
 * Only ACTIVE events are returned by the backend.
 *
 * Clicking "View event" opens:
 *     /events/<eventId>
 *
 * which is handled by EventDetails.jsx.
 */
export default function Events() {
  const { isAuthenticated, role, logout } = useAuth();

  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [name, setName] = useState("");
  const [category, setCategory] = useState("");

  async function fetchEvents(customName = name, customCategory = category) {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams();

      if (customName.trim()) {
        params.set("name", customName.trim());
      }

      if (customCategory.trim()) {
        params.set("category", customCategory.trim());
      }

      const queryString = params.toString();

      const url = queryString
        ? `/api/events?${queryString}`
        : "/api/events";

      const res = await fetch(url);
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
    fetchEvents("", "");
  }, []);

  function handleSearch(e) {
    e.preventDefault();
    fetchEvents();
  }

  function handleClear() {
    setName("");
    setCategory("");
    fetchEvents("", "");
  }

  return (
    <>
      <Navbar
        isAuthenticated={isAuthenticated}
        userRole={role}
        onLogout={logout}
      />

      <main className="events-page">

        {/* Page header */}
        <div className="events-page__header">
          <h1>Events</h1>
          <p>
            Browse events created by sellers across the platform.
          </p>
        </div>

        {/* Search and filters */}
        <form
          className="events-page__filters"
          onSubmit={handleSearch}
        >
          <input
            type="text"
            placeholder="Search event name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <input
            type="text"
            placeholder="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />

          <button
            type="submit"
            className="btn btn-primary"
          >
            Search
          </button>

          <button
            type="button"
            className="btn btn-ghost"
            onClick={handleClear}
          >
            Clear
          </button>
        </form>

        {/* Loading */}
        {loading && (
          <p className="events-page__status">
            Loading events…
          </p>
        )}

        {/* Error */}
        {!loading && error && (
          <p className="events-page__status">
            {error}
          </p>
        )}

        {/* No events */}
        {!loading && !error && events.length === 0 && (
          <p className="events-page__status">
            No active events available right now.
          </p>
        )}

        {/* Event cards */}
        {!loading && !error && events.length > 0 && (
          <div className="events-grid">
            {events.map((event) => (
              <article
                key={event._id}
                className="event-card"
              >
                <span className="event-card__category">
                  {event.category}
                </span>

                <h2>
                  {event.name}
                </h2>

                <p className="event-card__meta">
                  {new Date(
                    event.date_time
                  ).toLocaleString(undefined, {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </p>

                <p className="event-card__meta">
                  {event.venue}
                </p>

                {event.description && (
                  <p className="event-card__description">
                    {event.description}
                  </p>
                )}

                <div className="event-card__footer">
                  <span className="event-card__price">
                    ৳{event.ticket_price}
                  </span>

                  <a
                    href={`/events/${event._id}`}
                    className="btn btn-primary"
                  >
                    View event
                  </a>
                </div>
              </article>
            ))}
          </div>
        )}
      </main>
    </>
  );
}