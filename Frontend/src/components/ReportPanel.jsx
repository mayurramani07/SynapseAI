import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  FileText,
  Copy,
  Download,
  Check,
  ShieldCheck,
  Brain,
  Lightbulb,
  Scale,
  ExternalLink,
  Code2,
  FileCode,
  Sparkles,
  MessageSquare,
  Send,
  ChevronDown,
  ChevronUp,
  Loader2
} from "lucide-react";
import { sendFollowUpQuestion } from "../api/research";

function ReportPanel({ topic, completed, result, duration, liveLog }) {
  const [activeTab, setActiveTab] = useState("report");
  const [copied, setCopied] = useState(false);
  const [exportFormat, setExportFormat] = useState(null);

  // Chat Drawer State
  const [chatOpen, setChatOpen] = useState(true);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  const finalReport = typeof result?.final_report === "object" ? (result?.final_report?.data || "") : (result?.final_report || "");
  const reasoning = typeof result?.reasoning === "object" ? (result?.reasoning?.data || "") : (result?.reasoning || "");
  const evidenceList = Array.isArray(result?.evidence)
    ? result.evidence
    : Array.isArray(result?.verified_evidence?.data)
    ? result.verified_evidence.data
    : Array.isArray(result?.evidence?.data)
    ? result.evidence.data
    : [];
  const insights = typeof result?.insights === "object" ? (result?.insights?.data || "") : (result?.insights || "");
  const feedback = typeof result?.feedback === "object" ? (result?.feedback?.data || "") : (result?.feedback || "");

  const handleSendChat = async (queryText) => {
    const question = queryText || chatInput;
    if (!question.trim() || chatLoading) return;

    const userMsg = { role: "user", text: question };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatLoading(true);

    try {
      const historyStr = chatMessages
        .map((m) => `${m.role.toUpperCase()}: ${m.text}`)
        .join("\n");

      const response = await sendFollowUpQuestion({
        topic,
        report: finalReport,
        evidence: evidenceList,
        question,
        history: historyStr,
      });

      const assistantMsg = { role: "assistant", text: response.answer };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: `⚠️ Error getting response: ${err.message}` },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleChatSubmit = (e) => {
    e.preventDefault();
    handleSendChat();
  };

  const fullMarkdownExport = `# SynapseAI Deep Research Report
Topic: ${topic}
Date: ${new Date().toLocaleDateString()}

---

## 📄 Final Improved Report
${finalReport}

---

## 🧠 Strategic Reasoning
${reasoning}

---

## 🔍 Verified Evidence (${evidenceList.length} Items)
${evidenceList
  .map(
    (e, idx) =>
      `### [${idx + 1}] ${e.claim}\n- **Type**: ${e.evidence_type}\n- **Supporting Text**: "${e.supporting_text}"\n- **Source**: ${e.source_url}\n`
  )
  .join("\n")}

---

## 💡 Analytical Insights
${insights}

---

## ⚖️ Critic Evaluation
${feedback}
`;

  const handleCopy = async () => {
    if (!completed || !finalReport) return;
    await navigator.clipboard.writeText(fullMarkdownExport);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const handleDownload = (format) => {
    if (!completed || !finalReport) return;

    let content = "";
    let mimeType = "text/plain;charset=utf-8";
    let extension = "txt";

    if (format === "json") {
      content = JSON.stringify(result, null, 2);
      mimeType = "application/json;charset=utf-8";
      extension = "json";
    } else if (format === "md") {
      content = fullMarkdownExport;
      mimeType = "text/markdown;charset=utf-8";
      extension = "md";
    } else {
      content = fullMarkdownExport;
      mimeType = "text/plain;charset=utf-8";
      extension = "txt";
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const fileName = topic.replace(/[^a-z0-9]/gi, "_").toLowerCase();

    const link = document.createElement("a");
    link.href = url;
    link.download = `${fileName || "synapse_research"}.${extension}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setExportFormat(null);
  };

  return (
    <motion.div
      className="report-panel"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="report-header">
        <div className="report-title-wrapper">
          <div className="report-label">
            <FileText size={16} />
            <span>Autonomous Intelligence Report</span>
          </div>
          <h2>{topic}</h2>
        </div>

        <div className="report-actions">
          <button
            onClick={handleCopy}
            disabled={!completed}
            className={`action-btn ${!completed ? "disabled" : ""}`}
            title="Copy Report to Clipboard"
          >
            {copied ? <Check size={16} className="text-success" /> : <Copy size={16} />}
            <span>{copied ? "Copied!" : "Copy"}</span>
          </button>

          <div className="export-dropdown-container">
            <button
              onClick={() => setExportFormat(exportFormat ? null : "open")}
              disabled={!completed}
              className={`action-btn primary ${!completed ? "disabled" : ""}`}
            >
              <Download size={16} />
              <span>Export</span>
            </button>

            {exportFormat && (
              <div className="export-menu">
                <button onClick={() => handleDownload("md")}>
                  <FileCode size={14} /> Markdown (.md)
                </button>
                <button onClick={() => handleDownload("txt")}>
                  <FileText size={14} /> Text (.txt)
                </button>
                <button onClick={() => handleDownload("json")}>
                  <Code2 size={14} /> Raw JSON (.json)
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {!completed ? (
        <div className="report-waiting">
          {/* MINI PRINTER ANIMATION */}
          <div className="printer-container">
            <div className="printer-top">
              <div className="paper-input"></div>
            </div>
            <div className="printer-body">
              <div className="printer-light"></div>
              <div className="printer-slot"></div>
            </div>
            <div className="printed-page-wrapper">
              <div className="printed-page">
                <div className="page-line title"></div>
                <div className="page-line short"></div>
                <div className="page-line"></div>
                <div className="page-line medium"></div>
                <div className="page-line"></div>
              </div>
            </div>
            <div className="printer-tray"></div>
          </div>

          <h3>Synthesizing Deep Research...</h3>
          <p className="live-ticker">{liveLog || "Initializing multi-agent intelligence pipeline..."}</p>
        </div>
      ) : (
        <div className="report-body">
          {/* TAB HEADERS */}
          <div className="tabs-header">
            <button
              className={`tab-btn ${activeTab === "report" ? "active" : ""}`}
              onClick={() => setActiveTab("report")}
            >
              <FileText size={16} />
              <span>Final Report</span>
            </button>

            <button
              className={`tab-btn ${activeTab === "evidence" ? "active" : ""}`}
              onClick={() => setActiveTab("evidence")}
            >
              <ShieldCheck size={16} />
              <span>Evidence Cards ({evidenceList.length})</span>
            </button>

            <button
              className={`tab-btn ${activeTab === "reasoning" ? "active" : ""}`}
              onClick={() => setActiveTab("reasoning")}
            >
              <Brain size={16} />
              <span>Reasoning</span>
            </button>

            <button
              className={`tab-btn ${activeTab === "insights" ? "active" : ""}`}
              onClick={() => setActiveTab("insights")}
            >
              <Lightbulb size={16} />
              <span>Insights</span>
            </button>

            <button
              className={`tab-btn ${activeTab === "critic" ? "active" : ""}`}
              onClick={() => setActiveTab("critic")}
            >
              <Scale size={16} />
              <span>Critic Evaluation</span>
            </button>
          </div>

          {/* TAB CONTENTS */}
          <div className="tab-content-area">
            <AnimatePresence mode="wait">
              {activeTab === "report" && (
                <motion.div
                  key="report"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="markdown-wrapper"
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{finalReport}</ReactMarkdown>
                </motion.div>
              )}

              {activeTab === "evidence" && (
                <motion.div
                  key="evidence"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="evidence-grid"
                >
                  {evidenceList.length === 0 ? (
                    <div className="empty-state">No verified evidence items recorded.</div>
                  ) : (
                    evidenceList.map((item, idx) => (
                      <div key={idx} className="evidence-card">
                        <div className="card-top">
                          <span className="evidence-badge-idx">Claim #{idx + 1}</span>
                          <span className={`evidence-type-badge ${item.evidence_type}`}>
                            {item.evidence_type || "factual_claim"}
                          </span>
                        </div>

                        <h4 className="claim-title">{item.claim}</h4>
                        <p className="supporting-text">"{item.supporting_text}"</p>

                        <div className="card-bottom">
                          {item.source_url && (
                            <a
                              href={item.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="source-chip"
                            >
                              <ExternalLink size={12} />
                              <span>{new URL(item.source_url).hostname}</span>
                            </a>
                          )}
                          <span className="confidence-tag">
                            <ShieldCheck size={14} /> 95% Verified
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </motion.div>
              )}

              {activeTab === "reasoning" && (
                <motion.div
                  key="reasoning"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="markdown-wrapper"
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{reasoning}</ReactMarkdown>
                </motion.div>
              )}

              {activeTab === "insights" && (
                <motion.div
                  key="insights"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="markdown-wrapper"
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{insights}</ReactMarkdown>
                </motion.div>
              )}

              {activeTab === "critic" && (
                <motion.div
                  key="critic"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="markdown-wrapper"
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{feedback}</ReactMarkdown>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ASK SYNAPSE - GROUNDED FOLLOW-UP CHAT DRAWER */}
          <div className="ask-synapse-drawer">
            <div className="drawer-header" onClick={() => setChatOpen(!chatOpen)}>
              <div className="drawer-title">
                <Sparkles size={16} className="sparkle-icon" />
                <span>Ask Synapse (Grounded Follow-up Assistant)</span>
              </div>
              <div className="drawer-toggle">
                {chatOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </div>
            </div>

            {chatOpen && (
              <div className="drawer-body">
                {chatMessages.length === 0 ? (
                  <div className="chat-suggestions">
                    <p className="suggestion-label">Suggested follow-up questions:</p>
                    <div className="chip-list">
                      <button onClick={() => handleSendChat("What are the key technical risks and trade-offs mentioned in the report?")}>
                        What are the key technical risks & trade-offs?
                      </button>
                      <button onClick={() => handleSendChat("Summarize the top verified evidence claims.")}>
                        Summarize the top verified evidence claims
                      </button>
                      <button onClick={() => handleSendChat("What actionable recommendations can we draw from this report?")}>
                        What actionable recommendations can we draw?
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="chat-messages-container">
                    {chatMessages.map((msg, index) => (
                      <div key={index} className={`chat-message ${msg.role}`}>
                        <div className="message-header">
                          {msg.role === "assistant" ? <Sparkles size={13} /> : <MessageSquare size={13} />}
                          <span>{msg.role === "assistant" ? "SynapseAI" : "You"}</span>
                        </div>
                        <div className="message-content">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                        </div>
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="chat-message assistant loading">
                        <Loader2 size={16} className="spin-icon" />
                        <span>Analyzing report and verified evidence...</span>
                      </div>
                    )}
                  </div>
                )}

                <form className="chat-input-row" onSubmit={handleChatSubmit}>
                  <input
                    type="text"
                    placeholder="Ask a question about this research report..."
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    disabled={chatLoading}
                  />
                  <button type="submit" disabled={!chatInput.trim() || chatLoading} className="chat-send-btn">
                    {chatLoading ? <Loader2 size={16} className="spin-icon" /> : <Send size={15} />}
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default ReportPanel;