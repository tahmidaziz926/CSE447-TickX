import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import AdminLayout from "../../components/AdminLayout";
import "../../components/AdminLayout.css";

/**
 * admin/Users.jsx — Section 5.3: view and manage Buyer/Seller accounts.
 */
export default function AdminUsers() {
  const { token } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  async function fetchUsers() {
    setLoading(true);
    const res = await fetch("/api/admin/users", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    setUsers(res.ok ? data : []);
    setLoading(false);
  }

  useEffect(() => { fetchUsers(); }, [token]);

  async function toggleStatus(user) {
    const action = user.account_status === "ACTIVE" ? "suspend" : "reactivate";
    await fetch(`/api/admin/users/${user._id}/${action}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchUsers();
  }

  return (
    <AdminLayout>
      <div className="admin-page__header">
        <h1>Users</h1>
        <p>Manage buyer and seller accounts.</p>
      </div>

      {loading ? (
        <p>Loading…</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u._id}>
                <td>{u.email}</td>
                <td>{u.role}</td>
                <td>
                  <span className={`admin-table__badge admin-table__badge--${u.account_status.toLowerCase()}`}>
                    {u.account_status}
                  </span>
                </td>
                <td className="admin-table__actions">
                  <button className="btn btn-ghost" onClick={() => toggleStatus(u)}>
                    {u.account_status === "ACTIVE" ? "Suspend" : "Reactivate"}
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