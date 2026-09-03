import { useState, useEffect } from "react";
import { Shield, Lock, ArrowRight, AlertCircle, KeyRound } from "lucide-react";
import { verifyAdminPasscode } from "../api/telemetry";

function AdminGuard({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [passcode, setPasscode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const saved = sessionStorage.getItem("synapse_admin_passcode");
    if (saved) {
      verifyAdminPasscode(saved)
        .then(() => setIsAuthenticated(true))
        .catch(() => sessionStorage.removeItem("synapse_admin_passcode"));
    }
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!passcode.trim()) return;
    setError("");
    setLoading(true);

    try {
      await verifyAdminPasscode(passcode.trim());
      sessionStorage.setItem("synapse_admin_passcode", passcode.trim());
      setIsAuthenticated(true);
    } catch (err) {
      setError(err.message || "Invalid Admin Passcode.");
    } finally {
      setLoading(false);
    }
  };

  if (isAuthenticated) {
    return children;
  }

  return (
    <div className="admin-lock-screen">
      <div className="bg-glow purple"></div>
      <div className="bg-glow blue"></div>

      <div className="admin-lock-card">
        <div className="lock-icon-badge">
          <Shield size={28} className="shield-glow-icon" />
        </div>

        <h2>Restricted Telemetry Access</h2>
        <p className="lock-subtext">
          Enter your Admin Security Key to access Grafana system telemetry, LLM token metrics, and real-time execution logs.
        </p>

        {error && (
          <div className="lock-error-alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="lock-form">
          <div className="passcode-input-wrapper">
            <KeyRound size={18} className="key-input-icon" />
            <input
              type="password"
              placeholder="Enter Admin Passcode..."
              value={passcode}
              onChange={(e) => setPasscode(e.target.value)}
              autoFocus
            />
          </div>

          <button type="submit" className="lock-submit-btn" disabled={loading}>
            {loading ? (
              <span>Authenticating...</span>
            ) : (
              <>
                <span>Unlock Grafana Dashboard</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>

          {sessionStorage.getItem("synapse_admin_passcode") && (
            <button
              type="button"
              className="recent-clear-btn"
              style={{ marginTop: "12px", width: "100%", justifyContent: "center" }}
              onClick={() => {
                sessionStorage.removeItem("synapse_admin_passcode");
                setPasscode("");
                setError("Stored session cleared. Please enter your new passcode.");
              }}
            >
              <span>Clear Saved Passcode</span>
            </button>
          )}
        </form>
      </div>
    </div>
  );
}

export default AdminGuard;
