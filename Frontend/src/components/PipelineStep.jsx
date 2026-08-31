import { motion } from "framer-motion";
import { CheckCircle2, Loader2, Circle } from "lucide-react";

function PipelineStep({ step, index, activeStep, eventMessage }) {
  const isCompleted = index < activeStep;
  const isActive = index === activeStep;
  const isPending = index > activeStep;

  return (
    <motion.div
      className={`pipeline-step ${isCompleted ? "completed" : ""} ${isActive ? "active" : ""} ${isPending ? "pending" : ""}`}
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <div className="step-icon-col">
        {isCompleted && <CheckCircle2 className="status-icon success" size={20} />}
        {isActive && <Loader2 className="status-icon spinning" size={20} />}
        {isPending && <Circle className="status-icon pending" size={20} />}
        {index < 7 && <div className="step-connector"></div>}
      </div>

      <div className="step-content">
        <div className="step-header">
          <span className="step-title">{step.title}</span>
          <span className="step-badge">Stage {index + 1}</span>
        </div>

        <p className="step-desc">
          {isActive && eventMessage ? eventMessage : step.desc}
        </p>
      </div>
    </motion.div>
  );
}

export default PipelineStep;