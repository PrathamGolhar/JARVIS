import { API_BASE_URL } from "./client";

export type AssistantMode =
  | "general"
  | "study"
  | "research"
  | "coding"
  | "project"
  | "document"
  | "presentation"
  | "automation"
  | "voice";

export type ResponseStyle = "concise" | "balanced" | "detailed";

export type Citation = {
  title: string;
  url: string;
  domain?: string;
  snippet?: string;
};

export type ToolEvent = {
  toolName: string;
  arguments?: Record<string, unknown>;
  result?: Record<string, unknown>;
  requiresConfirmation?: boolean;
  status?: "pending" | "completed" | "failed";
  fileVerification?: Record<string, unknown>;
};

export type PlanStep = {
  stepNumber: number;
  title: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  detail?: string;
};

export type PendingAction = {
  actionId: string;
  toolName: string;
  arguments?: Record<string, unknown>;
  label: string;
  description: string;
  requiresConfirmation: boolean;
};

export type GeneratedFile = {
  id: string;
  filename: string;
  fileType: string;
  sizeBytes: number;
  downloadUrl: string;
  description?: string;
};

export type ChatPayload = {
  sessionId: string;
  text: string;
  mode?: AssistantMode;
  projectId?: string;
  responseStyle?: ResponseStyle;
  confirmedActionId?: string;
  imageIds?: string[];
  providerOverride?: "auto" | "gemini" | "groq" | "openai" | "anthropic" | "local";
  idempotencyKey?: string;
};

export type ChatResponse = {
  sessionId: string;
  reply: string;
  mode?: AssistantMode;
  executionStatus?: "success" | "partial_success" | "failure" | "unverified";
  verification?: Record<string, unknown>;
  turnsRetained?: number;
  citations?: Citation[];
  toolEvents?: ToolEvent[];
  planSteps?: PlanStep[];
  pendingAction?: PendingAction | null;
  generatedFiles?: GeneratedFile[];
};

import { parseApiError } from "./errors";

export async function sendChatMessage(payload: ChatPayload): Promise<ChatResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sessionId: payload.sessionId,
        text: payload.text,
        mode: payload.mode || "general",
        responseStyle: payload.responseStyle || "balanced",
        projectId: payload.projectId,
        confirmedActionId: payload.confirmedActionId,
        imageIds: payload.imageIds,
        providerOverride: payload.providerOverride,
        idempotencyKey: payload.idempotencyKey || crypto.randomUUID(),
      }),
    });
  } catch (err) {
    throw await parseApiError(err, "/api/chat");
  }

  if (!res.ok) {
    throw await parseApiError(res, "/api/chat");
  }

  try {
    return await res.json();
  } catch (err) {
    throw await parseApiError(err, "/api/chat");
  }
}
