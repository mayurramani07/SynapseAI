const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://synapseai-83c9.onrender.com";

export async function verifyAdminPasscode(passcode) {
  const response = await fetch(`${API_BASE_URL}/api/admin/verify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ passcode }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Authentication failed");
  }
  return data;
}

export async function fetchAdminMetrics(passcode) {
  const response = await fetch(`${API_BASE_URL}/api/admin/metrics`, {
    method: "GET",
    headers: {
      "X-Admin-Passcode": passcode,
    },
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Failed to fetch metrics");
  }
  return data.data;
}

export async function clearAdminLogs(passcode) {
  const response = await fetch(`${API_BASE_URL}/api/admin/logs`, {
    method: "DELETE",
    headers: {
      "X-Admin-Passcode": passcode,
    },
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Failed to clear logs");
  }
  return data;
}
