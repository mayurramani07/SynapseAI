import { motion } from "framer-motion";
import { FileText, Copy, Download } from "lucide-react";

function ReportPanel({ topic, completed }) {
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
          <h2>{topic || "Research Topic"}</h2>
        </div>

        <div className="report-actions">
          <button>
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
          <div className="pulse-orb"></div>
          <p>Report will appear here after the pipeline finishes...</p>
        </div>
      ) : (
        <div className="report-content">
          <h3>1. Introduction</h3>
          <p>
            This report analyzes the selected topic using a multi-stage AI research pipeline.
            The system combines search, scraping, reasoning, evidence extraction, insight generation,
            report writing, criticism, and improvement.
          </p>

          <h3>2. Methodology</h3>
          <p>
            SynapseAI first searches trusted sources, ranks URLs by credibility, extracts clean content,
            then passes the research data through specialized LLM chains.
          </p>

          <h3>3. Key Findings</h3>
          <ul>
            <li>Credible sources are prioritized before analysis.</li>
            <li>Evidence and insights are separated to reduce shallow summarization.</li>
            <li>A critic-improver loop improves final report quality.</li>
          </ul>

          <h3>4. Conclusion</h3>
          <p>
            The pipeline demonstrates a controlled agentic research workflow suitable for automated
            report generation and professional analysis.
          </p>
        </div>
      )}
    </motion.div>
  );
}

export default ReportPanel;