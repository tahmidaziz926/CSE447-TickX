import { useState, useEffect } from "react";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import "./Events.css";
import "../components/AdminLayout.css"

/**
 * MyTransactions.jsx — Section 2.6: buyer's transaction history.
 */
export default function MyTransactions() {
  const { isAuthenticated, role, logout, token } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTransactions() {
      try {
        const res = await fetch("/api/transactions/my", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        setTransactions(res.ok ? data : []);
      } catch {
        setTransactions([]);
      } finally {
        setLoading(false);
      }
    }
    fetchTransactions();
  }, [token]);

  return (
    <>
      <Navbar isAuthenticated={isAuthenticated} userRole={role} onLogout={logout} />

      <main className="events-page">
        <div className="events-page__header">
          <h1>My transactions</h1>
          <p>Your purchase history.</p>
        </div>

        {loading ? (
          <p className="events-page__status">Loading…</p>
        ) : transactions.length === 0 ? (
          <p className="events-page__status">No transactions yet.</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Seat</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t._id}>
                  <td>{t.seat_number}</td>
                  <td>৳{t.amount}</td>
                  <td>
                    <span className={`admin-table__badge admin-table__badge--${t.status.toLowerCase()}`}>
                      {t.status}
                    </span>
                  </td>
                  <td>{new Date(t.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
    </>
  );
}