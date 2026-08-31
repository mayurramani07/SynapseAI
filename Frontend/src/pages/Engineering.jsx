import { motion } from "framer-motion";
import { useState } from "react";
import { Layers, Cpu, ShieldCheck, RefreshCw, Maximize2, X } from "lucide-react";
import workflow from "../assets/workflow.png";

export default function Engineering() {
  const [expanded, setExpanded] = useState(false);

  return (
    <main className="engineering-page">
      <div className="bg-glow purple"></div>
      <div className="bg-glow blue"></div>

      <section className="engineering-hero">
        <span className="engineering-badge">SYSTEM ARCHITECTURE</span>
        <h1>Multi-Agent Intelligence Architecture</h1>
        <p className="engineering-subtext">
          SynapseAI uses an 8-stage autonomous pipeline combining real-time web search, LLM failover pools, evidence grounding, and self-critique.
        </p>

        <div className="engineering-tags">
          <span className="tag"><Layers size={13} /> Multi-Agent Swarm</span>
          <span className="tag"><Cpu size={13} /> Parallel Execution</span>
          <span className="tag"><ShieldCheck size={13} /> Evidence Grounding</span>
          <span className="tag"><RefreshCw size={13} /> LLM Failover Pool</span>
        </div>
      </section>

      {/* ARCHITECTURE SUMMARY CARDS */}
      <div className="arch-cards-grid">
        <div className="arch-card">
          <div className="arch-icon purple">
            <Cpu size={20} />
          </div>
          <h3>1. Search & Scraping Layer</h3>
          <p>Ranks sources by domain authority (.gov, .edu, IEEE) and extracts clean content using BeautifulSoup, PyPDF, and Jina Reader cloud bypass.</p>
        </div>

        <div className="arch-card">
          <div className="arch-icon cyan">
            <ShieldCheck size={20} />
          </div>
          <h3>2. Reasoning & Grounding</h3>
          <p>Extracts claim-level evidence and cross-verifies confidence scores against original source content with structured JSON Mode enforcement.</p>
        </div>

        <div className="arch-card">
          <div className="arch-icon blue">
            <RefreshCw size={20} />
          </div>
          <h3>3. Critic & Self-Improvement</h3>
          <p>Evaluates initial reports for analytical gaps. If score &lt; 8.0/10, the Improver agent rewrites the report incorporating feedback.</p>
        </div>
      </div>

      {/* WORKFLOW DIAGRAM CONTAINER */}
      <section className="workflow-section">
        <div className="workflow-header">
          <h2>Detailed Workflow Diagram</h2>
          <button className="expand-btn" onClick={() => setExpanded(true)}>
            <Maximize2 size={14} />
            <span>Expand View</span>
          </button>
        </div>

        <motion.div
          className="workflow-container"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          onClick={() => setExpanded(true)}
        >
          <img
            src={workflow}
            alt="SynapseAI Architecture Workflow Diagram"
            className="workflow-image"
          />
          <div className="workflow-overlay">
            <span>Click to Enlarge Diagram</span>
          </div>
        </motion.div>
      </section>

      {/* MODAL VIEW */}
      {expanded && (
        <div className="workflow-modal" onClick={() => setExpanded(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-btn" onClick={() => setExpanded(false)}>
              <X size={18} />
            </button>
            <img
              src={workflow}
              alt="Expanded SynapseAI Workflow Architecture Diagram"
              className="expanded-image"
            />
          </div>
        </div>
      )}
    </main>
  );
}