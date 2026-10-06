import { useEffect, useState } from "react";
import { deleteGeneratedFile, fetchGeneratedFiles, GeneratedFileItem } from "../api/generation";

type GeneratedFilesDrawerProps = {
  onClose: () => void;
};

export function GeneratedFilesDrawer({ onClose }: GeneratedFilesDrawerProps) {
  const [files, setFiles] = useState<GeneratedFileItem[]>([]);
  const [loading, setLoading] = useState(true);

  const refreshFiles = async () => {
    setLoading(true);
    try {
      const data = await fetchGeneratedFiles();
      setFiles(data);
    } catch {
      // Offline / error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshFiles();
  }, []);

  const handleDelete = async (filename: string) => {
    if (!confirm(`Delete ${filename}?`)) return;
    try {
      await deleteGeneratedFile(filename);
      await refreshFiles();
    } catch (err) {
      alert(`Delete error: ${err}`);
    }
  };

  const getFileIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "pdf": return "📄";
      case "pptx": return "📊";
      case "docx": return "📝";
      case "xlsx":
      case "csv": return "📈";
      default: return "💾";
    }
  };

  return (
    <div style={{
      position: "fixed",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      width: "min(760px, 92vw)",
      maxHeight: "80vh",
      background: "rgba(10, 22, 38, 0.95)",
      backdropFilter: "blur(20px)",
      border: "1px solid rgba(0, 217, 255, 0.4)",
      borderRadius: "16px",
      boxShadow: "0 0 40px rgba(0, 217, 255, 0.25), 0 20px 50px rgba(0, 0, 0, 0.8)",
      display: "flex",
      flexDirection: "column",
      zIndex: 1000,
      color: "#e2e8f0",
      fontFamily: "Segoe UI, sans-serif",
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        padding: "16px 24px",
        background: "rgba(5, 12, 24, 0.8)",
        borderBottom: "1px solid rgba(0, 217, 255, 0.2)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "20px" }}>📂</span>
          <div>
            <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#64ffda", letterSpacing: "1px" }}>
              GENERATED FILES & ARTIFACTS CENTER
            </h2>
            <p style={{ margin: 0, fontSize: "11px", color: "#94a3b8" }}>
              {files.length} publication documents, presentations, and spreadsheets available
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{ background: "transparent", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer" }}
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {loading && (
          <p style={{ textAlign: "center", color: "#64ffda", padding: "40px" }}>Loading generated files catalog...</p>
        )}

        {!loading && files.length === 0 && (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "#64748b" }}>
            <span style={{ fontSize: "40px", display: "block", marginBottom: "12px" }}>📭</span>
            <p style={{ margin: 0, fontSize: "14px", color: "#94a3b8" }}>No documents generated yet.</p>
            <p style={{ margin: "4px 0 0 0", fontSize: "12px" }}>Ask JARVIS to create a PDF report, PowerPoint, Word doc, or study notes.</p>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {files.map((f) => (
            <div
              key={f.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "14px 18px",
                background: "rgba(15, 30, 50, 0.6)",
                border: "1px solid rgba(0, 217, 255, 0.15)",
                borderRadius: "10px",
                transition: "all 0.2s ease",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                <span style={{ fontSize: "24px" }}>{getFileIcon(f.fileType)}</span>
                <div>
                  <h4 style={{ margin: 0, fontSize: "13.5px", color: "#ffffff", fontWeight: 600 }}>{f.filename}</h4>
                  <p style={{ margin: "2px 0 0 0", fontSize: "11px", color: "#94a3b8" }}>
                    {f.fileType.toUpperCase()} • {(f.sizeBytes / 1024).toFixed(1)} KB • Created {f.createdAt}
                  </p>
                </div>
              </div>

              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <a
                  href={f.downloadUrl}
                  download={f.filename}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    padding: "6px 14px",
                    background: "rgba(0, 217, 255, 0.15)",
                    border: "1px solid #00d9ff",
                    borderRadius: "6px",
                    color: "#00d9ff",
                    fontSize: "11px",
                    fontWeight: 700,
                    textDecoration: "none",
                    cursor: "pointer",
                  }}
                >
                  ⬇ DOWNLOAD
                </a>
                <button
                  onClick={() => handleDelete(f.filename)}
                  style={{
                    padding: "6px 10px",
                    background: "transparent",
                    border: "1px solid rgba(239, 68, 68, 0.4)",
                    borderRadius: "6px",
                    color: "#ef4444",
                    fontSize: "11px",
                    cursor: "pointer",
                  }}
                >
                  🗑
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
