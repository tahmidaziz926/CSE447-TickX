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
import Checkout from "./pages/Checkout";
import MyTickets from "./pages/MyTickets";
import MyTransactions from "./pages/MyTransactions";
import AdminDashboard from "./pages/admin/Dashboard";
import AdminUsers from "./pages/admin/Users";
import AdminSellers from "./pages/admin/Sellers";
import AdminEvents from "./pages/admin/Events";
import AdminTransactions from "./pages/admin/Transactions";
import AdminSecurityLogs from "./pages/admin/SecurityLogs";
import AdminKeys from "./pages/admin/Keys";

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
        {/* Auth pages */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/otp-verify" element={<OtpVerify />} />

        {/* Public event browsing */}
        <Route path="/events" element={<Events />} />
        <Route path="/events/:eventId" element={<EventDetails />} />

        <Route path="/" element={<Layout><Home /></Layout>} />
        <Route
          path="/dashboard"
          element={<Layout><ProtectedRoute><Dashboard /></ProtectedRoute></Layout>}
        />

        {/* Seller-only event management */}
        <Route
          path="/dashboard/events"
          element={<ProtectedRoute allowedRoles={["SELLER"]}><ManageEvents /></ProtectedRoute>}
        />
        <Route
          path="/dashboard/events/create"
          element={<ProtectedRoute allowedRoles={["SELLER"]}><CreateEvent /></ProtectedRoute>}
        />

        {/* Buyer purchase flow (Pallab's part) */}
        <Route
          path="/checkout"
          element={<ProtectedRoute allowedRoles={["BUYER"]}><Checkout /></ProtectedRoute>}
        />
        <Route
          path="/my-tickets"
          element={<ProtectedRoute allowedRoles={["BUYER"]}><MyTickets /></ProtectedRoute>}
        />
        <Route
          path="/my-transactions"
          element={<ProtectedRoute allowedRoles={["BUYER"]}><MyTransactions /></ProtectedRoute>}
        />

        {/* Admin dashboard (Pallab's part) — all require ADMIN role */}
        <Route path="/admin" element={<ProtectedRoute allowedRoles={["ADMIN"]}><AdminDashboard /></ProtectedRoute>} />
        <Route path="/admin/users" element={<ProtectedRoute allowedRoles={["ADMIN"]}><AdminUsers /></ProtectedRoute>} />
        <Route path="/admin/sellers" element={<ProtectedRoute allowedRoles={["ADMIN"]}><AdminSellers /></ProtectedRoute>} />
        <Route path="/admin/events" element={<ProtectedRoute allowedRoles={["ADMIN"]}><AdminEvents /></ProtectedRoute>} />
        <Route path="/admin/transactions" element={<ProtectedRoute allowedRoles={["ADMIN"]}><AdminTransactions /></ProtectedRoute>} />
        <Route path="/admin/security-logs" element={<ProtectedRoute allowedRoles={["ADMIN"]}><AdminSecurityLogs /></ProtectedRoute>} />
        <Route path="/admin/keys" element={<ProtectedRoute allowedRoles={["ADMIN"]}><AdminKeys /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}