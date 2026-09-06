import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import AdminLayout from "../../components/AdminLayout";
import "../../components/AdminLayout.css";

/**
 * admin/Keys.jsx — Section 7: key lifecycle management UI.
 * Shows key METADATA only — key_material (the actual secret) is never
 * sent by the backend to any API response, so there's nothing to leak
 * here even if this page were compromised.
 */
export default function AdminKeys() {
  const { token } = useAuth();
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rotatePurpose, setRotatePurpose] = useState("");

  async function fetchKeys() {
    setLoading(true);
    const res = await fetch("/api/admin/keys", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    setKeys(res.ok ? data : []);
    setLoading(false);
  }

  useEffect(() => { fetchKeys(); }, [token]);

  async function handleRotate(e) {
    e.preventDefault();
    if (!rotatePurpose) return;
    await fetch("/api/admin/keys/rotate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ purpose: rotatePurpose }),
    });
    setRotatePurpose("");
    fetchKeys();
  }

  async function handleRevoke(keyId) {
    if (!window.confirm("Revoke this key? It will be rejected for both new operations and future verification.")) return;
    await fetch(`/api/admin/keys/${keyId}/revoke`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchKeys();
  }

  return (
    <AdminLayout>
      <div className="admin-page__header">
        <h1>Key management</h1>
        <p>Lifecycle state for every cryptographic key. Key material is never shown here.</p>
      </div>

      <form onSubmit={handleRotate} className="admin-rotate-form">
        <input
          placeholder="Purpose (e.g. ticket-mac)"
          value={rotatePurpose}
          onChange={(e) => setRotatePurpose(e.target.value)}
        />
        <button type="submit" className="btn btn-primary">Rotate key</button>
      </form>

      {loading ? (
        <p>Loading…</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Purpose</th>
              <th>Algorithm</th>
              <th>Version</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k.key_id}>
                <td>{k.purpose}</td>
                <td>{k.algorithm}</td>
                <td>v{k.key_version}</td>
                <td>
                  <span className={`admin-table__badge admin-table__badge--${k.status.toLowerCase()}`}>
                    {k.status}
                  </span>
                </td>
                <td className="admin-table__actions">
                  {k.status !== "REVOKED" && (
                    <button className="btn btn-ghost" onClick={() => handleRevoke(k.key_id)}>
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </AdminLayout>
  );
}