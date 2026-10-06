import { API_BASE_URL } from "./client";

export type DiagnosticItem = {
  id: string;
  label: string;
  status: "ready" | "active" | "warning" | "error" | "unconfigured";
  latencyMs?: number;
  details: string;
};

export type SystemMetrics = {
  cpu_usage_percent?: number;
  cpu_cores?: number;
  ram_total_gb?: number;
  ram_used_gb?: number;
  ram_usage_percent?: number;
  disk_total_gb?: number;
  disk_free_gb?: number;
  disk_usage_percent?: number;
  system_uptime?: string;
  battery?: {
    percent: number;
    power_plugged: boolean;
    seconds_left: number | string;
  } | null;
  os?: string;
  processor?: string;
};

export type DiagnosticsResponse = {
  ok: boolean;
  timestamp: string;
  items: DiagnosticItem[];
  systemMetrics: SystemMetrics;
};

export async function fetchDiagnostics(): Promise<DiagnosticsResponse> {
  const res = await fetch(`${API_BASE_URL}/diagnostics`);
  if (!res.ok) {
    throw new Error("Diagnostics endpoint unavailable.");
  }
  return res.json() as Promise<DiagnosticsResponse>;
}
