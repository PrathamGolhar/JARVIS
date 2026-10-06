from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

AssistantMode = Literal[
    "general",
    "study",
    "research",
    "coding",
    "project",
    "document",
    "presentation",
    "automation",
    "voice",
]


class Citation(BaseModel):
    title: str
    url: str
    domain: str = ""
    snippet: str = ""


class ToolEvent(BaseModel):
    tool_name: str = Field(alias="toolName")
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = Field(default=False, alias="requiresConfirmation")


class PlanStep(BaseModel):
    step_number: int = Field(alias="stepNumber")
    title: str
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    detail: str = ""


class PendingAction(BaseModel):
    action_id: str = Field(alias="actionId")
    tool_name: str = Field(alias="toolName")
    arguments: dict[str, Any] = Field(default_factory=dict)
    label: str
    description: str
    requires_confirmation: bool = Field(default=True, alias="requiresConfirmation")


class ChatRequest(BaseModel):
    session_id: UUID = Field(alias="sessionId")
    text: str = Field(min_length=1, max_length=50_000)
    mode: AssistantMode = "general"
    project_id: str | None = Field(default=None, alias="projectId")
    confirmed_action_id: str | None = Field(default=None, alias="confirmedActionId")


class ChatResponse(BaseModel):
    session_id: UUID = Field(alias="sessionId")
    reply: str
    mode: AssistantMode = "general"
    turns_retained: int = Field(default=0, alias="turnsRetained")
    citations: list[Citation] = Field(default_factory=list)
    tool_events: list[ToolEvent] = Field(default_factory=list, alias="toolEvents")
    plan_steps: list[PlanStep] = Field(default_factory=list, alias="planSteps")
    pending_action: PendingAction | None = Field(default=None, alias="pendingAction")
    generated_files: list[dict[str, Any]] = Field(default_factory=list, alias="generatedFiles")


# Local & Web Action Schemas
class LocalActionPlanRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2_000)


class LocalActionPlanResponse(BaseModel):
    kind: Literal["open_local_app"]
    app_id: Literal["calculator", "notepad", "file_explorer", "vscode"] = Field(alias="appId")
    label: str = Field(min_length=1, max_length=160)
    requires_confirmation: bool = Field(alias="requiresConfirmation")


class LocalActionExecuteRequest(BaseModel):
    app_id: Literal["calculator", "notepad", "file_explorer", "vscode"] = Field(alias="appId")
    confirmed: Literal[True]


class LocalActionExecuteResponse(BaseModel):
    ok: bool
    message: str


class LocalActionStatusResponse(BaseModel):
    enabled: bool


class WebActionPlanRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2_000)


class WebActionPlanResponse(BaseModel):
    kind: Literal["open_website", "web_search", "youtube_search", "spotify_search"]
    label: str = Field(min_length=1, max_length=160)
    url: str = Field(min_length=1, max_length=2_000)


# Voice & Audio
class Voice(BaseModel):
    id: str
    label: str


class VoicesResponse(BaseModel):
    voices: list[Voice]


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8_000)
    voice_id: str = Field(alias="voiceId")
    rate: str = "+0%"
    pitch: str = "+0Hz"


class TranscriptResponse(BaseModel):
    transcript: str


# File Upload & Analysis
class FileUploadResponse(BaseModel):
    ok: bool
    file_id: str = Field(alias="fileId")
    filename: str
    file_type: str = Field(alias="fileType")
    size_bytes: int = Field(alias="sizeBytes")
    extracted_text_preview: str = Field(alias="extractedTextPreview")
    total_pages_or_lines: int = Field(default=1, alias="totalPagesOrLines")
    detected_topics: list[str] = Field(default_factory=list, alias="detectedTopics")
    message: str


class FileAnalysisRequest(BaseModel):
    file_id: str = Field(alias="fileId")
    action: Literal["summarize", "detailed_notes", "extract_formulas", "exam_mcqs", "presentation_outline", "explain"] = "detailed_notes"
    depth: Literal["brief", "standard", "comprehensive"] = "standard"


# Study Mode Schemas
class FormulaItem(BaseModel):
    name: str
    formula: str
    explanation: str
    variables: dict[str, str] = Field(default_factory=dict)


class DefinitionItem(BaseModel):
    term: str
    definition: str
    example: str = ""


class MCQItem(BaseModel):
    id: int
    question: str
    options: list[str]
    correct_option_index: int = Field(alias="correctOptionIndex")
    difficulty: Literal["Easy", "Medium", "Hard", "Exam Level"] = "Medium"
    hint: str = ""
    solution: str = ""
    explanation: str = ""


class FlashcardItem(BaseModel):
    front: str
    back: str
    topic: str = ""


class StudyNotesRequest(BaseModel):
    topic_or_text: str = Field(alias="topicOrText")
    file_id: str | None = Field(default=None, alias="fileId")
    subject: str = "General"
    include_formulas: bool = Field(default=True, alias="includeFormulas")
    include_practice_questions: bool = Field(default=True, alias="includePracticeQuestions")
    format_output: Literal["json", "pdf", "docx"] = "json"


class StudyNotesResponse(BaseModel):
    title: str
    subject: str
    summary: str
    key_concepts: list[str] = Field(default_factory=list, alias="keyConcepts")
    definitions: list[DefinitionItem] = Field(default_factory=list)
    formulas: list[FormulaItem] = Field(default_factory=list)
    detailed_notes_markdown: str = Field(alias="detailedNotesMarkdown")
    practice_questions: list[MCQItem] = Field(default_factory=list, alias="practiceQuestions")
    flashcards: list[FlashcardItem] = Field(default_factory=list)
    generated_file_url: str | None = Field(default=None, alias="generatedFileUrl")


# Document & Presentation Generation
class SlideContent(BaseModel):
    title: str
    bullets: list[str] = Field(default_factory=list)
    subtitle: str = ""
    speaker_notes: str = Field(default="", alias="speakerNotes")
    layout_style: Literal["standard", "two_column", "quote", "highlight", "conclusion"] = "standard"


class GeneratePptxRequest(BaseModel):
    topic: str
    slides: list[SlideContent] = Field(default_factory=list)
    theme_color: str = "cyan"
    file_id: str | None = Field(default=None, alias="fileId")
    num_slides: int = Field(default=6, ge=1, le=50, alias="numSlides")


class GeneratePdfRequest(BaseModel):
    title: str
    subtitle: str = ""
    content_markdown: str = Field(alias="contentMarkdown")
    subject: str = "JARVIS Report"
    include_cover: bool = Field(default=True, alias="includeCover")
    theme: str = "futuristic"


class GenerateDocxRequest(BaseModel):
    title: str
    subtitle: str = ""
    content_markdown: str = Field(alias="contentMarkdown")
    author: str = "JARVIS AI"


class GenerateXlsxRequest(BaseModel):
    filename: str
    sheet_name: str = "Data Sheet"
    headers: list[str]
    rows: list[list[Any]]
    include_summary_row: bool = Field(default=True, alias="includeSummaryRow")


class GeneratedFileItem(BaseModel):
    id: str
    filename: str
    file_type: str = Field(alias="fileType")
    size_bytes: int = Field(alias="sizeBytes")
    created_at: str = Field(alias="createdAt")
    download_url: str = Field(alias="downloadUrl")
    description: str = ""


# Web Research Schemas
class ResearchRequest(BaseModel):
    query: str
    depth: Literal["quick", "deep", "comprehensive"] = "deep"
    generate_document: Literal["none", "pdf", "docx", "pptx"] = "none"


class ResearchResponse(BaseModel):
    topic: str
    summary: str
    findings_markdown: str = Field(alias="findingsMarkdown")
    citations: list[Citation]
    key_takeaways: list[str] = Field(default_factory=list, alias="keyTakeaways")
    generated_file_url: str | None = Field(default=None, alias="generatedFileUrl")


# Code Assistant & Sandbox
class CodeExecutionRequest(BaseModel):
    code: str
    language: Literal["python", "javascript", "typescript", "cpp", "c", "java"] = "python"
    stdin_input: str = Field(default="", alias="stdinInput")
    timeout_seconds: int = Field(default=10, ge=1, le=30, alias="timeoutSeconds")


class CodeExecutionResponse(BaseModel):
    ok: bool
    stdout: str
    stderr: str
    exit_code: int = Field(alias="exitCode")
    execution_time_ms: float = Field(alias="executionTimeMs")
    memory_mb: float = Field(default=0.0, alias="memoryMb")


class CodeAnalysisRequest(BaseModel):
    code: str
    language: str = "python"
    task: Literal["explain", "debug", "refactor", "generate_tests", "optimize"] = "explain"


class CodeAnalysisResponse(BaseModel):
    analysis: str
    fixed_or_improved_code: str = Field(default="", alias="fixedOrImprovedCode")
    test_code: str = Field(default="", alias="testCode")
    complexity_score: str = Field(default="", alias="complexityScore")


# Projects
class ProjectTaskItem(BaseModel):
    id: str
    title: str
    completed: bool = False
    due_date: str | None = Field(default=None, alias="dueDate")


class ProjectItem(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    tasks: list[ProjectTaskItem] = Field(default_factory=list)
    linked_files: list[str] = Field(default_factory=list, alias="linkedFiles")
    notes: str = ""


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""


# Memory & Preferences
class MemoryItem(BaseModel):
    key: str
    value: str
    category: str = "general"
    updated_at: str = Field(alias="updatedAt")


class MemorySetRequest(BaseModel):
    key: str
    value: str
    category: str = "general"


# Automation & Reminders
class ReminderItem(BaseModel):
    id: str
    title: str
    scheduled_time: str = Field(alias="scheduledTime")
    recurring: str | None = None
    completed: bool = False
    created_at: str = Field(alias="createdAt")


class ReminderCreateRequest(BaseModel):
    title: str
    scheduled_time: str = Field(alias="scheduledTime")
    recurring: str | None = None


# Diagnostics & Settings
class DiagnosticItem(BaseModel):
    id: str
    label: str
    status: Literal["ready", "active", "warning", "error", "unconfigured"]
    latency_ms: float | None = Field(default=None, alias="latencyMs")
    details: str = ""


class SystemMetrics(BaseModel):
    cpu_percent: float = Field(alias="cpuPercent")
    ram_percent: float = Field(alias="ramPercent")
    disk_free_gb: float = Field(alias="diskFreeGb")
    active_tools_count: int = Field(alias="activeToolsCount")
    memory_items_count: int = Field(alias="memoryItemsCount")
    uptime: str


class DiagnosticsResponse(BaseModel):
    ok: bool
    timestamp: str
    items: list[DiagnosticItem]
    system_metrics: SystemMetrics = Field(alias="systemMetrics")


class SettingsStatusResponse(BaseModel):
    ai_provider: str = Field(alias="aiProvider")
    available_providers: list[str] = Field(alias="availableProviders")
    active_model: str = Field(alias="activeModel")
    gemini_configured: bool = Field(alias="geminiConfigured")
    groq_configured: bool = Field(alias="groqConfigured")
    openai_configured: bool = Field(alias="openaiConfigured")
    anthropic_configured: bool = Field(alias="anthropicConfigured")
    elevenlabs_configured: bool = Field(alias="elevenlabsConfigured")
    permission_mode: str = Field(alias="permissionMode")
    wake_word_enabled: bool = Field(alias="wakeWordEnabled")


class SettingsUpdateRequest(BaseModel):
    ai_provider: str | None = Field(default=None, alias="aiProvider")
    gemini_api_key: str | None = Field(default=None, alias="geminiApiKey")
    groq_api_key: str | None = Field(default=None, alias="groqApiKey")
    openai_api_key: str | None = Field(default=None, alias="openaiApiKey")
    anthropic_api_key: str | None = Field(default=None, alias="anthropicApiKey")
    elevenlabs_api_key: str | None = Field(default=None, alias="elevenlabsApiKey")
    permission_mode: str | None = Field(default=None, alias="permissionMode")
    wake_word_enabled: bool | None = Field(default=None, alias="wakeWordEnabled")
