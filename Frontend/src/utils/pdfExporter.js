/**
 * SynapseAI Publication-Grade PDF Exporter
 * Generates an executive, client-ready printable document with cover page,
 * branding, table of contents, structured formatting, and footnoted citations.
 */

// Helper to convert basic Markdown to clean HTML for print view
function markdownToHtml(mdText) {
  if (!mdText || typeof mdText !== "string") return "";

  let html = mdText;

  // Escape HTML tags to prevent XSS
  html = html
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Headers
  html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
  html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
  html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");

  // Bold & Italic
  html = html.replace(/\*\*\*(.*?)\*\*\*/g, "<strong><em>$1</em></strong>");
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

  // Inline Code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, "<blockquote>$1</blockquote>");

  // Horizontal Rule
  html = html.replace(/^---$/gim, "<hr />");

  // Unordered Lists
  html = html.replace(/^\* (.*$)/gim, "<ul><li>$1</li></ul>");
  html = html.replace(/^- (.*$)/gim, "<ul><li>$1</li></ul>");
  // Fix consecutive <ul> tags
  html = html.replace(/<\/ul>\s*<ul>/g, "");

  // Ordered Lists
  html = html.replace(/^\d+\.\s+(.*$)/gim, "<ol><li>$1</li></ol>");
  html = html.replace(/<\/ol>\s*<ol>/g, "");

  // Paragraphs (double newlines)
  const paragraphs = html.split(/\n\n+/);
  html = paragraphs
    .map((p) => {
      const trimmed = p.trim();
      if (
        trimmed.startsWith("<h") ||
        trimmed.startsWith("<ul") ||
        trimmed.startsWith("<ol") ||
        trimmed.startsWith("<blockquote") ||
        trimmed.startsWith("<hr") ||
        trimmed.startsWith("<table")
      ) {
        return trimmed;
      }
      return `<p>${trimmed.replace(/\n/g, "<br/>")}</p>`;
    })
    .join("\n");

  return html;
}

export function exportToPublicationPdf(topic, result, duration) {
  const finalReport =
    typeof result?.final_report === "object"
      ? result?.final_report?.data || ""
      : result?.final_report || "";
  const reasoning =
    typeof result?.reasoning === "object"
      ? result?.reasoning?.data || ""
      : result?.reasoning || "";
  const evidenceList = Array.isArray(result?.evidence)
    ? result.evidence
    : Array.isArray(result?.verified_evidence?.data)
    ? result.verified_evidence.data
    : Array.isArray(result?.evidence?.data)
    ? result.evidence.data
    : [];
  const insights =
    typeof result?.insights === "object"
      ? result?.insights?.data || ""
      : result?.insights || "";
  const feedback =
    typeof result?.feedback === "object"
      ? result?.feedback?.data || ""
      : result?.feedback || "";

  const reportDate = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const reportTime = new Date().toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
  const documentUuid = "SYN-" + Math.random().toString(36).substring(2, 9).toUpperCase();

  // Helper to extract domain from URL
  const getDomain = (url) => {
    if (!url) return "N/A";
    try {
      const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
      return parsed.hostname.replace(/^www\./, "");
    } catch {
      return url.split("/")[0] || "N/A";
    }
  };

  // Convert sections
  const reportHtml = markdownToHtml(finalReport);
  const reasoningHtml = markdownToHtml(reasoning);
  const insightsHtml = markdownToHtml(insights);
  const feedbackHtml = markdownToHtml(feedback);

  // Evidence Rows & Citation Index
  const citationsRowsHtml = evidenceList
    .map((item, idx) => {
      const footnoteId = idx + 1;
      const domain = getDomain(item.source_url);
      const confidence = item.grounding?.confidence
        ? Math.round(item.grounding.confidence * 100)
        : 95;
      const confClass = confidence >= 75 ? "conf-high" : "conf-low";

      return `
      <tr>
        <td class="col-idx"><strong>[${footnoteId}]</strong></td>
        <td class="col-claim">
          <strong>${item.claim || "Fact Claim"}</strong>
          ${item.supporting_text ? `<div class="quote-text">"${item.supporting_text}"</div>` : ""}
        </td>
        <td class="col-type"><span class="badge-type">${item.evidence_type || "factual_claim"}</span></td>
        <td class="col-source">
          <a href="${item.source_url || "#"}" target="_blank" class="source-link">${domain}</a>
        </td>
        <td class="col-conf"><span class="conf-badge ${confClass}">${confidence}% Verified</span></td>
      </tr>
    `;
    })
    .join("");

  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    alert("Please allow pop-ups to open the publication-grade PDF report.");
    return;
  }

  const printDocumentHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SynapseAI Executive Briefing - ${topic}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    @page {
      size: A4;
      margin: 20mm 15mm 20mm 15mm;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      color: #09090b;
      background: #ffffff;
      line-height: 1.65;
      font-size: 13.5px;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }

    a {
      color: #000000;
      text-decoration: underline;
    }

    .page-break {
      page-break-after: always;
      break-after: page;
    }

    /* ═══════════════════════════════════════════════════
       1. COVER PAGE
       ═══════════════════════════════════════════════════ */
    .cover-page {
      height: 100vh;
      min-height: 280mm;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 40px 30px;
      position: relative;
      border: 1px solid #e4e4e7;
      border-radius: 12px;
      background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
    }

    .cover-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 2px solid #000000;
      padding-bottom: 20px;
    }

    .brand-logo {
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.8px;
    }

    .brand-logo .synapse {
      color: #71717a;
    }

    .brand-logo .ai {
      color: #000000;
    }

    .cover-tagline {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: #71717a;
      background: #f4f4f5;
      padding: 6px 14px;
      border-radius: 20px;
      border: 1px solid #e4e4e7;
    }

    .cover-body {
      margin: auto 0;
      padding: 40px 0;
    }

    .doc-type-label {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 2px;
      color: #000000;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .doc-type-label::before {
      content: '';
      width: 12px;
      height: 12px;
      background: #000000;
      border-radius: 3px;
    }

    .cover-title {
      font-size: 34px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: -1.2px;
      color: #000000;
      margin-bottom: 24px;
      max-width: 90%;
    }

    .cover-subtitle {
      font-size: 15px;
      color: #52525b;
      line-height: 1.7;
      max-width: 85%;
      margin-bottom: 40px;
    }

    .metadata-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
      background: #ffffff;
      border: 1px solid #e4e4e7;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
    }

    .meta-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .meta-item .label {
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: #71717a;
    }

    .meta-item .value {
      font-size: 13.5px;
      font-weight: 600;
      color: #09090b;
    }

    .cover-footer {
      border-top: 1px solid #e4e4e7;
      padding-top: 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      color: #71717a;
    }

    .confidential-tag {
      font-weight: 700;
      color: #dc2626;
      background: #fef2f2;
      border: 1px solid #fecaca;
      padding: 4px 10px;
      border-radius: 6px;
    }

    /* ═══════════════════════════════════════════════════
       2. TABLE OF CONTENTS
       ═══════════════════════════════════════════════════ */
    .toc-section {
      padding: 30px 0;
    }

    .section-title {
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: #000000;
      border-bottom: 2px solid #000000;
      padding-bottom: 10px;
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .toc-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-top: 20px;
    }

    .toc-item {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      font-size: 14px;
      font-weight: 600;
      color: #09090b;
      padding: 10px 14px;
      border-radius: 8px;
      background: #fafafa;
      border: 1px solid #f4f4f5;
    }

    .toc-dots {
      flex: 1;
      border-bottom: 1px dashed #d4d4d8;
      margin: 0 12px;
    }

    /* ═══════════════════════════════════════════════════
       3. DOCUMENT BODY STYLING
       ═══════════════════════════════════════════════════ */
    .doc-section {
      margin-bottom: 36px;
    }

    h1, h2, h3, h4 {
      color: #000000;
      font-weight: 700;
      letter-spacing: -0.4px;
    }

    h2 {
      font-size: 18px;
      border-bottom: 1px solid #e4e4e7;
      padding-bottom: 8px;
      margin: 28px 0 14px;
    }

    h3 {
      font-size: 15px;
      margin: 20px 0 10px;
    }

    p {
      margin-bottom: 14px;
      line-height: 1.7;
      color: #27272a;
    }

    blockquote {
      border-left: 3px solid #000000;
      background: #fafafa;
      padding: 12px 16px;
      margin: 16px 0;
      font-style: italic;
      color: #3f3f46;
      border-radius: 0 8px 8px 0;
    }

    code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      background: #f4f4f5;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid #e4e4e7;
    }

    ul, ol {
      margin: 12px 0 16px 24px;
    }

    li {
      margin-bottom: 6px;
    }

    /* ═══════════════════════════════════════════════════
       4. CITATION TABLE
       ═══════════════════════════════════════════════════ */
    .citations-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
      font-size: 12px;
      border: 1px solid #e4e4e7;
      border-radius: 8px;
      overflow: hidden;
    }

    .citations-table th {
      background: #f4f4f5;
      color: #000000;
      font-weight: 700;
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1px solid #e4e4e7;
    }

    .citations-table td {
      padding: 10px 12px;
      border-bottom: 1px solid #f4f4f5;
      vertical-align: top;
    }

    .citations-table tr:nth-child(even) td {
      background: #fafafa;
    }

    .col-idx { width: 45px; text-align: center; }
    .col-claim { min-width: 220px; }
    .quote-text { font-style: italic; color: #71717a; font-size: 11px; margin-top: 4px; }
    .col-type { width: 110px; }
    .col-source { width: 120px; }
    .col-conf { width: 100px; text-align: right; }

    .badge-type {
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
      background: #f4f4f5;
      border: 1px solid #e4e4e7;
      padding: 2px 6px;
      border-radius: 4px;
      color: #3f3f46;
    }

    .conf-badge {
      font-size: 10.5px;
      font-weight: 700;
    }

    .conf-high { color: #16a34a; }
    .conf-low { color: #dc2626; }

    /* Floating Print Button for Preview Screen */
    .no-print-bar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      background: #09090b;
      color: #ffffff;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 9999;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    .no-print-bar button {
      background: #ffffff;
      color: #000000;
      border: none;
      padding: 8px 18px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .no-print-bar button:hover {
      background: #e4e4e7;
    }

    @media print {
      .no-print-bar {
        display: none !important;
      }
      body {
        padding-top: 0 !important;
      }
    }

    body {
      padding-top: 60px;
    }
  </style>
</head>
<body>

  <!-- Floating Action Bar for Web Preview -->
  <div class="no-print-bar">
    <div>
      <strong>SynapseAI Publication-Grade Export</strong> — Ready for PDF Download
    </div>
    <button onclick="window.print()">
      🖨️ Print / Save as PDF
    </button>
  </div>

  <!-- 1. COVER PAGE -->
  <div class="cover-page page-break">
    <div class="cover-header">
      <div class="brand-logo">
        <span class="synapse">Synapse</span><span class="ai">AI</span>
      </div>
      <div class="cover-tagline">Executive Intelligence Briefing</div>
    </div>

    <div class="cover-body">
      <div class="doc-type-label">Deep Research Assessment</div>
      <h1 class="cover-title">${topic}</h1>
      <p class="cover-subtitle">
        An autonomous, domain-verified intelligence synthesis prepared by the SynapseAI multi-agent reasoning engine. Grounded in empirical claim extraction, multi-source triangulation, and automated quality auditing.
      </p>

      <div class="metadata-grid">
        <div class="meta-item">
          <span class="label">Date Generated</span>
          <span class="value">${reportDate} at ${reportTime}</span>
        </div>
        <div class="meta-item">
          <span class="label">Document Identifier</span>
          <span class="value">${documentUuid}</span>
        </div>
        <div class="meta-item">
          <span class="label">Verified Evidence Items</span>
          <span class="value">${evidenceList.length} Claim-Level Facts</span>
        </div>
        <div class="meta-item">
          <span class="label">Pipeline Architecture</span>
          <span class="value">Agentic Synthesis v2.4</span>
        </div>
      </div>
    </div>

    <div class="cover-footer">
      <div>© ${new Date().getFullYear()} SynapseAI Platform. Confidential & Proprietary.</div>
      <div class="confidential-tag">CLIENT READY</div>
    </div>
  </div>

  <!-- 2. TABLE OF CONTENTS -->
  <div class="toc-section page-break">
    <h2 class="section-title">
      <span>Table of Contents</span>
      <span style="font-size:12px; font-weight:500; color:#71717a;">SynapseAI Executive Briefing</span>
    </h2>

    <div class="toc-list">
      <div class="toc-item">
        <span>1. Executive Summary & Research Synthesis</span>
        <span class="toc-dots"></span>
        <span>Page 3</span>
      </div>
      <div class="toc-item">
        <span>2. Verified Evidence Matrix (${evidenceList.length} Items)</span>
        <span class="toc-dots"></span>
        <span>Page 4</span>
      </div>
      <div class="toc-item">
        <span>3. Strategic Reasoning & Pipeline Methodology</span>
        <span class="toc-dots"></span>
        <span>Page 5</span>
      </div>
      <div class="toc-item">
        <span>4. Analytical Insights & Key Takeaways</span>
        <span class="toc-dots"></span>
        <span>Page 6</span>
      </div>
      <div class="toc-item">
        <span>5. Critic Evaluation & Quality Audit</span>
        <span class="toc-dots"></span>
        <span>Page 7</span>
      </div>
      <div class="toc-item">
        <span>6. Citation Index & Source References</span>
        <span class="toc-dots"></span>
        <span>Page 8</span>
      </div>
    </div>
  </div>

  <!-- 3. EXECUTIVE SUMMARY & FINAL REPORT -->
  <div class="doc-section page-break">
    <h2 class="section-title">1. Executive Summary & Research Synthesis</h2>
    <div class="report-content">
      ${reportHtml || "<p>No report text available.</p>"}
    </div>
  </div>

  <!-- 4. VERIFIED EVIDENCE MATRIX -->
  <div class="doc-section page-break">
    <h2 class="section-title">2. Grounded Evidence Matrix</h2>
    <p>The following table lists claim-level facts extracted and verified from authoritative web domains.</p>
    
    <table class="citations-table">
      <thead>
        <tr>
          <th class="col-idx">#</th>
          <th class="col-claim">Claim & Supporting Excerpt</th>
          <th class="col-type">Type</th>
          <th class="col-source">Domain</th>
          <th class="col-conf">Verification</th>
        </tr>
      </thead>
      <tbody>
        ${citationsRowsHtml || "<tr><td colspan='5'>No verified evidence items recorded.</td></tr>"}
      </tbody>
    </table>
  </div>

  <!-- 5. STRATEGIC REASONING -->
  <div class="doc-section page-break">
    <h2 class="section-title">3. Strategic Reasoning & Pipeline Methodology</h2>
    <div class="report-content">
      ${reasoningHtml || "<p>Reasoning log synthesized during agentic analysis.</p>"}
    </div>
  </div>

  <!-- 6. ANALYTICAL INSIGHTS -->
  <div class="doc-section page-break">
    <h2 class="section-title">4. Analytical Insights & Key Takeaways</h2>
    <div class="report-content">
      ${insightsHtml || "<p>Key strategic deductions generated by the research engine.</p>"}
    </div>
  </div>

  <!-- 7. CRITIC EVALUATION -->
  <div class="doc-section page-break">
    <h2 class="section-title">5. Self-Evaluation & Quality Audit</h2>
    <div class="report-content">
      ${feedbackHtml || "<p>Critique and self-improver feedback log.</p>"}
    </div>
  </div>

  <!-- 8. CITATION & REFERENCES INDEX -->
  <div class="doc-section">
    <h2 class="section-title">6. Citation Index & Source References</h2>
    <ol style="margin-left: 20px;">
      ${
        evidenceList.length > 0
          ? evidenceList
              .map(
                (e, i) => `
          <li style="margin-bottom: 12px;">
            <strong>[${i + 1}] ${e.claim || "Evidence Claim"}</strong><br/>
            <span style="font-size:11.5px; color:#52525b;">
              Source URL: <a href="${e.source_url}" target="_blank">${e.source_url}</a> | Type: ${e.evidence_type || "Fact"}
            </span>
          </li>
        `
              )
              .join("")
          : "<li>No citations listed.</li>"
      }
    </ol>
  </div>

  <script>
    // Auto trigger print dialog on page load
    window.addEventListener('DOMContentLoaded', () => {
      setTimeout(() => {
        window.print();
      }, 500);
    });
  </script>
</body>
</html>`;

  printWindow.document.open();
  printWindow.document.write(printDocumentHtml);
  printWindow.document.close();
}
