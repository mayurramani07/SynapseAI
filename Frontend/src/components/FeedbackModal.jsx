import { useState } from "react";
import { X, Star, CheckCircle2 } from "lucide-react";

function FeedbackModal({ isOpen, onClose }) {
  const [rating, setRating] = useState(5);
  const [feedbackText, setFeedbackText] = useState("");
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!feedbackText.trim()) return;

    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setFeedbackText("");
      onClose();
    }, 2000);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="feedback-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-btn" onClick={onClose}>
          <X size={16} />
        </button>

        {submitted ? (
          <div className="feedback-success">
            <CheckCircle2 size={36} className="success-icon" />
            <h3>Feedback Received!</h3>
            <p>Thank you for helping us improve SynapseAI.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="feedback-form">
            <div className="modal-header">
              <h3>Share Your Feedback</h3>
              <p>How was your research experience with SynapseAI?</p>
            </div>

            <div className="star-rating">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  type="button"
                  key={star}
                  className={`star-btn ${star <= rating ? "filled" : ""}`}
                  onClick={() => setRating(star)}
                >
                  <Star size={20} fill={star <= rating ? "#000000" : "none"} />
                </button>
              ))}
            </div>

            <textarea
              placeholder="Tell us what you liked or how we can improve..."
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              rows={4}
              required
            />

            <button type="submit" className="submit-btn">
              Submit Feedback
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default FeedbackModal;
