import { useState, useEffect, useCallback } from "react";
import "./SeatGrid.css";

/**
 * SeatGrid.jsx — clickable seat grid for an event.
 *
 * IMPORTANT: this is a UI convenience only. The backend
 * (events/seats.py) always re-checks availability before confirming a
 * selection or a purchase — this component's local state is never the
 * security/business-logic authority, per Section 2.4 of the
 * requirements ("The system will verify seat availability before
 * completing the purchase").
 *
 * Usage:
 *   <SeatGrid eventId={id} onSeatConfirmed={(seatNumber) => {...}} />
 */
export default function SeatGrid({ eventId, onSeatConfirmed }) {
  const [statuses, setStatuses] = useState({});
  const [selectedSeat, setSelectedSeat] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const token = localStorage.getItem("session_token");

  const fetchStatuses = useCallback(async () => {
    try {
      const res = await fetch(`/api/events/${eventId}/seats`);
      const data = await res.json();
      if (res.ok) {
        setStatuses(data);
      }
    } catch {
      setError("Couldn't load seat availability.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    fetchStatuses();
    // Poll periodically so other buyers' selections/purchases show up
    // without a manual refresh.
    const interval = setInterval(fetchStatuses, 5000);
    return () => clearInterval(interval);
  }, [fetchStatuses]);

  async function handleSeatClick(seatNumber, currentStatus) {
    if (currentStatus === "SOLD") return;

    setError("");

    if (selectedSeat === seatNumber) {
      // clicking your own selected seat again releases it
      await fetch(`/api/events/${eventId}/seats/${seatNumber}/release`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      setSelectedSeat(null);
      fetchStatuses();
      return;
    }

    if (currentStatus === "SELECTED") return; // someone else has it held

    try {
      const res = await fetch(`/api/events/${eventId}/seats/${seatNumber}/select`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "That seat just became unavailable.");
        fetchStatuses(); // resync — someone else likely took it
        return;
      }

      // release any previously held seat before holding the new one
      if (selectedSeat !== null) {
        await fetch(`/api/events/${eventId}/seats/${selectedSeat}/release`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      }

      setSelectedSeat(seatNumber);
      onSeatConfirmed?.(seatNumber);
      fetchStatuses();
    } catch {
      setError("Couldn't reach the server. Try again.");
    }
  }

  if (loading) {
    return <p className="seat-grid__loading">Loading seats…</p>;
  }

  const seatNumbers = Object.keys(statuses).map(Number).sort((a, b) => a - b);

  return (
    <div className="seat-grid">
      <div className="seat-grid__legend">
        <span className="seat-grid__legend-item">
          <span className="seat seat--available seat--mini" /> Available
        </span>
        <span className="seat-grid__legend-item">
          <span className="seat seat--selected seat--mini" /> Selected
        </span>
        <span className="seat-grid__legend-item">
          <span className="seat seat--sold seat--mini" /> Sold
        </span>
      </div>

      {error && <p className="field-error" role="alert">{error}</p>}

      <div className="seat-grid__grid">
        {seatNumbers.map((num) => {
          const status = statuses[num];
          const isMine = selectedSeat === num;
          const className = isMine
            ? "seat seat--selected"
            : status === "SOLD"
            ? "seat seat--sold"
            : status === "SELECTED"
            ? "seat seat--held"
            : "seat seat--available";

          return (
            <button
              key={num}
              className={className}
              disabled={status === "SOLD" || (status === "SELECTED" && !isMine)}
              onClick={() => handleSeatClick(num, status)}
              aria-label={`Seat ${num} — ${isMine ? "selected by you" : status}`}
            >
              {num}
            </button>
          );
        })}
      </div>
    </div>
  );
}