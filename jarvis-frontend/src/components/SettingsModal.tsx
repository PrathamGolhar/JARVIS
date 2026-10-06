import { useEffect, useRef, useState } from "react";
import { fetchSettings, SettingsStatus, updateSettings } from "../api/settings";
import { Voice } from "../api/speech";
import { showToast } from "./ToastNotificationSystem";

type SettingsModalProps = {
  voices: Voice[];
  selectedVoiceId: string;
  onSelectVoice: (id: string) => void;
  wakeWordEnabled: boolean;
  onToggleWakeWord: (enabled: boolean) => void;
  onClose: () => void;
};

export function SettingsModal({
  voices,
  selectedVoiceId,
  onSelectVoice,
  wakeWordEnabled,
  onToggleWakeWord,
  onClose,
}: SettingsModalProps) {
  const [settingsStatus, setSettingsStatus] = useState<SettingsStatus | null>(null);
  const [aiProvider, setAiProvider] = useState("auto");
  const [geminiKey, setGeminiKey] = useState("");
  const [groqKey, setGroqKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [elevenlabsKey, setElevenlabsKey] = useState("");
  const [permissionMode, setPermissionMode] = useState("assisted");
  const [saving, setSaving] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const titleId = "settings-modal-title";

  useEffect(() => {
    void (async () => {
      try {
        const s = await fetchSettings();
        setSettingsStatus(s);
        setAiProvider(s.aiProvider);
        setPermissionMode(s.permissionMode);
      } catch {
        // Error
      }
    })();
  }, []);

  // Escape key handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    // Focus trap: move focus to dialog on mount
    dialogRef.current?.focus();
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateSettings({
        aiProvider,
        geminiApiKey: geminiKey || undefined,
        groqApiKey: groqKey || undefined,
        openaiApiKey: openaiKey || undefined,
        anthropicApiKey: anthropicKey || undefined,
        elevenlabsApiKey: elevenlabsKey || undefined,
        permissionMode,
        wakeWordEnabled,
      });
      setSettingsStatus(updated);
      showToast({
        title: "Configuration Saved",
        message: "JARVIS system settings have been updated.",
        type: "success",
      });
    } catch (err) {
      showToast({
        title: "Save Failed",
        message: err instanceof Error ? err.message : "Could not update settings.",
        type: "error",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.6)",
          backdropFilter: "blur(4px)",
          zIndex: 999,
        }}
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: "min(760px, 92vw)",
          maxHeight: "86vh",
          background: "rgba(10, 22, 38, 0.96)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(0, 217, 255, 0.4)",
          borderRadius: "16px",
          boxShadow: "0 0 40px rgba(0, 217, 255, 0.25), 0 20px 50px rgba(0, 0, 0, 0.8)",
          display: "flex",
          flexDirection: "column",
          zIndex: 1000,
          color: "#e2e8f0",
          fontFamily: "var(--font-body, Segoe UI, sans-serif)",
          overflow: "hidden",
          outline: "none",
        }}
      >
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
          <span style={{ fontSize: "20px" }} aria-hidden="true">⚙️</span>
          <div>
            <h2 id={titleId} style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#64ffda", letterSpacing: "1px" }}>
              SYSTEM CONFIGURATION & SECURITY
            </h2>
            <p style={{ margin: 0, fontSize: "11px", color: "#94a3b8" }}>
              AI providers, neural voices, wake word detection, and authorization tiers
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Close settings"
          style={{ background: "transparent", border: "none", color: "#94a3b8", fontSize: "20px", cursor: "pointer", lineHeight: 1 }}
        >
          ✕
        </button>
      </div>

      {/* Main Settings Form */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: "20px" }}>
        {/* Section 1: AI Provider */}
        <div style={{ background: "rgba(15, 30, 50, 0.5)", padding: "16px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
          <h3 style={{ margin: "0 0 12px 0", fontSize: "13px", color: "#00d9ff" }}>1. AI MODEL PROVIDER</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "8px", marginBottom: "14px" }}>
            {["auto", "gemini", "groq", "openai", "local"].map((p) => {
              const isSelected = aiProvider === p;
              return (
                <button
                  key={p}
                  onClick={() => setAiProvider(p)}
                  style={{
                    padding: "8px 12px",
                    background: isSelected ? "rgba(0, 217, 255, 0.25)" : "rgba(8, 16, 28, 0.6)",
                    border: isSelected ? "1px solid #00d9ff" : "1px solid rgba(255, 255, 255, 0.1)",
                    borderRadius: "6px",
                    color: isSelected ? "#ffffff" : "#94a3b8",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                    textTransform: "uppercase",
                  }}
                >
                  {p === "auto" ? "⚡ AUTO-DETECT" : p}
                </button>
              );
            })}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div>
              <label style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                Google Gemini API Key {settingsStatus?.geminiConfigured && <span style={{ color: "#10b981" }}>(Configured)</span>}
              </label>
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="AIzaSy..."
                style={{ width: "100%", padding: "7px 10px", background: "rgba(8, 16, 28, 0.8)", border: "1px solid rgba(255, 255, 255, 0.12)", borderRadius: "6px", color: "#fff", fontSize: "12px", boxSizing: "border-box" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                Groq API Key {settingsStatus?.groqConfigured && <span style={{ color: "#10b981" }}>(Configured)</span>}
              </label>
              <input
                type="password"
                value={groqKey}
                onChange={(e) => setGroqKey(e.target.value)}
                placeholder="gsk_..."
                style={{ width: "100%", padding: "7px 10px", background: "rgba(8, 16, 28, 0.8)", border: "1px solid rgba(255, 255, 255, 0.12)", borderRadius: "6px", color: "#fff", fontSize: "12px", boxSizing: "border-box" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                OpenAI API Key {settingsStatus?.openaiConfigured && <span style={{ color: "#10b981" }}>(Configured)</span>}
              </label>
              <input
                type="password"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder="sk-..."
                style={{ width: "100%", padding: "7px 10px", background: "rgba(8, 16, 28, 0.8)", border: "1px solid rgba(255, 255, 255, 0.12)", borderRadius: "6px", color: "#fff", fontSize: "12px", boxSizing: "border-box" }}
              />
            </div>
          </div>
        </div>

        {/* Section 2: Voice & Wake Word */}
        <div style={{ background: "rgba(15, 30, 50, 0.5)", padding: "16px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
          <h3 style={{ margin: "0 0 12px 0", fontSize: "13px", color: "#00d9ff" }}>2. NEURAL VOICE & WAKE WORD</h3>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", alignItems: "center" }}>
            <div>
              <label style={{ fontSize: "11px", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                Synthesis Voice (Edge-TTS Neural)
              </label>
              <select
                value={selectedVoiceId}
                onChange={(e) => onSelectVoice(e.target.value)}
                style={{ width: "100%", padding: "8px 10px", background: "rgba(8, 16, 28, 0.9)", border: "1px solid rgba(0, 217, 255, 0.3)", borderRadius: "6px", color: "#fff", fontSize: "12px" }}
              >
                {voices.map((v) => (
                  <option key={v.id} value={v.id}>{v.label}</option>
                ))}
              </select>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(8, 16, 28, 0.6)", padding: "10px 14px", borderRadius: "8px", border: "1px solid rgba(255, 255, 255, 0.1)" }}>
              <div>
                <span style={{ fontSize: "12.5px", fontWeight: 600, color: "#ffffff", display: "block" }}>Wake Word ("JARVIS")</span>
                <span style={{ fontSize: "10px", color: "#94a3b8" }}>Voice-activated trigger</span>
              </div>
              <input
                type="checkbox"
                checked={wakeWordEnabled}
                onChange={(e) => onToggleWakeWord(e.target.checked)}
                style={{ width: "18px", height: "18px", cursor: "pointer" }}
              />
            </div>
          </div>
        </div>

        {/* Section 3: Safety & Permission Level */}
        <div style={{ background: "rgba(15, 30, 50, 0.5)", padding: "16px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
          <h3 style={{ margin: "0 0 12px 0", fontSize: "13px", color: "#00d9ff" }}>3. SECURITY & PERMISSION TIER</h3>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
            {[
              { id: "read_only", label: "READ ONLY", desc: "No file writes or desktop launches" },
              { id: "assisted", label: "ASSISTED (Recommended)", desc: "Requires confirmation modal for high-impact actions" },
              { id: "full_control", label: "FULL CONTROL", desc: "Auto-executes all approved workspace tools" },
            ].map((tier) => {
              const isSelected = permissionMode === tier.id;
              return (
                <div
                  key={tier.id}
                  onClick={() => setPermissionMode(tier.id)}
                  style={{
                    padding: "10px 12px",
                    background: isSelected ? "rgba(0, 217, 255, 0.2)" : "rgba(8, 16, 28, 0.6)",
                    border: isSelected ? "1px solid #00d9ff" : "1px solid rgba(255, 255, 255, 0.1)",
                    borderRadius: "8px",
                    cursor: "pointer",
                  }}
                >
                  <strong style={{ fontSize: "12px", color: isSelected ? "#64ffda" : "#ffffff", display: "block" }}>{tier.label}</strong>
                  <p style={{ margin: "4px 0 0 0", fontSize: "10.5px", color: "#94a3b8" }}>{tier.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

        {/* Footer */}
        <div style={{ padding: "14px 24px", background: "rgba(5, 12, 24, 0.8)", borderTop: "1px solid rgba(255, 255, 255, 0.08)", display: "flex", justifyContent: "flex-end", gap: "10px" }}>
          <button
            onClick={onClose}
            style={{ padding: "8px 18px", background: "transparent", border: "1px solid rgba(255, 255, 255, 0.2)", borderRadius: "8px", color: "#94a3b8", fontSize: "12px", cursor: "pointer" }}
          >
            CLOSE
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{ padding: "8px 24px", background: "linear-gradient(135deg, #00d9ff, #0284c7)", border: "none", borderRadius: "8px", color: "#0f172a", fontWeight: 700, fontSize: "12px", cursor: "pointer", boxShadow: "0 0 15px rgba(0, 217, 255, 0.3)" }}
          >
            {saving ? "SAVING..." : "💾 SAVE SETTINGS"}
          </button>
        </div>
      </div>
    </>
  );
}
