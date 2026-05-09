import { useState } from "react";
import { motion } from "framer-motion";
import { FileText, Copy, Download, Check } from "lucide-react";

function ReportPanel({ topic, completed, result }) {
  const [copied, setCopied] = useState(false);

  const finalReport = result?.final_report || "";
  const reasoning = result?.reasoning || "";
  const evidence = result?.evidence || "";
  const insights = result?.insights || "";
  const feedback = result?.feedback || "";

  const fullReport = `
TOPIC:
${topic}

FINAL IMPROVED REPORT:
${finalReport}

REASONING:
${reasoning}

EVIDENCE:
${evidence}

INSIGHTS:
${insights}

CRITIC FEEDBACK:
${feedback}
`.trim();

  const handleCopy = async () => {
    if (!completed || !fullReport) return;

    await navigator.clipboard.writeText(fullReport);
    setCopied(true);

    setTimeout(() => {
      setCopied(false);
    }, 1500);
  };

  const handleDownload = () => {
    if (!completed || !fullReport) return;

    const blob = new Blob([fullReport], {
      type: "text/plain;charset=utf-8",
    });

    const url = URL.createObjectURL(blob);

    const fileName = topic
      .replace(/[^a-z0-9]/gi, "_")
      .toLowerCase();

    const link = document.createElement("a");
    link.href = url;
    link.download = `${fileName || "research_report"}.txt`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
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
          <button
            onClick={handleCopy}
            disabled={!completed}
            className={!completed ? "disabled-btn" : ""}
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
            {copied ? "Copied" : "Copy"}
          </button>

          <button
            onClick={handleDownload}
            disabled={!completed}
            className={!completed ? "disabled-btn" : ""}
          >
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