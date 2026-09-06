import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import AdminLayout from "../../components/AdminLayout";
import "../../components/AdminLayout.css";

/**
 * admin/Transactions.jsx — Section 5.5: monitor all ticket sales and
 * transactions across the platform.
 */
export default function AdminTransactions() {
  const { token } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAll() {
      const res = await fetch("/api/admin/transactions", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setTransactions(res.ok ? data : []);
      setLoading(false);
    }
    fetchAll();
  }, [token]);

  return (
    <AdminLayout>
      <div className="admin-page__header">
        <h1>Transactions</h1>
        <p>All ticket purchases across the platform.</p>
      </div>

      {loading ? (
        <p>Loading…</p>
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
    </AdminLayout>
  );
}