import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import OtpVerify from "./pages/OtpVerify";
import Events from "./pages/Events";
import EventDetails from "./pages/EventDetails";
import CreateEvent from "./pages/CreateEvent";
import ManageEvents from "./pages/ManageEvents";

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
    <main style={{ padding: "3rem 1.5rem", textAlign: "center" }}>
      <h1>Welcome to TixCrypt</h1>
      <p>Secure event ticketing, built from the ground up.</p>
    </main>
  );
}

// Placeholder — Pallab will replace this with a real buyer/admin dashboard.
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
        {/* Auth pages render their own Navbar (isAuthenticated=false) */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/otp-verify" element={<OtpVerify />} />

        {/* Public event browsing — Events.jsx and EventDetails.jsx
            render their own Navbar with real auth state internally */}
        <Route path="/events" element={<Events />} />
        <Route path="/events/:eventId" element={<EventDetails />} />

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

        {/* Seller-only event management */}
        <Route
          path="/dashboard/events"
          element={
            <ProtectedRoute allowedRoles={["SELLER"]}>
              <ManageEvents />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard/events/create"
          element={
            <ProtectedRoute allowedRoles={["SELLER"]}>
              <CreateEvent />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}