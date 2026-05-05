import { motion } from "framer-motion";
import { CheckCircle2, Loader2, Circle } from "lucide-react";

function PipelineStep({ step, index, activeStep }) {
  const isDone = index < activeStep;
  const isActive = index === activeStep;

  return (
    <motion.div
      className={`pipeline-step ${isDone ? "done" : ""} ${isActive ? "active" : ""}`}
      initial={{ opacity: 0, x: -18 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.06 }}
    >
      <div className="pipeline-status">
        {isDone && <CheckCircle2 size={22} />}
        {isActive && <Loader2 size={22} className="spin" />}
        {!isDone && !isActive && <Circle size={22} />}
      </div>

      <div>
        <h4>{step.title}</h4>
        <p>{step.desc}</p>
      </div>
    </motion.div>
  );
}

export default PipelineStep;