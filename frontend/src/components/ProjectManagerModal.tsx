import { useEffect, useState } from "react";
import { addProjectTask, createProject, fetchProjects, ProjectItem, toggleProjectTask, updateProjectNotes } from "../api/projects";

type ProjectManagerModalProps = {
  activeProjectId?: string;
  onSelectProject: (projectId: string | undefined) => void;
  onClose: () => void;
};

export function ProjectManagerModal({ activeProjectId, onSelectProject, onClose }: ProjectManagerModalProps) {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [selectedProj, setSelectedProj] = useState<ProjectItem | null>(null);
  const [newProjName, setNewProjName] = useState("");
  const [newProjDesc, setNewProjDesc] = useState("");
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);

  const refreshProjects = async () => {
    setLoading(true);
    try {
      const data = await fetchProjects();
      setProjects(data);
      if (data.length > 0) {
        const found = data.find((p) => p.id === activeProjectId) || data[0];
        setSelectedProj(found);
        setNotes(found.notes || "");
      }
    } catch {
      // Offline / error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshProjects();
  }, []);

  const handleCreateProject = async () => {
    if (!newProjName.trim()) return;
    try {
      const p = await createProject(newProjName, newProjDesc);
      setNewProjName("");
      setNewProjDesc("");
      await refreshProjects();
      setSelectedProj(p);
      onSelectProject(p.id);
    } catch (err) {
      alert(`Create project error: ${err}`);
    }
  };

  const handleAddTask = async () => {
    if (!selectedProj || !newTaskTitle.trim()) return;
    try {
      const updated = await addProjectTask(selectedProj.id, newTaskTitle);
      setSelectedProj(updated);
      setNewTaskTitle("");
      await refreshProjects();
    } catch (err) {
      alert(`Task error: ${err}`);
    }
  };

  const handleToggleTask = async (taskId: string) => {
    if (!selectedProj) return;
    try {
      const updated = await toggleProjectTask(selectedProj.id, taskId);
      setSelectedProj(updated);
      await refreshProjects();
    } catch (err) {
      alert(`Toggle error: ${err}`);
    }
  };

  const handleSaveNotes = async () => {
    if (!selectedProj) return;
    try {
      const updated = await updateProjectNotes(selectedProj.id, notes);
      setSelectedProj(updated);
      alert("Project context notes updated!");
    } catch (err) {
      alert(`Notes error: ${err}`);
    }
  };

  return (
    <div style={{
      position: "fixed",
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      width: "min(880px, 94vw)",
      height: "min(680px, 86vh)",
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
          <span style={{ fontSize: "20px" }}>📁</span>
          <div>
            <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#64ffda", letterSpacing: "1px" }}>
              PROJECT & MISSION CONTROL
            </h2>
            <p style={{ margin: 0, fontSize: "11px", color: "#94a3b8" }}>
              Contextual workspace projects, tasks, linked research, and persistence
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

      {/* Main Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", flex: 1, overflow: "hidden" }}>
        {/* Left Project List */}
        <div style={{ borderRight: "1px solid rgba(255, 255, 255, 0.08)", background: "rgba(8, 16, 28, 0.6)", padding: "16px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "12px" }}>
          <h4 style={{ margin: "0 0 8px 0", fontSize: "11px", color: "#64ffda", letterSpacing: "1px" }}>PROJECTS</h4>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {projects.map((p) => {
              const isSelected = selectedProj?.id === p.id;
              const isActiveContext = activeProjectId === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => { setSelectedProj(p); setNotes(p.notes || ""); }}
                  style={{
                    padding: "10px 12px",
                    background: isSelected ? "rgba(0, 217, 255, 0.2)" : "rgba(15, 30, 50, 0.5)",
                    border: isSelected ? "1px solid #00d9ff" : "1px solid rgba(255, 255, 255, 0.05)",
                    borderRadius: "8px",
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "13px", fontWeight: 600, color: "#ffffff" }}>{p.name}</span>
                    {isActiveContext && (
                      <span style={{ fontSize: "9px", padding: "2px 6px", background: "#10b981", color: "#0f172a", borderRadius: "4px", fontWeight: 700 }}>
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <p style={{ margin: "3px 0 0 0", fontSize: "11px", color: "#94a3b8" }}>{p.tasks.filter(t => !t.completed).length} open tasks</p>
                </div>
              );
            })}
          </div>

          {/* New Project Creator */}
          <div style={{ marginTop: "auto", paddingTop: "14px", borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
            <h5 style={{ margin: "0 0 8px 0", fontSize: "11px", color: "#94a3b8" }}>CREATE PROJECT</h5>
            <input
              type="text"
              value={newProjName}
              onChange={(e) => setNewProjName(e.target.value)}
              placeholder="Project Name..."
              style={{ width: "100%", padding: "6px 10px", background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "6px", color: "#fff", fontSize: "12px", marginBottom: "6px", boxSizing: "border-box" }}
            />
            <input
              type="text"
              value={newProjDesc}
              onChange={(e) => setNewProjDesc(e.target.value)}
              placeholder="Description..."
              style={{ width: "100%", padding: "6px 10px", background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "6px", color: "#fff", fontSize: "12px", marginBottom: "8px", boxSizing: "border-box" }}
            />
            <button
              onClick={handleCreateProject}
              style={{ width: "100%", padding: "7px", background: "rgba(0, 217, 255, 0.2)", border: "1px solid #00d9ff", borderRadius: "6px", color: "#00d9ff", fontWeight: 700, fontSize: "11px", cursor: "pointer" }}
            >
              + NEW PROJECT
            </button>
          </div>
        </div>

        {/* Right Detail Pane */}
        {selectedProj ? (
          <div style={{ padding: "20px 24px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "18px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h2 style={{ margin: 0, fontSize: "18px", color: "#64ffda" }}>{selectedProj.name}</h2>
                <p style={{ margin: "3px 0 0 0", fontSize: "12px", color: "#94a3b8" }}>{selectedProj.description || "No description provided."}</p>
              </div>
              <button
                onClick={() => onSelectProject(activeProjectId === selectedProj.id ? undefined : selectedProj.id)}
                style={{
                  padding: "7px 16px",
                  background: activeProjectId === selectedProj.id ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.2)",
                  border: activeProjectId === selectedProj.id ? "1px solid #ef4444" : "1px solid #10b981",
                  borderRadius: "8px",
                  color: activeProjectId === selectedProj.id ? "#ef4444" : "#10b981",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {activeProjectId === selectedProj.id ? "⚡ DEACTIVATE CONTEXT" : "🎯 SET AS ACTIVE CONTEXT"}
              </button>
            </div>

            {/* Tasks Section */}
            <div style={{ background: "rgba(15, 30, 50, 0.4)", padding: "16px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
              <h4 style={{ margin: "0 0 12px 0", fontSize: "13px", color: "#00d9ff" }}>TASK CHECKLIST</h4>
              
              <div style={{ display: "flex", gap: "8px", marginBottom: "12px" }}>
                <input
                  type="text"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  placeholder="Add a new milestone or task..."
                  onKeyDown={(e) => e.key === "Enter" && handleAddTask()}
                  style={{ flex: 1, padding: "7px 12px", background: "rgba(8, 16, 28, 0.8)", border: "1px solid rgba(0, 217, 255, 0.3)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
                />
                <button
                  onClick={handleAddTask}
                  style={{ padding: "7px 16px", background: "#00d9ff", border: "none", borderRadius: "6px", color: "#0f172a", fontWeight: 700, fontSize: "11px", cursor: "pointer" }}
                >
                  ADD TASK
                </button>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {selectedProj.tasks.map((t) => (
                  <div
                    key={t.id}
                    onClick={() => handleToggleTask(t.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      padding: "8px 12px",
                      background: "rgba(10, 20, 35, 0.6)",
                      borderRadius: "6px",
                      cursor: "pointer",
                    }}
                  >
                    <input type="checkbox" checked={t.completed} readOnly style={{ cursor: "pointer" }} />
                    <span style={{ fontSize: "12.5px", color: t.completed ? "#64748b" : "#f1f5f9", textDecoration: t.completed ? "line-through" : "none" }}>
                      {t.title}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Context Notes */}
            <div style={{ background: "rgba(15, 30, 50, 0.4)", padding: "16px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <h4 style={{ margin: 0, fontSize: "13px", color: "#00d9ff" }}>PROJECT MEMORY & PERSISTENT NOTES</h4>
                <button
                  onClick={handleSaveNotes}
                  style={{ padding: "4px 12px", background: "rgba(100, 255, 218, 0.2)", border: "1px solid #64ffda", borderRadius: "6px", color: "#64ffda", fontSize: "11px", fontWeight: 700, cursor: "pointer" }}
                >
                  💾 SAVE NOTES
                </button>
              </div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={5}
                placeholder="Write specific context, equations, or hardware notes for JARVIS to keep in mind when working on this project..."
                style={{ width: "100%", padding: "10px", background: "rgba(8, 16, 28, 0.8)", border: "1px solid rgba(255, 255, 255, 0.1)", borderRadius: "8px", color: "#e2e8f0", fontSize: "12px", boxSizing: "border-box", resize: "vertical" }}
              />
            </div>
          </div>
        ) : (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
            Select or create a project to manage tasks and contextual memory.
          </div>
        )}
      </div>
    </div>
  );
}
