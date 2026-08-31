import { Link } from "react-router-dom";

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-container">
        <div className="footer-brand">
          <div className="logo">
            <span className="logo-text">
              <span className="logo-synapse">Synapse</span>
              <span className="logo-ai">AI</span>
            </span>
          </div>
          <p className="footer-tagline">
            Autonomous multi-agent deep research intelligence platform.
          </p>
        </div>

        <div className="footer-links">
          <div className="footer-col">
            <h4>Navigation</h4>
            <Link to="/">Home</Link>
            <Link to="/engineering">Engineering Architecture</Link>
          </div>

          <div className="footer-col">
            <h4>System Status</h4>
            <div className="status-badge">
              <span className="status-dot"></span>
              <span>All Systems Operational</span>
            </div>
          </div>
        </div>
      </div>

      <div className="footer-bottom">
        <p>© {new Date().getFullYear()} SynapseAI. Built for deep autonomous research.</p>
      </div>
    </footer>
  );
}

export default Footer;
