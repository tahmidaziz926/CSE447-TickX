import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import AdminLayout from "../../components/AdminLayout";
import "../../components/AdminLayout.css";

/**
 * admin/SecurityLogs.jsx — Section 5.6: security event log viewer.
 */
export default function AdminSecurityLogs() {
  const { token } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLogs() {
      const res = await fetch("/api/admin/security-logs", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setLogs(res.ok ? data : []);
      setLoading(false);
    }
    fetchLogs();
  }, [token]);

  return (
    <AdminLayout>
      <div className="admin-page__header">
        <h1>Security logs</h1>
        <p>Authentication attempts, MAC failures, key actions, and admin operations.</p>
      </div>

      {loading ? (
        <p>Loading…</p>
      ) : logs.length === 0 ? (
        <p>No security events recorded yet.</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Event</th>
              <th>Message</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log._id}>
                <td>
                  <span className="admin-table__badge admin-table__badge--pending">
                    {log.event_type}
                  </span>
                </td>
                <td>{log.message}</td>
                <td>{new Date(log.timestamp).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </AdminLayout>
  );
}