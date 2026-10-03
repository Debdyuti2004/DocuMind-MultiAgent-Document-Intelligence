export async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail || body.message || message;
    } catch { /* response did not contain JSON */ }
    throw new Error(message);
  }
  return response.json();
}

export function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

export function notify(message, isError = false) {
  const node = document.createElement("div");
  node.className = `toast${isError ? " error" : ""}`;
  node.setAttribute("role", isError ? "alert" : "status");
  node.textContent = message;
  document.body.append(node);
  window.setTimeout(() => node.remove(), 4000);
}

export function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? escapeHtml(value) : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function displayName(document) {
  return document.title && document.title !== "(anonymous)" ? document.title : document.filename || "Untitled document";
}

const SESSION_KEY = "documind.session.v1";
const HISTORY_KEY = "documind.history.v1";
export const sessionId = localStorage.getItem(SESSION_KEY) || (() => {
  const id = globalThis.crypto?.randomUUID?.() || `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  localStorage.setItem(SESSION_KEY, id);
  return id;
})();

export function queryHistory() {
  try {
    const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(value) ? value : [];
  } catch { return []; }
}

export function saveQuery(entry) {
  const items = queryHistory();
  items.unshift(entry);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 100)));
  return items;
}

export function clearQueryHistory() {
  localStorage.removeItem(HISTORY_KEY);
}
