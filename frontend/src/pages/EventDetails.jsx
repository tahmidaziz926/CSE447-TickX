import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import SeatGrid from "../components/SeatGrid";
import { useAuth } from "../context/AuthContext";
import "./Events.css";
import "./EventDetails.css";

/**
 * EventDetails.jsx — Section 2.3: event details + seat selection entry
 * point. Ties together event info display and the SeatGrid component.
 */
export default function EventDetails() {
  const { eventId } = useParams();
  const { isAuthenticated, role, logout } = useAuth();
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedSeat, setSelectedSeat] = useState(null);

  useEffect(() => {
    async function fetchEvent() {
      try {
        const res = await fetch(`/api/events/${eventId}`);
        const data = await res.json();
        if (!res.ok) {
          setError(data.error || "Event not found.");
          return;
        }
        setEvent(data);
      } catch {
        setError("Couldn't reach the server.");
      } finally {
        setLoading(false);
      }
    }
    fetchEvent();
  }, [eventId]);

  return (
    <>
      <Navbar isAuthenticated={isAuthenticated} userRole={role} onLogout={logout} />

      <main className="events-page">
        {loading ? (
          <p className="events-page__status">Loading…</p>
        ) : error ? (
          <p className="events-page__status">{error}</p>
        ) : (
          <div className="event-details">
            <div className="event-details__info">
              <span className="event-card__category">{event.category}</span>
              <h1>{event.name}</h1>
              <p className="event-details__meta">
                {new Date(event.date_time).toLocaleString(undefined, {
                  dateStyle: "full",
                  timeStyle: "short",
                })}
              </p>
              <p className="event-details__meta">{event.venue}</p>
              <p className="event-details__description">{event.description}</p>
              <p className="event-card__price">৳{event.ticket_price} per seat</p>
            </div>

            <div className="event-details__seats ticket-card">
              <h2>Select a seat</h2>
              {isAuthenticated ? (
                <>
                  <SeatGrid eventId={eventId} onSeatConfirmed={setSelectedSeat} />
                  {selectedSeat && (
                    <a
                      href={`/checkout?event=${eventId}&seat=${selectedSeat}`}
                      className="btn btn-primary event-details__checkout"
                    >
                      Continue to checkout — Seat {selectedSeat}
                    </a>
                  )}
                </>
              ) : (
                <p>
                  <a href="/login">Log in</a> to select a seat and purchase tickets.
                </p>
              )}
            </div>
          </div>
        )}
      </main>
    </>
  );
}