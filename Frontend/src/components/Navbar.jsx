import { useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import FeedbackModal from "./FeedbackModal";

function Navbar() {
  const location = useLocation();
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);

  return (
    <>
      <nav className="navbar">
        <Link to="/" className="logo">
          <span className="logo-text">
            <span className="logo-synapse">Synapse</span>
            <span className="logo-ai">AI</span>
          </span>
        </Link>

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
        </div>
      </nav>

      <FeedbackModal
        isOpen={isFeedbackOpen}
        onClose={() => setIsFeedbackOpen(false)}
      />
    </>
  );
}

export default Navbar;