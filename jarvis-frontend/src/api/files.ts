import { API_BASE_URL } from "./client";

export type FileUploadResult = {
  ok: boolean;
  filename: string;
  fileType: string;
  sizeBytes: number;
  extractedTextPreview: string;
  message: string;
};

export async function uploadDocument(file: File, sessionId?: string): Promise<FileUploadResult> {
  const formData = new FormData();
  formData.append("file", file);

  const url = new URL(`${API_BASE_URL}/files/upload`, window.location.origin);
  if (sessionId) {
    url.searchParams.append("session_id", sessionId);
  }

  const response = await fetch(url.toString(), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to upload and parse document.");
  }

  return response.json() as Promise<FileUploadResult>;
}
