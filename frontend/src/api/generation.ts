import { API_BASE_URL } from "./client";

export type GeneratedFileItem = {
  id: string;
  filename: string;
  fileType: string;
  sizeBytes: number;
  createdAt: string;
  downloadUrl: string;
  description?: string;
};

export async function fetchGeneratedFiles(): Promise<GeneratedFileItem[]> {
  const res = await fetch(`${API_BASE_URL}/files/generated`);
  if (!res.ok) throw new Error("Failed to list generated files");
  return res.json();
}

export async function deleteGeneratedFile(filename: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/files/${encodeURIComponent(filename)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete file");
}

export async function generatePdf(title: string, contentMarkdown: string, subtitle?: string): Promise<{ filename: string; downloadUrl: string }> {
  const res = await fetch(`${API_BASE_URL}/generate/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, contentMarkdown, subtitle }),
  });
  if (!res.ok) throw new Error("Failed to generate PDF");
  return res.json();
}

export async function generatePptx(topic: string, numSlides: number = 6, themeColor: string = "cyan"): Promise<{ filename: string; downloadUrl: string }> {
  const res = await fetch(`${API_BASE_URL}/generate/pptx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, numSlides, themeColor }),
  });
  if (!res.ok) throw new Error("Failed to generate PowerPoint");
  return res.json();
}

export async function generateDocx(title: string, contentMarkdown: string, subtitle?: string): Promise<{ filename: string; downloadUrl: string }> {
  const res = await fetch(`${API_BASE_URL}/generate/docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, contentMarkdown, subtitle }),
  });
  if (!res.ok) throw new Error("Failed to generate Word document");
  return res.json();
}
