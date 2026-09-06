import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import AdminLayout from "../../components/AdminLayout";
import "../../components/AdminLayout.css";

/**
 * admin/Sellers.jsx — Section 5.2: seller approval queue.
 */
export default function AdminSellers() {
  const { token } = useAuth();
  const [sellers, setSellers] = useState([]);
  const [loading, setLoading] = useState(true);

  async function fetchPending() {
    setLoading(true);
    const res = await fetch("/api/admin/sellers/pending", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    setSellers(res.ok ? data : []);
    setLoading(false);
  }

  useEffect(() => { fetchPending(); }, [token]);

  async function handleDecision(sellerId, decision) {
    await fetch(`/api/admin/sellers/${sellerId}/${decision}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchPending();
  }

  return (
    <AdminLayout>
      <div className="admin-page__header">
        <h1>Seller approvals</h1>
        <p>Review newly registered sellers before they can publish events.</p>
      </div>

      {loading ? (
        <p>Loading…</p>
      ) : sellers.length === 0 ? (
        <p>No pending seller applications.</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sellers.map((s) => (
              <tr key={s._id}>
                <td>{s.email}</td>
                <td>
                  <span className="admin-table__badge admin-table__badge--pending">PENDING</span>
                </td>
                <td className="admin-table__actions">
                  <button className="btn btn-primary" onClick={() => handleDecision(s._id, "approve")}>
                    Approve
                  </button>
                  <button className="btn btn-ghost" onClick={() => handleDecision(s._id, "reject")}>
                    Reject
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </AdminLayout>
  );
}