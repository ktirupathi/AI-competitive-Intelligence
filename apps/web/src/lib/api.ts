import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(async (config) => {
  if (typeof window !== "undefined") {
    const token = await window.Clerk?.session?.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        window.location.href = "/sign-in";
      }
    }
    return Promise.reject(error);
  }
);

declare global {
  interface Window {
    Clerk?: {
      session?: {
        getToken: () => Promise<string | null>;
      };
    };
  }
}

export default api;

export async function getCompetitors() {
  const { data } = await api.get("/competitors");
  return data;
}

export async function getCompetitor(id: string) {
  const { data } = await api.get(`/competitors/${id}`);
  return data;
}

export async function addCompetitor(payload: {
  name: string;
  domain: string;
  description?: string;
}) {
  const { data } = await api.post("/competitors", payload);
  return data;
}

export async function deleteCompetitor(id: string) {
  const { data } = await api.delete(`/competitors/${id}`);
  return data;
}

export async function getBriefings() {
  const { data } = await api.get("/briefings");
  return data;
}

export async function getBriefing(id: string) {
  const { data } = await api.get(`/briefings/${id}`);
  return data;
}

export async function getIntegrations() {
  const { data } = await api.get("/integrations");
  return data;
}

export async function connectIntegration(
  type: string,
  config: Record<string, string>
) {
  const { data } = await api.post("/integrations", { type, config });
  return data;
}

export async function disconnectIntegration(id: string) {
  const { data } = await api.delete(`/integrations/${id}`);
  return data;
}

export async function getSettings() {
  const { data } = await api.get("/settings");
  return data;
}

export async function updateSettings(payload: Record<string, unknown>) {
  const { data } = await api.put("/settings", payload);
  return data;
}

export async function createBillingPortalSession() {
  const { data } = await api.post("/billing/portal");
  return data;
}

export async function createCheckoutSession(priceId: string) {
  const { data } = await api.post("/billing/checkout", { priceId });
  return data;
}
