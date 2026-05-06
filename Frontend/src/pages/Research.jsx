import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, BrainCircuit, Activity, AlertCircle } from "lucide-react";
import PipelineStep from "../components/PipelineStep";
import ReportPanel from "../components/ReportPanel";
import { runResearch } from "../api/research";

const steps = [
  {
    title: "Smart Search",
    desc: "Searching trusted sources using Tavily.",
  },
  {
    title: "URL Ranking + Scraping",
    desc: "Ranking URLs and extracting clean content.",
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
    title: "Critic Agent",
    desc: "Reviewing report quality and weaknesses.",
  },
  {
    title: "Improver Agent",
    desc: "Improving final report using feedback.",
  },
];

function Research() {
  const location = useLocation();
  const navigate = useNavigate();

  const topic = location.state?.topic || "Untitled Research";

  const [activeStep, setActiveStep] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function startResearch() {
      try {
        setError("");
        setCompleted(false);
        setActiveStep(0);

        const animation = setInterval(() => {
          setActiveStep((prev) => {
            if (prev < steps.length - 1) {
              return prev + 1;
            }
            return prev;
          });
        }, 1800);

        const response = await runResearch(topic);

        clearInterval(animation);
        setActiveStep(steps.length);
        setResult(response.data);
        setCompleted(true);
      } catch (err) {
        setError(err.message);
      }
    }

    startResearch();
  }, [topic]);

  return (
    <main className="research-page">
      <button className="back-btn" onClick={() => navigate("/")}>
        <ArrowLeft size={18} />
        Back
      </button>

      <section className="research-top">
        <motion.div
          className={completed ? "research-badge completed" : "research-badge"}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Activity size={14} />
          {completed ? "Pipeline Completed" : "Pipeline Running"}
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

      {error && (
        <div className="error-box">
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      <section className="research-layout">
        <div className="pipeline-panel">
          <div className="panel-title">
            <BrainCircuit size={22} />
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

        <ReportPanel topic={topic} completed={completed} result={result} />
      </section>
    </main>
  );
}

export default Research;