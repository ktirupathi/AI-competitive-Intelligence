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

// ---------------------------------------------------------------------------
// Workspace APIs
// ---------------------------------------------------------------------------

export async function getWorkspaces() {
  const { data } = await api.get("/workspaces");
  return data;
}

export async function createWorkspace(payload: {
  name: string;
  plan?: string;
}) {
  const { data } = await api.post("/workspaces", payload);
  return data;
}

export async function getWorkspace(id: string) {
  const { data } = await api.get(`/workspaces/${id}`);
  return data;
}

export async function getWorkspaceMembers(workspaceId: string) {
  const { data } = await api.get(`/workspaces/${workspaceId}/members`);
  return data;
}

export async function inviteWorkspaceMember(
  workspaceId: string,
  payload: { email: string; role?: string }
) {
  const { data } = await api.post(
    `/workspaces/${workspaceId}/members`,
    payload
  );
  return data;
}

export async function removeWorkspaceMember(
  workspaceId: string,
  userId: string
) {
  await api.delete(`/workspaces/${workspaceId}/members/${userId}`);
}

export async function getWorkspaceUsage(workspaceId: string) {
  const { data } = await api.get(`/workspaces/${workspaceId}/usage`);
  return data;
}

// ---------------------------------------------------------------------------
// Timeline & History APIs
// ---------------------------------------------------------------------------

export async function getCompetitorTimeline(
  competitorId: string,
  params?: { since?: string; limit?: number }
) {
  const { data } = await api.get(`/competitors/${competitorId}/timeline`, {
    params,
  });
  return data;
}

export async function getBriefingHistory(params?: {
  competitor_id?: string;
  date_from?: string;
  date_to?: string;
  frequency?: string;
  offset?: number;
  limit?: number;
}) {
  const { data } = await api.get("/briefings/history", { params });
  return data;
}

// ---------------------------------------------------------------------------
// Search API
// ---------------------------------------------------------------------------

export async function semanticSearch(payload: {
  query: string;
  source_type?: string;
  limit?: number;
}) {
  const { data } = await api.post("/search", payload);
  return data;
}

// ---------------------------------------------------------------------------
// Alert APIs
// ---------------------------------------------------------------------------

export async function getAlerts(
  workspaceId: string,
  params?: {
    severity?: string;
    alert_type?: string;
    is_read?: boolean;
    offset?: number;
    limit?: number;
  }
) {
  const { data } = await api.get("/alerts", {
    params: { workspace_id: workspaceId, ...params },
  });
  return data;
}

export async function markAlertsRead(
  workspaceId: string,
  alertIds: string[]
) {
  const { data } = await api.post("/alerts/mark-read", {
    alert_ids: alertIds,
  }, { params: { workspace_id: workspaceId } });
  return data;
}

// ---------------------------------------------------------------------------
// Public & Export APIs
// ---------------------------------------------------------------------------

export async function shareInsight(insightId: string) {
  const { data } = await api.post(`/public/insights/${insightId}/share`);
  return data;
}

export async function unshareInsight(insightId: string) {
  const { data } = await api.post(`/public/insights/${insightId}/unshare`);
  return data;
}

export async function exportReport(payload: {
  format: "pdf" | "markdown" | "notion";
  briefing_id?: string;
  competitor_id?: string;
}) {
  const { data } = await api.post("/public/export", payload);
  return data;
}

// ---------------------------------------------------------------------------
// Admin APIs
// ---------------------------------------------------------------------------

export async function getAgentHealth() {
  const { data } = await api.get("/admin/agents");
  return data;
}

export async function getAuditLogs(
  workspaceId: string,
  params?: {
    action?: string;
    resource?: string;
    offset?: number;
    limit?: number;
  }
) {
  const { data } = await api.get("/admin/audit-logs", {
    params: { workspace_id: workspaceId, ...params },
  });
  return data;
}
