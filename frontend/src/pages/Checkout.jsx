import { useState, useEffect } from "react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import "./AuthPage.css";
import "./Checkout.css";

/**
 * Checkout.jsx — Section 2.5: ticket purchase.
 * Reads ?event=<id>&seat=<n> from the URL (set by EventDetails.jsx's
 * seat selection), shows a summary, and calls the simulated-payment
 * purchase endpoint on confirm.
 */
export default function Checkout() {
  const { isAuthenticated, role, logout, token } = useAuth();
  const params = new URLSearchParams(window.location.search);
  const eventId = params.get("event");
  const seatNumber = params.get("seat");

  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    async function fetchEvent() {
      try {
        const res = await fetch(`/api/events/${eventId}`);
        const data = await res.json();
        if (res.ok) setEvent(data);
        else setError(data.error || "Event not found.");
      } catch {
        setError("Couldn't reach the server.");
      } finally {
        setLoading(false);
      }
    }
    if (eventId) fetchEvent();
  }, [eventId]);

  async function handleConfirmPurchase() {
    setPurchasing(true);
    setError("");
    try {
      const res = await fetch("/api/tickets/purchase", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ event_id: eventId, seat_number: parseInt(seatNumber, 10) }),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Purchase failed.");
        return;
      }

      setResult(data);
    } catch {
      setError("Couldn't reach the server.");
    } finally {
      setPurchasing(false);
    }
  }

  return (
    <>
      <Navbar isAuthenticated={isAuthenticated} userRole={role} onLogout={logout} />

      <main className="auth-page">
        <div className="ticket-card auth-card checkout-card">
          {result ? (
            <div className="checkout-success">
              <h1>Ticket confirmed 🎫</h1>
              <p className="auth-card__sub">
                Ticket ID: <strong>{result.ticket_id}</strong>
              </p>
              <a href="/my-tickets" className="btn btn-primary auth-card__submit">
                View my tickets
              </a>
            </div>
          ) : loading ? (
            <p className="events-page__status">Loading…</p>
          ) : !event ? (
            <p className="field-error">{error || "Event not found."}</p>
          ) : (
            <>
              <h1>Confirm your purchase</h1>
              <p className="auth-card__sub">Payment is simulated for this project — no real charge occurs.</p>

              <div className="checkout-summary">
                <div className="checkout-summary__row">
                  <span>Event</span>
                  <strong>{event.name}</strong>
                </div>
                <div className="checkout-summary__row">
                  <span>Venue</span>
                  <strong>{event.venue}</strong>
                </div>
                <div className="checkout-summary__row">
                  <span>Seat</span>
                  <strong>#{seatNumber}</strong>
                </div>
                <div className="checkout-summary__row checkout-summary__row--total">
                  <span>Total</span>
                  <strong>৳{event.ticket_price}</strong>
                </div>
              </div>

              {error && <p className="field-error" role="alert">{error}</p>}

              <button
                className="btn btn-primary auth-card__submit"
                onClick={handleConfirmPurchase}
                disabled={purchasing}
              >
                {purchasing ? "Processing payment…" : "Confirm & pay"}
              </button>
            </>
          )}
        </div>
      </main>
    </>
  );
}