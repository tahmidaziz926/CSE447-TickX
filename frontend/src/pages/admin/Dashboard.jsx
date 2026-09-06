import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import AdminLayout from "../../components/AdminLayout";
import "../../components/AdminLayout.css";
import "./AdminDashboard.css";

/**
 * admin/Dashboard.jsx — Section 5.1: admin overview.
 * Pulls lightweight counts from the existing admin endpoints rather
 * than needing a dedicated /api/admin/stats endpoint.
 */
export default function AdminDashboard() {
  const { token } = useAuth();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    async function fetchStats() {
      const headers = { Authorization: `Bearer ${token}` };
      const [users, sellers, events, transactions] = await Promise.all([
        fetch("/api/admin/users", { headers }).then((r) => r.json()),
        fetch("/api/admin/sellers/pending", { headers }).then((r) => r.json()),
        fetch("/api/admin/events", { headers }).then((r) => r.json()),
        fetch("/api/admin/transactions", { headers }).then((r) => r.json()),
      ]);
      setStats({
        totalUsers: Array.isArray(users) ? users.length : 0,
        pendingSellers: Array.isArray(sellers) ? sellers.length : 0,
        totalEvents: Array.isArray(events) ? events.length : 0,
        totalTransactions: Array.isArray(transactions) ? transactions.length : 0,
      });
    }
    fetchStats();
  }, [token]);

  return (
    <AdminLayout>
      <div className="admin-page__header">
        <h1>Overview</h1>
        <p>System-wide activity at a glance.</p>
      </div>

      {stats && (
        <div className="admin-stats">
          <div className="ticket-card admin-stats__card">
            <span className="admin-stats__value">{stats.totalUsers}</span>
            <span className="admin-stats__label">Total users</span>
          </div>
          <div className="ticket-card admin-stats__card">
            <span className="admin-stats__value">{stats.pendingSellers}</span>
            <span className="admin-stats__label">Pending sellers</span>
          </div>
          <div className="ticket-card admin-stats__card">
            <span className="admin-stats__value">{stats.totalEvents}</span>
            <span className="admin-stats__label">Total events</span>
          </div>
          <div className="ticket-card admin-stats__card">
            <span className="admin-stats__value">{stats.totalTransactions}</span>
            <span className="admin-stats__label">Transactions</span>
          </div>
        </div>
      )}
    </AdminLayout>
  );
}