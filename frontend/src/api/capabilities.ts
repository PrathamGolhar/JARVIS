import { API_BASE_URL } from "./client";

export type CapabilityCategory =
  | "voice"
  | "ai"
  | "web"
  | "math"
  | "system"
  | "files"
  | "desktop"
  | "tts"
  | "visualizer";

export type ApprovalStatus = "approved" | "requires_confirmation" | "denied" | "unknown";

export type CapabilityDto = {
  name: string;
  category: CapabilityCategory;
  description: string;
  requiresConfirmation: boolean;
  toolName?: string;
  status: ApprovalStatus;
};

export async function fetchCapabilities(): Promise<CapabilityDto[]> {
  const response = await fetch(`${API_BASE_URL}/capabilities`);
  if (!response.ok) {
    throw new Error("Could not retrieve capability allowlist.");
  }
  return response.json() as Promise<CapabilityDto[]>;
}

export async function checkCapability(capability: string): Promise<{
  capability: string;
  approved: boolean;
  status: ApprovalStatus;
  requiresConfirmation: boolean;
}> {
  const response = await fetch(`${API_BASE_URL}/capabilities/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ capability }),
  });
  if (!response.ok) {
    throw new Error(`Capability check failed for ${capability}`);
  }
  return response.json();
}
