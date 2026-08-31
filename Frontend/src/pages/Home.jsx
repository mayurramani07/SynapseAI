import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Search, Sparkles, ShieldCheck, FileText, Cpu, ArrowRight, Zap } from "lucide-react";

const SUGGESTED_TOPICS = [
  "Impact of Generative AI on Software Engineering Productivity",
  "Quantum Computing Applications in Financial Risk Modeling",
  "CRISPR Gene Editing Breakthroughs in Oncology Therapeutics",
  "Autonomous Agent Orchestration in Multi-Cloud Architectures",
];

function Home() {
  const [topic, setTopic] = useState("");
  const navigate = useNavigate();

  const handleStart = (selectedTopic) => {
    const targetTopic = selectedTopic || topic;
    if (!targetTopic.trim()) return;
    navigate("/research", { state: { topic: targetTopic.trim() } });
  };

  return (
    <main className="home">
      <div className="bg-glow purple"></div>
      <div className="bg-glow blue"></div>

      <section className="hero">
        <motion.div
          className="badge"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <Sparkles size={14} className="sparkle-icon" />
          <span>Autonomous AI Research Engine</span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
        >
          Deep research powered by an
          <span className="hero-gradient-text"> agentic intelligence pipeline.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          Search verified sources, extract structured evidence, reason over patterns, synthesize insights, and auto-critique reports with zero hallucinations.
        </motion.p>

        <motion.div
          className="search-container"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
        >
          <div className="search-box">
            <Search className="search-icon" size={20} />
            <input
              placeholder="Enter any complex research topic..."
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleStart()}
            />
            <button onClick={() => handleStart()} className="glow-btn">
              <span>Start Research</span>
              <ArrowRight size={16} />
            </button>
          </div>

          <div className="suggested-chips">
            <span className="chips-label">
              <Zap size={13} /> Try asking:
            </span>
            <div className="chips-wrapper">
              {SUGGESTED_TOPICS.map((suggested) => (
                <button
                  key={suggested}
                  className="chip-btn"
                  onClick={() => handleStart(suggested)}
                >
                  {suggested}
                </button>
              ))}
            </div>
          </div>
        </motion.div>

        {/* RECTANGULAR FEATURE CARDS */}
        <div className="feature-grid-rect">
          <motion.div
            className="feature-card-rect"
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
          >
            <div className="icon-wrapper purple">
              <ShieldCheck size={22} />
            </div>
            <div className="card-rect-content">
              <h3>Domain-Scored Search</h3>
              <p>Prioritizes high-authority domains (.gov, .edu, Nature, IEEE, World Bank) with automated provider failovers.</p>
            </div>
          </motion.div>

          <motion.div
            className="feature-card-rect"
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
          >
            <div className="icon-wrapper cyan">
              <Cpu size={22} />
            </div>
            <div className="card-rect-content">
              <h3>Strict Evidence Grounding</h3>
              <p>Extracts claim-level facts and cross-verifies confidence scores strictly against original source content.</p>
            </div>
          </motion.div>

          <motion.div
            className="feature-card-rect"
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
          >
            <div className="icon-wrapper blue">
              <FileText size={22} />
            </div>
            <div className="card-rect-content">
              <h3>Critic & Improver Loop</h3>
              <p>Self-evaluates report quality, detects weaknesses, and refines the draft before final delivery.</p>
            </div>
          </motion.div>
        </div>
      </section>
    </main>
  );
}

export default Home;