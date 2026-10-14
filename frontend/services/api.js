// All communication with the FastAPI backend goes through this file.
// The browser never talks to the database or to the AI provider directly.

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "finsight_token";
const USER_KEY = "finsight_user";

const hasWindow = () => typeof window !== "undefined";

export const getToken = () => (hasWindow() ? localStorage.getItem(TOKEN_KEY) : null);

export function getUser() {
  if (!hasWindow()) return null;
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

export function saveSession({ access_token, user }) {
  localStorage.setItem(TOKEN_KEY, access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  if (!hasWindow()) return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function errorMessage(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // FastAPI validation errors: [{loc: [...], msg: "..."}]
    return detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return `Request failed (${status})`;
}

async function request(path, { method = "GET", body, params, auth = true } = {}) {
  const url = new URL(API_URL + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch {
    throw new Error(`Can't reach the FinSight server at ${API_URL}. Is the backend running?`);
  }

  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON response */
  }

  if (res.status === 401 && auth) {
    clearSession();
    if (hasWindow() && !window.location.pathname.startsWith("/login")) window.location.href = "/login";
  }
  if (!res.ok) throw new Error(errorMessage(data, res.status));
  return data;
}

export const api = {
  // auth
  register: (payload) => request("/api/auth/register", { method: "POST", body: payload, auth: false }),
  login: (payload) => request("/api/auth/login", { method: "POST", body: payload, auth: false }),
  me: () => request("/api/auth/me"),

  // dashboard + analytics
  dashboard: () => request("/api/dashboard"),
  monthly: (months = 6) => request("/api/analytics/monthly", { params: { months } }),
  expenseAnalytics: (month) => request("/api/analytics/expenses", { params: { month } }),
  insights: (month) => request("/api/analytics/insights", { params: { month } }),
  forecast: (monthsAhead = 1) => request("/api/analytics/forecast", { params: { months_ahead: monthsAhead } }),
  scenario: (payload) => request("/api/analytics/scenario", { method: "POST", body: payload }),

  // transactions
  listTransactions: (params) => request("/api/transactions", { params }),
  categories: (type) => request("/api/transactions/categories", { params: { type } }),
  createTransaction: (payload) => request("/api/transactions", { method: "POST", body: payload }),
  updateTransaction: (id, payload) => request(`/api/transactions/${id}`, { method: "PUT", body: payload }),
  deleteTransaction: (id) => request(`/api/transactions/${id}`, { method: "DELETE" }),

  // assistant
  chat: (message, history = []) => request("/api/assistant/chat", { method: "POST", body: { message, history } }),
};
