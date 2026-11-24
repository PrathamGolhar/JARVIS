import { API_BASE_URL } from "./client";

export type ConversationMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

async function checkResponse(response: Response, action: string): Promise<void> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Failed to ${action}.`);
  }
}

export async function registerSession(sessionId: string): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId }),
  });
  if (response.status === 404) return false;
  await checkResponse(response, "register conversation");
  return true;
}

export async function fetchSessionHistory(sessionId: string): Promise<ConversationMessage[]> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}/history`);
  if (response.status === 404) return [];
  await checkResponse(response, "load conversation");
  return response.json();
}

export async function resetSessionHistory(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}/reset`, {
    method: "POST",
  });
  await checkResponse(response, "reset conversation");
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  await checkResponse(response, "delete conversation");
}
