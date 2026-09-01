import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  ShieldCheck,
  Globe,
  Lightbulb,
  Share2,
  Code2,
  Check,
  Copy,
  ExternalLink,
  Info,
  Maximize2,
  Filter,
  Sparkles
} from "lucide-react";

export default function KnowledgeGraph({ topic, evidenceList = [], reasoning = "", insights = "" }) {
  const [activeMode, setActiveMode] = useState("canvas"); // "canvas" | "mermaid"
  const [selectedNode, setSelectedNode] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState("all"); // "all" | "evidence" | "sources" | "insights"
  const [copiedMermaid, setCopiedMermaid] = useState(false);

  // Extract Domain from URL helper
  const getDomain = (url) => {
    if (!url || typeof url !== "string") return "Search Source";
    try {
      const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
      return parsed.hostname.replace(/^www\./, "");
    } catch {
      return url.split("/")[0] || "Search Source";
    }
  };

  // Build Structured Nodes & Links
  const graphData = useMemo(() => {
    const nodes = [];
    const links = [];

    // 1. Central Topic Node
    const rootId = "root";
    nodes.push({
      id: rootId,
      label: topic || "Research Topic",
      type: "root",
      category: "Topic",
      desc: "Central subject of autonomous research analysis."
    });

    // 2. Unique Sources
    const sourceMap = new Map();
    evidenceList.forEach((e, idx) => {
      const domain = getDomain(e.source_url);
      if (!sourceMap.has(domain)) {
        const sourceId = `src-${sourceMap.size + 1}`;
        sourceMap.set(domain, { id: sourceId, domain, rawUrl: e.source_url });
        nodes.push({
          id: sourceId,
          label: domain,
          type: "source",
          category: "Source Domain",
          rawUrl: e.source_url,
          desc: `Source Domain referenced in research citations.`
        });
        links.push({ source: rootId, target: sourceId, relation: "indexed from" });
      }
    });

    // 3. Evidence Claims
    evidenceList.slice(0, 6).forEach((item, idx) => {
      const evId = `ev-${idx + 1}`;
      const domain = getDomain(item.source_url);
      const parentSource = sourceMap.get(domain)?.id || rootId;
      const confidence = item.grounding?.confidence
        ? Math.round(item.grounding.confidence * 100)
        : 85;

      nodes.push({
        id: evId,
        label: item.claim?.slice(0, 55) + (item.claim?.length > 55 ? "..." : "") || `Evidence Claim #${idx + 1}`,
        fullText: item.claim,
        supportingText: item.supporting_text,
        type: "evidence",
        category: "Evidence Claim",
        evidenceType: item.evidence_type || "Fact",
        confidence,
        sourceUrl: item.source_url,
        domain
      });

      links.push({ source: parentSource, target: evId, relation: "supports claim" });
    });

    // 4. Strategic Insights
    if (typeof insights === "string" && insights.trim()) {
      const insightLines = insights
        .split("\n")
        .map((line) => line.replace(/^[#*\-•\d.\s]+/, "").trim())
        .filter((line) => line.length > 20 && !line.toLowerCase().startsWith("insight"))
        .slice(0, 3);

      insightLines.forEach((insText, idx) => {
        const insId = `ins-${idx + 1}`;
        nodes.push({
          id: insId,
          label: insText.slice(0, 50) + (insText.length > 50 ? "..." : ""),
          fullText: insText,
          type: "insight",
          category: "Analytical Insight",
          desc: "Key strategic deduction synthesized across verified claims."
        });
        links.push({ source: rootId, target: insId, relation: "yields insight" });
      });
    }

    return { nodes, links };
  }, [topic, evidenceList, insights]);

  // Filtered Nodes
  const filteredNodes = useMemo(() => {
    if (categoryFilter === "all") return graphData.nodes;
    return graphData.nodes.filter(
      (n) => n.type === "root" || n.type === categoryFilter
    );
  }, [graphData, categoryFilter]);

  // Generate Mermaid Diagram String
  const mermaidSyntax = useMemo(() => {
    const lines = [
      "graph TD",
      "  %% SynapseAI Knowledge Topology",
      "  classDef rootStyle fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff;",
      "  classDef srcStyle fill:#0f172a,stroke:#38bdf8,stroke-width:1.5px,color:#bae6fd;",
      "  classDef evStyle fill:#064e3b,stroke:#34d399,stroke-width:1.5px,color:#a7f3d0;",
      "  classDef insStyle fill:#451a03,stroke:#fbbf24,stroke-width:1.5px,color:#fef08a;"
    ];

    const sanitize = (text) => (text || "").replace(/["'()]/g, "").slice(0, 40);

    const rootLabel = sanitize(topic || "Research Topic");
    lines.push(`  root["🧠 ${rootLabel}"]:::rootStyle`);

    graphData.nodes.forEach((node) => {
      if (node.type === "source") {
        lines.push(`  ${node.id}["🌐 ${sanitize(node.label)}"]:::srcStyle`);
      } else if (node.type === "evidence") {
        lines.push(`  ${node.id}["🔍 ${sanitize(node.label)} (${node.confidence}% Conf)"]:::evStyle`);
      } else if (node.type === "insight") {
        lines.push(`  ${node.id}["💡 ${sanitize(node.label)}"]:::insStyle`);
      }
    });

    graphData.links.forEach((link) => {
      lines.push(`  ${link.source} -->|" ${link.relation} "| ${link.target}`);
    });

    return lines.join("\n");
  }, [graphData, topic]);

  const handleCopyMermaid = async () => {
    await navigator.clipboard.writeText(mermaidSyntax);
    setCopiedMermaid(true);
    setTimeout(() => setCopiedMermaid(false), 1800);
  };

  return (
    <div className="knowledge-graph-wrapper">
      {/* GRAPH HEADER CONTROLS */}
      <div className="graph-toolbar">
        <div className="mode-toggle">
          <button
            className={`mode-btn ${activeMode === "canvas" ? "active" : ""}`}
            onClick={() => setActiveMode("canvas")}
          >
            <Share2 size={15} />
            <span>Interactive Map</span>
          </button>
          <button
            className={`mode-btn ${activeMode === "mermaid" ? "active" : ""}`}
            onClick={() => setActiveMode("mermaid")}
          >
            <Code2 size={15} />
            <span>Mermaid Syntax</span>
          </button>
        </div>

        {activeMode === "canvas" && (
          <div className="filter-group">
            <Filter size={13} className="filter-icon" />
            <button
              className={`filter-pill ${categoryFilter === "all" ? "active" : ""}`}
              onClick={() => setCategoryFilter("all")}
            >
              All ({graphData.nodes.length})
            </button>
            <button
              className={`filter-pill ${categoryFilter === "evidence" ? "active" : ""}`}
              onClick={() => setCategoryFilter("evidence")}
            >
              Evidence ({graphData.nodes.filter((n) => n.type === "evidence").length})
            </button>
            <button
              className={`filter-pill ${categoryFilter === "source" ? "active" : ""}`}
              onClick={() => setCategoryFilter("source")}
            >
              Sources ({graphData.nodes.filter((n) => n.type === "source").length})
            </button>
            <button
              className={`filter-pill ${categoryFilter === "insight" ? "active" : ""}`}
              onClick={() => setCategoryFilter("insight")}
            >
              Insights ({graphData.nodes.filter((n) => n.type === "insight").length})
            </button>
          </div>
        )}
      </div>

      {/* CANVAS VIEW MODE */}
      {activeMode === "canvas" ? (
        <div className="graph-canvas-container">
          <div className="graph-nodes-grid">
            {filteredNodes.map((node) => {
              const isSelected = selectedNode?.id === node.id;
              let icon = <Brain size={18} />;
              let badgeColor = "purple";

              if (node.type === "source") {
                icon = <Globe size={18} />;
                badgeColor = "cyan";
              } else if (node.type === "evidence") {
                icon = <ShieldCheck size={18} />;
                badgeColor = "emerald";
              } else if (node.type === "insight") {
                icon = <Lightbulb size={18} />;
                badgeColor = "amber";
              }

              return (
                <motion.div
                  key={node.id}
                  layout
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  className={`graph-node-card ${node.type} ${isSelected ? "selected" : ""}`}
                  onClick={() => setSelectedNode(node)}
                >
                  <div className={`node-icon-wrapper ${badgeColor}`}>
                    {icon}
                  </div>
                  <div className="node-info">
                    <span className={`node-type-tag ${badgeColor}`}>
                      {node.category}
                    </span>
                    <h4 className="node-title">{node.label}</h4>
                    {node.confidence && (
                      <span className="confidence-pill">
                        ⚡ {node.confidence}% Verified
                      </span>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* NODE INSPECTOR DRAWER / CARD */}
          <AnimatePresence>
            {selectedNode && (
              <motion.div
                className="node-inspector-panel"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
              >
                <div className="inspector-header">
                  <span className="inspector-label">
                    <Sparkles size={14} /> Node Details
                  </span>
                  <button className="close-btn" onClick={() => setSelectedNode(null)}>
                    ×
                  </button>
                </div>

                <div className="inspector-body">
                  <h3 className="inspector-title">{selectedNode.fullText || selectedNode.label}</h3>

                  <div className="inspector-meta">
                    <div className="meta-badge">
                      <span className="meta-key">Type:</span>
                      <span className="meta-val">{selectedNode.category}</span>
                    </div>

                    {selectedNode.confidence && (
                      <div className="meta-badge">
                        <span className="meta-key">Grounding:</span>
                        <span className="meta-val emerald-text">{selectedNode.confidence}% Verified</span>
                      </div>
                    )}
                  </div>

                  {selectedNode.supportingText && (
                    <div className="inspector-quote">
                      <p className="quote-label">Supporting Grounded Excerpt:</p>
                      <blockquote>"{selectedNode.supportingText}"</blockquote>
                    </div>
                  )}

                  {selectedNode.sourceUrl && (
                    <a
                      href={selectedNode.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="source-link-btn"
                      title={selectedNode.sourceUrl}
                    >
                      <ExternalLink size={14} className="flex-shrink-0" />
                      <span className="source-link-text">Visit Source ({selectedNode.domain})</span>
                    </a>
                  )}

                  {selectedNode.desc && !selectedNode.supportingText && (
                    <p className="inspector-desc">{selectedNode.desc}</p>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ) : (
        /* MERMAID DIAGRAM CODE MODE */
        <div className="mermaid-view-container">
          <div className="mermaid-header">
            <div className="mermaid-title">
              <Code2 size={16} />
              <span>Mermaid Flowchart Syntax</span>
            </div>
            <button className="action-btn copy-mermaid-btn" onClick={handleCopyMermaid}>
              {copiedMermaid ? <Check size={14} className="text-success" /> : <Copy size={14} />}
              <span>{copiedMermaid ? "Copied!" : "Copy Mermaid Code"}</span>
            </button>
          </div>
          <pre className="mermaid-code-box">
            <code>{mermaidSyntax}</code>
          </pre>
        </div>
      )}
    </div>
  );
}
