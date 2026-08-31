const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function runResearch(topic) {
  const response = await fetch(`${API_BASE_URL}/api/research`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ topic }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Research failed");
  }

  return data;
}

export function runResearchStream(topic, onEvent, onError) {
  const url = `${API_BASE_URL}/api/research/stream?topic=${encodeURIComponent(topic)}`;
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