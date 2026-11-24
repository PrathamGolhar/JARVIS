import { API_BASE_URL } from "./client";

export type SettingsStatus = {
  aiProvider: string;
  availableProviders: string[];
  activeModel: string;
  geminiConfigured: boolean;
  groqConfigured: boolean;
  openaiConfigured: boolean;
  anthropicConfigured: boolean;
  elevenlabsConfigured: boolean;
  permissionMode: string;
  wakeWordEnabled: boolean;
};

export type SettingsUpdate = {
  aiProvider?: string;
  geminiApiKey?: string;
  groqApiKey?: string;
  openaiApiKey?: string;
  anthropicApiKey?: string;
  elevenlabsApiKey?: string;
  permissionMode?: string;
  wakeWordEnabled?: boolean;
};

export async function fetchSettings(): Promise<SettingsStatus> {
  const res = await fetch(`${API_BASE_URL}/settings`);
  if (!res.ok) throw new Error("Failed to fetch settings");
  return res.json();
}

export async function updateSettings(req: SettingsUpdate): Promise<SettingsStatus> {
  const res = await fetch(`${API_BASE_URL}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error("Failed to update settings");
  return res.json();
}
