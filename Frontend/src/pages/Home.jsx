import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Sparkles, ShieldCheck, FileText, Cpu,
  ArrowRight, Zap, Clock, X, Trash2, History
} from "lucide-react";
import {
  getRecentTopics,
  saveRecentTopic,
  removeRecentTopic,
  clearRecentTopics,
  formatRelativeTime,
} from "../utils/recentTopics";

const SUGGESTED_TOPICS = [
  "Impact of Generative AI on Software Engineering Productivity",
  "Quantum Computing Applications in Financial Risk Modeling",
  "CRISPR Gene Editing Breakthroughs in Oncology Therapeutics",
  "Autonomous Agent Orchestration in Multi-Cloud Architectures",
];

function Home() {
  const [topic, setTopic] = useState("");
  const [recentTopics, setRecentTopics] = useState([]);
  const navigate = useNavigate();

  // Load recent topics on mount
  useEffect(() => {
    setRecentTopics(getRecentTopics());
  }, []);

  const handleStart = useCallback(
    (selectedTopic) => {
      const targetTopic = selectedTopic || topic;
      if (!targetTopic.trim()) return;
      const trimmed = targetTopic.trim();
      saveRecentTopic(trimmed);
      setRecentTopics(getRecentTopics());
      navigate("/research", { state: { topic: trimmed } });
    },
    [topic, navigate]
  );

  const handleRemove = (e, topicStr) => {
    e.stopPropagation();
    removeRecentTopic(topicStr);
    setRecentTopics(getRecentTopics());
  };

  const handleClearAll = () => {
    clearRecentTopics();
    setRecentTopics([]);
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
            <div className="search-input-wrapper">
              <Search className="search-icon" size={18} />
              <input
                placeholder="Enter any complex research topic..."
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleStart()}
              />
            </div>
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

          {/* RECENT TOPICS */}
          <AnimatePresence>
            {recentTopics.length > 0 && (
              <motion.div
                className="recent-topics-section"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.35 }}
              >
                <div className="recent-header">
                  <span className="recent-label">
                    <History size={13} />
                    Recent Searches
                    <span className="recent-count">{recentTopics.length}</span>
                  </span>
                  <button className="recent-clear-btn" onClick={handleClearAll} title="Clear all history">
                    <Trash2 size={12} />
                    <span>Clear all</span>
                  </button>
                </div>

                <div className="recent-list">
                  <AnimatePresence initial={false}>
                    {recentTopics.map((item, idx) => (
                      <motion.div
                        key={item.topic}
                        className="recent-item"
                        initial={{ opacity: 0, x: -12 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 16, height: 0, marginBottom: 0, padding: 0 }}
                        transition={{ duration: 0.22, delay: idx * 0.04 }}
                        onClick={() => handleStart(item.topic)}
                      >
                        <div className="recent-item-left">
                          <Clock size={13} className="recent-clock-icon" />
                          <span className="recent-topic-text">{item.topic}</span>
                        </div>
                        <div className="recent-item-right">
                          <span className="recent-time">{formatRelativeTime(item.timestamp)}</span>
                          <button
                            className="recent-remove-btn"
                            onClick={(e) => handleRemove(e, item.topic)}
                            title="Remove from history"
                          >
                            <X size={12} />
                          </button>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
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