import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import OtpVerify from "./pages/OtpVerify";

/**
 * Layout wraps every page with the Navbar, wired to real auth state
 * from AuthContext instead of hardcoded props.
 */
function Layout({ children }) {
  const { isAuthenticated, role, logout } = useAuth();
  return (
    <>
      <Navbar isAuthenticated={isAuthenticated} userRole={role} onLogout={logout} />
      {children}
    </>
  );
}

function Home() {
  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "calc(100vh - 80px)",
        padding: "3rem 1.5rem",
        textAlign: "center",
      }}
    >
      <h1
        style={{
          fontSize: "3.5rem",
          color: "var(--green-700)",
          marginBottom: "1rem",
        }}
      >
        Welcome to TixCrypt
      </h1>
      <p>Secure event ticketing, built from the ground up.</p>
    </main>
  );
}

// Placeholder — Tahmid/Pallab will replace this once their dashboards exist.
function Dashboard() {
  const { role } = useAuth();
  return (
    <main style={{ padding: "3rem 1.5rem" }}>
      <h1>Dashboard</h1>
      <p>Logged in as: {role}</p>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Auth pages render their own Navbar (isAuthenticated=false),
            since a logged-out user always sees the logged-out nav state
            on these specific pages. */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/otp-verify" element={<OtpVerify />} />

        {/* Everything else uses the shared Layout with live auth state */}
        <Route
          path="/"
          element={
            <Layout>
              <Home />
            </Layout>
          }
        />
        <Route
          path="/dashboard"
          element={
            <Layout>
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            </Layout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}