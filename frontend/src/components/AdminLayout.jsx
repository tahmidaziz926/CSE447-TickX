import Navbar from "./Navbar";
import { useAuth } from "../context/AuthContext";
import "./AdminLayout.css";

/**
 * AdminLayout.jsx — shared sidebar navigation for all admin pages.
 * Wrap each admin page's content with this instead of repeating the
 * sidebar in every file.
 */
export default function AdminLayout({ children }) {
  const { isAuthenticated, role, logout } = useAuth();

  const links = [
    { label: "Overview", href: "/admin" },
    { label: "Users", href: "/admin/users" },
    { label: "Sellers", href: "/admin/sellers" },
    { label: "Events", href: "/admin/events" },
    { label: "Transactions", href: "/admin/transactions" },
    { label: "Security logs", href: "/admin/security-logs" },
    { label: "Keys", href: "/admin/keys" },
  ];

  const currentPath = window.location.pathname;

  return (
    <>
      <Navbar isAuthenticated={isAuthenticated} userRole={role} onLogout={logout} />
      <div className="admin-layout">
        <aside className="admin-layout__sidebar">
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className={`admin-layout__link ${currentPath === link.href ? "admin-layout__link--active" : ""}`}
            >
              {link.label}
            </a>
          ))}
        </aside>
        <main className="admin-layout__content">{children}</main>
      </div>
    </>
  );
}