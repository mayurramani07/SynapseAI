import { motion } from "framer-motion";
import { Search, Sparkles, ShieldCheck, FileText } from "lucide-react";

function Home() {
  return (
    <main className="home">
      <section className="hero">
        <motion.div
          className="badge"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Sparkles size={15} />
          Multi-Stage AI Research Agent
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          Research smarter with an
          <span> agentic intelligence pipeline.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          SynapseAI searches trusted sources, scrapes evidence, reasons over
          patterns, extracts insights, writes a report, critiques it, and improves
          the final answer.
        </motion.p>

        <motion.div
          className="search-box"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Search className="search-icon" size={22} />
          <input placeholder="Enter research topic..." />
          <button>Start Research</button>
        </motion.div>

        <div className="feature-grid">
          <div className="feature-card">
            <ShieldCheck />
            <h3>Credible Search</h3>
            <p>Ranks trusted domains like .gov, .edu, Reuters and World Bank.</p>
          </div>

          <div className="feature-card">
            <BrainIcon />
            <h3>Reasoning Layer</h3>
            <p>Finds themes, patterns, contradictions and missing data.</p>
          </div>

          <div className="feature-card">
            <FileText />
            <h3>Final Report</h3>
            <p>Generates a structured professional research report.</p>
          </div>
        </div>
      </section>
    </main>
  );
}

function BrainIcon() {
  return <Sparkles />;
}

export default Home;