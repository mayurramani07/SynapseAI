import { motion } from "framer-motion";
import { FileText, Copy, Download } from "lucide-react";

function ReportPanel({ topic, completed, result }) {
  const finalReport = result?.final_report || "";
  const reasoning = result?.reasoning || "";
  const evidence = result?.evidence || "";
  const insights = result?.insights || "";
  const feedback = result?.feedback || "";

  const handleCopy = () => {
    navigator.clipboard.writeText(finalReport);
  };

  return (
    <motion.div
      className="report-panel"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="report-header">
        <div>
          <span className="report-label">
            <FileText size={16} />
            Final Research Report
          </span>
          <h2>{topic}</h2>
        </div>

        <div className="report-actions">
          <button onClick={handleCopy}>
            <Copy size={16} />
            Copy
          </button>

          <button>
            <Download size={16} />
            Export
          </button>
        </div>
      </div>

      {!completed ? (
        <div className="report-waiting">
          <div>
            <div className="pulse-orb"></div>
            <p>Running AI research pipeline...</p>
          </div>
        </div>
      ) : (
        <div className="report-content">
          <h3>Final Improved Report</h3>
          <pre>{finalReport}</pre>

          <h3>Reasoning</h3>
          <pre>{reasoning}</pre>

          <h3>Evidence</h3>
          <pre>{evidence}</pre>

          <h3>Insights</h3>
          <pre>{insights}</pre>

          <h3>Critic Feedback</h3>
          <pre>{feedback}</pre>
        </div>
      )}
    </motion.div>
  );
}

export default ReportPanel;