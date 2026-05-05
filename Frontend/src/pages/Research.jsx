import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, BrainCircuit, Activity } from "lucide-react";
import PipelineStep from "../components/PipelineStep";
import ReportPanel from "../components/ReportPanel";

const steps = [
  {
    title: "Smart Search",
    desc: "Searching trusted sources using Tavily.",
  },
  {
    title: "URL Ranking",
    desc: "Filtering and ranking sources by credibility.",
  },
  {
    title: "Web Scraping",
    desc: "Extracting clean content using BeautifulSoup.",
  },
  {
    title: "Reasoning Agent",
    desc: "Finding themes, patterns and contradictions.",
  },
  {
    title: "Evidence Extraction",
    desc: "Extracting facts, claims and statistics.",
  },
  {
    title: "Insight Generation",
    desc: "Generating deep analytical insights.",
  },
  {
    title: "Report Writer",
    desc: "Creating structured professional report.",
  },
  {
    title: "Critic + Improver",
    desc: "Reviewing and improving final output.",
  },
];

function Research() {
  const location = useLocation();
  const navigate = useNavigate();

  const topic = location.state?.topic || "Untitled Research";
  const [activeStep, setActiveStep] = useState(0);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    if (activeStep >= steps.length) {
      setCompleted(true);
      return;
    }

    const timer = setTimeout(() => {
      setActiveStep((prev) => prev + 1);
    }, 1200);

    return () => clearTimeout(timer);
  }, [activeStep]);

  return (
    <main className="research-page">
      <button className="back-btn" onClick={() => navigate("/")}>
        <ArrowLeft size={16} />
        Back
      </button>

      <section className="research-top">
        <motion.div
          className="research-badge"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Activity size={12} />
          Pipeline Running
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Researching: <span>{topic}</span>
        </motion.h1>

        <p>
          SynapseAI is processing your topic through an 8-stage autonomous research workflow.
        </p>
      </section>

      <section className="research-layout">
        <div className="pipeline-panel">
          <div className="panel-title">
            <BrainCircuit size={18} />
            Agent Workflow
          </div>

          <div className="pipeline-list">
            {steps.map((step, index) => (
              <PipelineStep
                key={step.title}
                step={step}
                index={index}
                activeStep={activeStep}
              />
            ))}
          </div>
        </div>

        <ReportPanel topic={topic} completed={completed} />
      </section>
    </main>
  );
}

export default Research;