import { useRef, useState } from "react";
import { uploadDocument } from "../api/files";

type FileUploadDrawerProps = {
  sessionId: string;
  onUploadSuccess: (filename: string, preview: string) => void;
  onError: (error: string) => void;
};

export function FileUploadDrawer({ sessionId, onUploadSuccess, onError }: FileUploadDrawerProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const result = await uploadDocument(file, sessionId);
      onUploadSuccess(result.filename, result.extractedTextPreview);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to upload document.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="file-upload-wrapper" style={{ display: "inline-flex", alignItems: "center" }}>
      <input
        ref={fileInputRef}
        type="file"
        id="jarvis-doc-upload"
        className="sr-only"
        accept=".pdf,.docx,.pptx,.xlsx,.csv,.json,.txt,.md,.py,.js,.ts,.html,.css,.cpp,.c,.java,.png,.jpg,.jpeg,.webp,.log"
        onChange={handleFileChange}
        disabled={isUploading}
      />
      <button
        type="button"
        className="file-attach-btn"
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
        title="Upload PDF, DOCX, PPTX, XLSX, Code or Image"
        aria-label="Upload File"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          padding: "8px 14px",
          background: "rgba(0, 217, 255, 0.15)",
          border: "1px solid rgba(0, 217, 255, 0.3)",
          borderRadius: "8px",
          color: "#00d9ff",
          fontSize: "12px",
          fontWeight: 700,
          cursor: isUploading ? "not-allowed" : "pointer",
          transition: "all 0.2s",
        }}
      >
        {isUploading ? (
          <span>ANALYZING FILE...</span>
        ) : (
          <>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
            <span>ATTACH FILE</span>
          </>
        )}
      </button>
    </div>
  );
}
