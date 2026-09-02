import { useState, useEffect } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { ExternalLink, Menu, X } from "lucide-react";
import FeedbackModal from "./FeedbackModal";

function Navbar() {
  const location = useLocation();
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [isMobileMenuOpen]);

  return (
    <>
      <nav className="navbar">
        <Link to="/" className="logo">
          <span className="logo-text">
            <span className="logo-synapse">Synapse</span>
            <span className="logo-ai">AI</span>
          </span>
        </Link>

        {/* Desktop Nav Links */}
        <div className="nav-links">
          {location.pathname === "/engineering" && (
            <NavLink to="/" className="nav-link">
              Research
            </NavLink>
          )}

          <a
            href="https://mayurramani-portfolio.vercel.app/"
            target="_blank"
            rel="noreferrer"
            className="nav-link external-link"
          >
            <span>Developer</span>
            <ExternalLink size={12} />
          </a>

          <button
            type="button"
            className="nav-text-btn"
            onClick={() => setIsFeedbackOpen(true)}
          >
            Feedback
          </button>

          <NavLink to="/engineering" className="nav-link">
            Engineering
          </NavLink>

          <NavLink to="/analytics" className="nav-link analytics-link" title="Grafana Telemetry (Admin Only)">
            Telemetry
          </NavLink>
        </div>

        {/* Hamburger Button (mobile only) */}
        <button
          className="hamburger-btn"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label="Toggle menu"
        >
          {isMobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </nav>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div className="mobile-menu-overlay" onClick={() => setIsMobileMenuOpen(false)}>
          <div className="mobile-menu" onClick={(e) => e.stopPropagation()}>
            {location.pathname === "/engineering" && (
              <NavLink to="/" className="mobile-menu-link">
                Research
              </NavLink>
            )}

            <a
              href="https://mayurramani-portfolio.vercel.app/"
              target="_blank"
              rel="noreferrer"
              className="mobile-menu-link"
            >
              <span>Developer</span>
              <ExternalLink size={13} />
            </a>

            <button
              type="button"
              className="mobile-menu-link"
              onClick={() => {
                setIsMobileMenuOpen(false);
                setIsFeedbackOpen(true);
              }}
            >
              Feedback
            </button>

            <NavLink to="/engineering" className="mobile-menu-link">
              Engineering
            </NavLink>
          </div>
        </div>
      )}

      <FeedbackModal
        isOpen={isFeedbackOpen}
        onClose={() => setIsFeedbackOpen(false)}
      />
    </>
  );
}

export default Navbar;