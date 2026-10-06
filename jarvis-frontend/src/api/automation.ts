import { API_BASE_URL } from "./client";

export type ReminderItem = {
  id: string;
  title: string;
  scheduledTime: string;
  recurring?: string | null;
  completed: boolean;
  createdAt: string;
};

export async function fetchReminders(): Promise<ReminderItem[]> {
  const res = await fetch(`${API_BASE_URL}/automation/reminders`);
  if (!res.ok) throw new Error("Failed to fetch reminders");
  return res.json();
}

export async function createReminder(title: string, scheduledTime: string, recurring?: string): Promise<ReminderItem> {
  const res = await fetch(`${API_BASE_URL}/automation/reminders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, scheduledTime, recurring }),
  });
  if (!res.ok) throw new Error("Failed to create reminder");
  return res.json();
}

export async function toggleReminder(reminderId: string): Promise<ReminderItem> {
  const res = await fetch(`${API_BASE_URL}/automation/reminders/${reminderId}/toggle`, {
    method: "PATCH",
  });
  if (!res.ok) throw new Error("Failed to toggle reminder");
  return res.json();
}

export async function deleteReminder(reminderId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/automation/reminders/${reminderId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete reminder");
}
