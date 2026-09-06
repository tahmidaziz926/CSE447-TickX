import { useState, useEffect } from "react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import "./Events.css";
import "./MyTickets.css";

/**
 * MyTickets.jsx — Section 2.6: buyer's ticket history.
 * Every ticket returned by GET /api/tickets/my has already been
 * MAC-verified server-side (tickets/services.py's list_my_tickets) —
 * a tampered ticket is silently excluded rather than shown broken.
 */
export default function MyTickets() {
  const { isAuthenticated, role, logout, token } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTickets() {
      try {
        const res = await fetch("/api/tickets/my", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        setTickets(res.ok ? data : []);
      } catch {
        setTickets([]);
      } finally {
        setLoading(false);
      }
    }
    fetchTickets();
  }, [token]);

  return (
    <>
      <Navbar isAuthenticated={isAuthenticated} userRole={role} onLogout={logout} />

      <main className="events-page">
        <div className="events-page__header">
          <h1>My tickets</h1>
          <p>Every ticket here has passed integrity verification.</p>
        </div>

        {loading ? (
          <p className="events-page__status">Loading…</p>
        ) : tickets.length === 0 ? (
          <p className="events-page__status">You don't have any tickets yet.</p>
        ) : (
          <div className="my-tickets__list">
            {tickets.map((ticket) => (
              <div key={ticket._id} className="ticket-card my-tickets__row">
                <div>
                  <span className="my-tickets__verified">✓ Verified</span>
                  <p className="my-tickets__id">Ticket #{ticket.ticket_id}</p>
                  <p className="event-card__meta">Seat {ticket.seat_number} · ৳{ticket.protected_fields.price}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </>
  );
}