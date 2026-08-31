import { useEffect, useState, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, BrainCircuit, Activity, AlertCircle, Clock, ShieldCheck, Layers } from "lucide-react";
import PipelineStep from "../components/PipelineStep";
import ReportPanel from "../components/ReportPanel";
import { runResearch, runResearchStream } from "../api/research";

const steps = [
  { title: "Smart Search", desc: "Searching trusted sources using Tavily." },
  { title: "URL Ranking + Scraping", desc: "Ranking URLs and extracting clean content." },
  { title: "Reasoning Agent", desc: "Finding themes, patterns and contradictions." },
  { title: "Evidence Extraction", desc: "Extracting facts, claims and statistics." },
  { title: "Evidence Grounding", desc: "Verifying claims against original text." },
  { title: "Insight Generation", desc: "Generating deep analytical insights." },
  { title: "Report Writer", desc: "Creating structured professional report." },
  { title: "Critic & Improver", desc: "Reviewing quality and improving final report." },
];

function Research() {
  const location = useLocation();
  const navigate = useNavigate();

  const topic = location.state?.topic || "Impact of Generative AI on Software Engineering Productivity";

  const [activeStep, setActiveStep] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [liveLog, setLiveLog] = useState("Initializing research workflow...");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const timerRef = useRef(null);

  useEffect(() => {
    let cleanupStream = null;

    setElapsedSeconds(0);
    timerRef.current = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    async function executeWorkflow() {
      setError("");
      setCompleted(false);
      setActiveStep(0);

      // Attempt SSE live stream
      try {
        cleanupStream = runResearchStream(
          topic,
          (event) => {
            if (event.message) {
              setLiveLog(event.message);
            }

            if (event.stage) {
              const stageName = event.stage.toLowerCase();
              if (stageName.includes("search")) setActiveStep(0);
              else if (stageName.includes("scrap")) setActiveStep(1);
              else if (stageName.includes("reason")) setActiveStep(2);
              else if (stageName.includes("extraction")) setActiveStep(3);
              else if (stageName.includes("grounding")) setActiveStep(4);
              else if (stageName.includes("insight")) setActiveStep(5);
              else if (stageName.includes("writer")) setActiveStep(6);
              else if (stageName.includes("critic") || stageName.includes("improver")) setActiveStep(7);
            }

            if (event.event === "pipeline_complete" || event.final_report) {
              clearInterval(timerRef.current);
              setActiveStep(steps.length);
              setCompleted(true);
              setResult(event);
            }
          },
          async (streamErr) => {
            // Fallback to standard POST endpoint if SSE fails or isn't proxied
            try {
              const response = await runResearch(topic);
              clearInterval(timerRef.current);
              setActiveStep(steps.length);
              setResult(response.data);
              setCompleted(true);
            } catch (fallbackErr) {
              clearInterval(timerRef.current);
              setError(fallbackErr.message || "Research failed.");
            }
          }
        );
      } catch (err) {
        // Direct POST fallback
        try {
          const response = await runResearch(topic);
          clearInterval(timerRef.current);
          setActiveStep(steps.length);
          setResult(response.data);
          setCompleted(true);
        } catch (fallbackErr) {
          clearInterval(timerRef.current);
          setError(fallbackErr.message || "Research failed.");
        }
      }
    }

    executeWorkflow();

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (cleanupStream) cleanupStream();
    };
  }, [topic]);

  return (
    <main className="research-page">
      <div className="bg-glow purple"></div>
      <div className="bg-glow cyan"></div>

      <button className="back-btn" onClick={() => navigate("/")}>
        <ArrowLeft size={18} />
        <span>Back to Search</span>
      </button>

      <section className="research-top">
        <div className="top-row">
          <motion.div
            className={completed ? "research-badge completed" : "research-badge active"}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Activity size={14} className={completed ? "" : "pulse-icon"} />
            <span>{completed ? "Pipeline Completed" : "Pipeline Running"}</span>
          </motion.div>

          <div className="metrics-summary-bar">
            <div className="metric-item">
              <Clock size={14} />
              <span>{elapsedSeconds}s elapsed</span>
            </div>
            <div className="metric-item">
              <Layers size={14} />
              <span>8 Autonomous Agents</span>
            </div>
            <div className="metric-item">
              <ShieldCheck size={14} />
              <span>Zero Hallucinations</span>
            </div>
          </div>
        </div>

        <motion.h1
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          Research Topic: <span className="research-topic-text">{topic}</span>
        </motion.h1>

        <p className="research-subtext">
          SynapseAI is analyzing your topic through an 8-stage agentic workflow with real-time evidence verification.
        </p>
      </section>

      {error && (
        <div className="error-box">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      <section className="research-layout">
        <div className="pipeline-panel">
          <div className="panel-title">
            <BrainCircuit size={22} className="title-icon" />
            <span>Agent Workflow</span>
          </div>

          <div className="pipeline-list">
            {steps.map((step, index) => (
              <PipelineStep
                key={step.title}
                step={step}
                index={index}
                activeStep={activeStep}
                eventMessage={index === activeStep ? liveLog : null}
              />
            ))}
          </div>
        </div>

        <ReportPanel
          topic={topic}
          completed={completed}
          result={result}
          duration={elapsedSeconds}
          liveLog={liveLog}
        />
      </section>
    </main>
  );
}

export default Research;