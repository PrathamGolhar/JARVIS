import { API_BASE_URL } from "./client";

export type ProjectTask = {
  id: string;
  title: string;
  completed: boolean;
  dueDate?: string | null;
};

export type ProjectItem = {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  tasks: ProjectTask[];
  linkedFiles: string[];
  notes: string;
};

export async function fetchProjects(): Promise<ProjectItem[]> {
  const res = await fetch(`${API_BASE_URL}/projects`);
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json();
}

export async function createProject(name: string, description: string = ""): Promise<ProjectItem> {
  const res = await fetch(`${API_BASE_URL}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) throw new Error("Failed to create project");
  return res.json();
}

export async function addProjectTask(projectId: string, title: string, dueDate?: string): Promise<ProjectItem> {
  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/tasks?title=${encodeURIComponent(title)}${dueDate ? `&due_date=${encodeURIComponent(dueDate)}` : ""}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to add task");
  return res.json();
}

export async function toggleProjectTask(projectId: string, taskId: string): Promise<ProjectItem> {
  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/tasks/${taskId}/toggle`, {
    method: "PATCH",
  });
  if (!res.ok) throw new Error("Failed to toggle task");
  return res.json();
}

export async function updateProjectNotes(projectId: string, notes: string): Promise<ProjectItem> {
  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/notes?notes=${encodeURIComponent(notes)}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to update notes");
  return res.json();
}
