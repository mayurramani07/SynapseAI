import { motion } from "framer-motion";
import { useState } from "react";
import workflow from "../assets/workflow.png";

export default function Engineering() {

  const [expanded, setExpanded] = useState(false);

  return (
    <main className="engineering-page">

      <div className="bg-glow purple"></div>
      <div className="bg-glow blue"></div>

      <section className="engineering-hero">
        <p className="engineering-subtext">
          ARCHITECTURE BEHIND THE MULTI-STAGE AI RESEARCH PIPELINE
        </p>

        <div className="engineering-tags">
          <span>Multi-Agent System</span>
          <span>Real-Time Web Search</span>
          <span>Iterative Reasoning</span>
          <span>Evidence-Based Reports</span>
        </div>

      </section>

      <motion.div
        className="workflow-container"
        initial={{ opacity: 0, y: 25 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >

        <button
          className="expand-btn"
          onClick={() => setExpanded(true)}
        >
          Expand
        </button>

        <img
          src={workflow}
          alt="workflow"
          className="workflow-image"
        />

      </motion.div>
      {
        expanded && (
          <div
            className="workflow-modal"
            onClick={() => setExpanded(false)}
          >
            <button
              className="close-btn"
              onClick={() => setExpanded(false)}
            >
              ✕
            </button>
            <img
              src={workflow}
              alt="expanded workflow"
              className="expanded-image"
            />
          </div>
        )
      }
    </main>
  );
}