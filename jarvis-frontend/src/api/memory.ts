import { API_BASE_URL } from "./client";

export type MemoryItem = {
  key: string;
  value: string;
  category: string;
  updatedAt: string;
};

export async function fetchMemories(): Promise<MemoryItem[]> {
  const res = await fetch(`${API_BASE_URL}/memory`);
  if (!res.ok) throw new Error("Failed to fetch memories");
  return res.json();
}

export async function setMemory(key: string, value: string, category: string = "general"): Promise<MemoryItem> {
  const res = await fetch(`${API_BASE_URL}/memory`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, value, category }),
  });
  if (!res.ok) throw new Error("Failed to set memory");
  return res.json();
}

export async function deleteMemory(key: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/memory/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete memory");
}
