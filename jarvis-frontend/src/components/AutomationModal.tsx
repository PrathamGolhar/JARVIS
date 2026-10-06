import { useEffect, useState } from "react";
import { createReminder, deleteReminder, fetchReminders, ReminderItem, toggleReminder } from "../api/automation";

type AutomationModalProps = {
  onClose: () => void;
};

export function AutomationModal({ onClose }: AutomationModalProps) {
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [title, setTitle] = useState("");
  const [scheduledTime, setScheduledTime] = useState("");
  const [recurring, setRecurring] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await fetchReminders();
      setReminders(data);
    } catch {
      // Error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const handleCreate = async () => {
    if (!title.trim() || !scheduledTime.trim()) return;
    try {
      await createReminder(title, scheduledTime, recurring || undefined);
      setTitle("");
      setScheduledTime("");
      setRecurring("");
      await refresh();
    } catch (err) {
      alert(`Create reminder error: ${err}`);
    }
  };

  const handleToggle = async (id: string) => {
    try {
      await toggleReminder(id);
      await refresh();
    } catch (err) {
      alert(`Toggle error: ${err}`);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteReminder(id);
      await refresh();
    } catch (err) {
      alert(`Delete error: ${err}`);
    }
  };

  return (
    <div style={{
      position: "fixed",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      width: "min(720px, 92vw)",
      maxHeight: "80vh",
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
          <span style={{ fontSize: "20px" }}>⏰</span>
          <div>
            <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#64ffda", letterSpacing: "1px" }}>
              AUTOMATION & SCHEDULED REMINDERS
            </h2>
            <p style={{ margin: 0, fontSize: "11px", color: "#94a3b8" }}>
              Autonomous cron tasks, scheduled alerts, and multi-step workflows
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

      {/* Input Bar */}
      <div style={{ padding: "14px 24px", background: "rgba(15, 30, 50, 0.4)", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Reminder Title (e.g. Review Research Notes)..."
          style={{ flex: 2, minWidth: "200px", padding: "7px 10px", background: "rgba(8, 16, 28, 0.8)", border: "1px solid rgba(0, 217, 255, 0.3)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
        />
        <input
          type="text"
          value={scheduledTime}
          onChange={(e) => setScheduledTime(e.target.value)}
          placeholder="Time (e.g. Tomorrow 8:00 AM)"
          style={{ flex: 1, minWidth: "140px", padding: "7px 10px", background: "rgba(8, 16, 28, 0.8)", border: "1px solid rgba(255, 255, 255, 0.15)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
        />
        <button
          onClick={handleCreate}
          disabled={!title.trim() || !scheduledTime.trim()}
          style={{ padding: "7px 16px", background: "#00d9ff", border: "none", borderRadius: "6px", color: "#0f172a", fontWeight: 700, fontSize: "11px", cursor: "pointer" }}
        >
          + SCHEDULE
        </button>
      </div>

      {/* List */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {loading && <p style={{ textAlign: "center", color: "#64ffda" }}>Loading scheduled tasks...</p>}

        {!loading && reminders.length === 0 && (
          <div style={{ textAlign: "center", padding: "50px 20px", color: "#64748b" }}>
            <span style={{ fontSize: "36px", display: "block", marginBottom: "10px" }}>⏳</span>
            <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8" }}>No active reminders scheduled.</p>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {reminders.map((r) => (
            <div
              key={r.id}
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
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <input
                  type="checkbox"
                  checked={r.completed}
                  onChange={() => handleToggle(r.id)}
                  style={{ cursor: "pointer" }}
                />
                <div>
                  <h4 style={{ margin: 0, fontSize: "13px", color: r.completed ? "#64748b" : "#ffffff", textDecoration: r.completed ? "line-through" : "none" }}>
                    {r.title}
                  </h4>
                  <p style={{ margin: "2px 0 0 0", fontSize: "11px", color: "#64ffda" }}>
                    Scheduled for: {r.scheduledTime}
                  </p>
                </div>
              </div>

              <button
                onClick={() => handleDelete(r.id)}
                style={{ background: "transparent", border: "1px solid rgba(239, 68, 68, 0.4)", color: "#ef4444", padding: "4px 8px", borderRadius: "6px", fontSize: "11px", cursor: "pointer" }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
