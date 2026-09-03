const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://synapseai-83c9.onrender.com";

export async function runResearch(topic, nocache = false) {
  const response = await fetch(`${API_BASE_URL}/api/research`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ topic, nocache }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Research failed");
  }

  return data;
}

export function runResearchStream(topic, onEvent, onError, nocache = false) {
  const url = `${API_BASE_URL}/api/research/stream?topic=${encodeURIComponent(topic)}&nocache=${nocache}`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const parsedData = JSON.parse(event.data);
      onEvent(parsedData);

      if (parsedData.event === "pipeline_complete" || parsedData.event === "error") {
        eventSource.close();
      }
    } catch (err) {
      if (onError) onError(err);
    }
  };

  eventSource.onerror = (err) => {
    eventSource.close();
    if (onError) onError(err);
  };

  return () => {
    eventSource.close();
  };
}

export async function sendFollowUpQuestion({ topic, report, evidence, question, history }) {
  const response = await fetch(`${API_BASE_URL}/api/research/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      topic,
      report,
      evidence,
      question,
      history,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to get chat response");
  }

  return data;
}