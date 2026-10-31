const API_BASE = `${window.location.origin.includes("5500") ? "http://localhost:8000" : window.location.origin}/api/v1`;

function authHeaders() {
  const token = localStorage.getItem("estateai_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = data?.error?.message || res.statusText;
    throw new Error(err);
  }
  return data;
}

window.EstateAPI = {
  searchProperties: (params) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") q.set(k, v);
    });
    return api(`/properties?${q}`);
  },
  getProperty: (id) => api(`/properties/${id}`),
  getNeighbourhood: (id, categories = "school,hospital,metro,grocery,park,shopping,office,bank") =>
    api(`/properties/${id}/neighbourhood?radius_m=3000&categories=${encodeURIComponent(categories)}`),
  getPriceAnalysis: (id) => api(`/properties/${id}/price-analysis`),
  calculateInvestment: (body) =>
    api("/investment/calculate", { method: "POST", body: JSON.stringify(body) }),
  aiSearch: (query) => api("/ai/search", { method: "POST", body: JSON.stringify({ query }) }),
  aiChat: (body) => api("/ai/chat", { method: "POST", body: JSON.stringify(body) }),
  createLead: (body) =>
    api("/leads", {
      method: "POST",
      headers: { "X-Idempotency-Key": body.idempotency_key || crypto.randomUUID() },
      body: JSON.stringify(body),
    }),
  login: (email, password) =>
    api("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (payload) =>
    api("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  me: () => api("/accounts/me"),
  localities: (city) => api(`/localities${city ? `?city=${encodeURIComponent(city)}` : ""}`),
};
