const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

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