import { useEffect, useState } from "react";
import { deleteMemory, fetchMemories, MemoryItem, setMemory } from "../api/memory";

type MemoryInspectorModalProps = {
  onClose: () => void;
};

export function MemoryInspectorModal({ onClose }: MemoryInspectorModalProps) {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [newKey, setNewKey] = useState("");
  const [newVal, setNewVal] = useState("");
  const [newCat, setNewCat] = useState("general");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const refreshMemories = async () => {
    setLoading(true);
    try {
      const data = await fetchMemories();
      setMemories(data);
    } catch {
      // Error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshMemories();
  }, []);

  const handleAdd = async () => {
    if (!newKey.trim() || !newVal.trim()) return;
    try {
      await setMemory(newKey, newVal, newCat);
      setNewKey("");
      setNewVal("");
      await refreshMemories();
    } catch (err) {
      alert(`Memory error: ${err}`);
    }
  };

  const handleDelete = async (key: string) => {
    if (!confirm(`Delete memory for '${key}'?`)) return;
    try {
      await deleteMemory(key);
      await refreshMemories();
    } catch (err) {
      alert(`Delete error: ${err}`);
    }
  };

  const filtered = memories.filter(
    (m) => m.key.toLowerCase().includes(search.toLowerCase()) || m.value.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{
      position: "fixed",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      width: "min(780px, 92vw)",
      maxHeight: "82vh",
      background: "rgba(10, 22, 38, 0.96)",
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
          <span style={{ fontSize: "20px" }}>🧠</span>
          <div>
            <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#64ffda", letterSpacing: "1px" }}>
              PERSISTENT MEMORY & USER PREFERENCES
            </h2>
            <p style={{ margin: 0, fontSize: "11px", color: "#94a3b8" }}>
              Long-term user preferences, hardware specifications, and project facts
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

      {/* Add / Search Bar */}
      <div style={{ padding: "14px 24px", background: "rgba(15, 30, 50, 0.4)", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", display: "flex", flexDirection: "column", gap: "10px" }}>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="🔍 Search stored memories..."
          style={{ width: "100%", padding: "7px 12px", background: "rgba(8, 16, 28, 0.8)", border: "1px solid rgba(255, 255, 255, 0.1)", borderRadius: "6px", color: "#fff", fontSize: "12px", boxSizing: "border-box" }}
        />

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <input
            type="text"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="Fact / Key (e.g. primary_language)"
            style={{ flex: 1, padding: "7px 10px", background: "rgba(8, 16, 28, 0.8)", border: "1px solid rgba(0, 217, 255, 0.3)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
          />
          <input
            type="text"
            value={newVal}
            onChange={(e) => setNewVal(e.target.value)}
            placeholder="Value / Details (e.g. Python and Rust)"
            style={{ flex: 2, padding: "7px 10px", background: "rgba(8, 16, 28, 0.8)", border: "1px solid rgba(0, 217, 255, 0.3)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
          />
          <button
            onClick={handleAdd}
            style={{ padding: "7px 16px", background: "#00d9ff", border: "none", borderRadius: "6px", color: "#0f172a", fontWeight: 700, fontSize: "11px", cursor: "pointer" }}
          >
            + REMEMBER
          </button>
        </div>
      </div>

      {/* Memory List */}
      <div style={{ flex: 1, overflowY: "auto", padding: "18px 24px" }}>
        {loading && <p style={{ textAlign: "center", color: "#64ffda" }}>Loading memory store...</p>}

        {!loading && filtered.length === 0 && (
          <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            No memories match your query.
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {filtered.map((m) => (
            <div
              key={m.key}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 16px",
                background: "rgba(15, 30, 50, 0.6)",
                border: "1px solid rgba(0, 217, 255, 0.15)",
                borderRadius: "8px",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <strong style={{ color: "#64ffda", fontSize: "13px" }}>{m.key}</strong>
                  <span style={{ fontSize: "10px", padding: "2px 6px", background: "rgba(255, 255, 255, 0.08)", borderRadius: "4px", color: "#94a3b8" }}>
                    {m.category}
                  </span>
                </div>
                <p style={{ margin: "4px 0 0 0", fontSize: "12.5px", color: "#e2e8f0" }}>{m.value}</p>
              </div>

              <button
                onClick={() => handleDelete(m.key)}
                style={{ background: "transparent", border: "1px solid rgba(239, 68, 68, 0.4)", color: "#ef4444", padding: "4px 8px", borderRadius: "6px", fontSize: "11px", cursor: "pointer" }}
              >
                FORGET
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
