import { useState, useEffect } from "react";
import "./Navbar.css";

/**
 * Navbar.jsx — TixCrypt navigation bar.
 *
 * Links shown depend on auth state AND role:
 *   - Logged out: Events, How it works
 *   - BUYER:      Events, My Tickets, My Transactions, Profile
 *   - SELLER:     Events, My Events, Create Event, Profile
 *   - ADMIN:      Events, Admin Dashboard, Profile
 *
 * This is what was missing before — the role-specific pages all
 * existed and worked, but nothing in the nav ever linked to them.
 */
export default function Navbar({ isAuthenticated = false, userRole = null, onLogout }) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  function getNavLinks() {
    if (!isAuthenticated) {
      return [
        { label: "Events", href: "/events" },
        { label: "How it works", href: "/how-it-works" },
      ];
    }

    if (userRole === "SELLER") {
      return [
        { label: "Events", href: "/events" },
        { label: "My Events", href: "/dashboard/events" },
        { label: "Create Event", href: "/dashboard/events/create" },
        { label: "Profile", href: "/profile" },
      ];
    }

    if (userRole === "ADMIN") {
      return [
        { label: "Events", href: "/events" },
        { label: "Admin Dashboard", href: "/admin" },
        { label: "Profile", href: "/profile" },
      ];
    }

    // BUYER (default authenticated role)
    return [
      { label: "Events", href: "/events" },
      { label: "My Tickets", href: "/my-tickets" },
      { label: "My Transactions", href: "/my-transactions" },
      { label: "Profile", href: "/profile" },
    ];
  }

  const navLinks = getNavLinks();

  return (
    <header className={`nav ${scrolled ? "nav--scrolled" : ""}`}>
      <div className="nav__inner">
        <a href="/" className="nav__brand">
          <span className="nav__mark" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a1.5 1.5 0 0 0 0 3v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a1.5 1.5 0 0 0 0-3V8Z"
                stroke="#0E6B4F"
                strokeWidth="1.6"
              />
              <path d="M14 6v12" stroke="#0E6B4F" strokeWidth="1.6" strokeDasharray="2.5 2.5" />
            </svg>
          </span>
          <span className="nav__brand-text">TixCrypt</span>
        </a>

        <nav className="nav__links" aria-label="Primary">
          {navLinks.map((link) => (
            <a key={link.href} href={link.href} className="nav__link">
              {link.label}
            </a>
          ))}
        </nav>

        <div className="nav__actions">
          {isAuthenticated ? (
            <>
              {userRole && <span className="nav__role-badge">{userRole}</span>}
              <button className="btn btn-ghost" onClick={onLogout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <a href="/login" className="btn btn-ghost">
                Log in
              </a>
              <a href="/register" className="btn btn-primary">
                Get started
              </a>
            </>
          )}
        </div>

        <button
          className="nav__toggle"
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((v) => !v)}
        >
          <span />
          <span />
          <span />
        </button>
      </div>

      {menuOpen && (
        <div className="nav__mobile">
          {navLinks.map((link) => (
            <a key={link.href} href={link.href} className="nav__mobile-link">
              {link.label}
            </a>
          ))}
          <div className="nav__mobile-actions">
            {isAuthenticated ? (
              <button className="btn btn-ghost" onClick={onLogout}>
                Log out
              </button>
            ) : (
              <>
                <a href="/login" className="btn btn-ghost">Log in</a>
                <a href="/register" className="btn btn-primary">Get started</a>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}