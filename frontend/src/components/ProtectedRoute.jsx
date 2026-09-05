import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * ProtectedRoute.jsx — guards a route behind login (and optionally a role).
 *
 * Remember: this is a UX convenience, NOT the real security boundary.
 * Flask's @login_required / @role_required (auth/middleware.py) are what
 * actually enforce access — this component only hides/redirects the UI
 * so an unauthenticated user doesn't even see a page they can't use.
 *
 * Usage (with react-router-dom):
 *   <Route path="/dashboard" element={
 *     <ProtectedRoute><Dashboard /></ProtectedRoute>
 *   } />
 *
 *   <Route path="/admin" element={
 *     <ProtectedRoute allowedRoles={["ADMIN"]}><AdminDashboard /></ProtectedRoute>
 *   } />
 */
export default function ProtectedRoute({ children, allowedRoles = null }) {
  const { isAuthenticated, role, loading } = useAuth();

  if (loading) {
    // avoid a flash-redirect to /login while we're still confirming
    // the session with the backend on initial page load
    return <div className="route-loading">Checking session…</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    return <Navigate to="/" replace />;
  }

  return children;
}