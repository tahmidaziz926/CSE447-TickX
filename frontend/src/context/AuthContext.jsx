import { createContext, useContext, useState, useEffect } from "react";

/**
 * AuthContext.jsx — holds the logged-in user's session/role app-wide.
 *
 * Wrap your app once in main.jsx or App.jsx:
 *   <AuthProvider>
 *     <App />
 *   </AuthProvider>
 *
 * Then anywhere in the app:
 *   const { isAuthenticated, role, logout } = useAuth();
 */

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("session_token"));
  const [role, setRole] = useState(() => localStorage.getItem("role"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // On app load, confirm the stored token is still valid by hitting
    // a protected endpoint. If it's expired/invalid, clear local state
    // so the UI doesn't claim to be logged in when the backend disagrees.
    async function checkSession() {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const res = await fetch("/api/auth/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          clearSession();
        }
      } catch {
        // network error — leave existing state as-is rather than
        // logging the user out just because of a transient failure
      } finally {
        setLoading(false);
      }
    }
    checkSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function clearSession() {
    localStorage.removeItem("session_token");
    localStorage.removeItem("role");
    setToken(null);
    setRole(null);
  }

  async function logout() {
    if (token) {
      try {
        await fetch("/api/auth/logout", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // best-effort — clear local session regardless of network result
      }
    }
    clearSession();
    window.location.href = "/login";
  }

  const value = {
    token,
    role,
    isAuthenticated: Boolean(token),
    loading,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside an <AuthProvider>");
  }
  return ctx;
}