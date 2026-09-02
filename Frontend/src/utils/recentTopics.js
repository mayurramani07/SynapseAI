/**
 * recentTopics.js
 * Browser localStorage utility for tracking recent research topics.
 */

const STORAGE_KEY = "synapse_recent_topics";
const MAX_TOPICS = 8;

/**
 * Get all recent topics from localStorage.
 * @returns {Array<{ topic: string, timestamp: number }>}
 */
export function getRecentTopics() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/**
 * Save a topic to localStorage. Deduplicates (moves to top if already exists).
 * @param {string} topic
 */
export function saveRecentTopic(topic) {
  if (!topic || !topic.trim()) return;
  try {
    const trimmed = topic.trim();
    const existing = getRecentTopics().filter(
      (t) => t.topic.toLowerCase() !== trimmed.toLowerCase()
    );
    const updated = [{ topic: trimmed, timestamp: Date.now() }, ...existing].slice(0, MAX_TOPICS);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // Silent fail — localStorage may be unavailable
  }
}

/**
 * Remove a specific topic by its exact string.
 * @param {string} topic
 */
export function removeRecentTopic(topic) {
  try {
    const updated = getRecentTopics().filter(
      (t) => t.topic.toLowerCase() !== topic.toLowerCase()
    );
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {}
}

/**
 * Clear all recent topics.
 */
export function clearRecentTopics() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {}
}

/**
 * Format a Unix timestamp as a relative human-readable string.
 * @param {number} timestamp
 * @returns {string}
 */
export function formatRelativeTime(timestamp) {
  const diffMs = Date.now() - timestamp;
  const diffMins = Math.floor(diffMs / 60_000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  if (diffDays === 1) return "Yesterday";
  return `${diffDays}d ago`;
}
