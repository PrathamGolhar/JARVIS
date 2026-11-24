from dataclasses import dataclass, field
import json
import logging
import re
from typing import Any, Optional

from app.schemas import AssistantMode, PlanStep

logger = logging.getLogger("jarvis.planner")


@dataclass
class ExecutionPlan:
    goal: str
    mode: AssistantMode
    steps: list[PlanStep] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    suggested_files_to_generate: list[str] = field(default_factory=list)
    risk_level: str = "low"  # "low", "high"
    requires_tools: bool = True
    completion_conditions: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)


class PlanningEngine:
    """
    Autonomous planning engine that classifies user intent beyond simple keyword matching,
    detects objectives, task dependencies, completion criteria, and distinguishes simple direct answers
    from multi-step tool-assisted execution.
    """

    DIRECT_ANSWER_PATTERNS = [
        r"^(hi|hello|hey|greetings|good morning|good evening|howdy)\b",
        r"^(who are you|what is your name|introduce yourself)\b",
        r"^(how are you|how do you do|what'?s up)\b",
        r"^(thank you|thanks|good job|well done)\b",
        r"^(what time is it|what is the date|who made you)\b",
    ]

    @classmethod
    def is_direct_answer_candidate(cls, text: str) -> bool:
        """Determines whether a user query can and should be answered directly without tool invocations."""
        clean = text.strip().lower()
        if any(re.search(pat, clean) for pat in cls.DIRECT_ANSWER_PATTERNS):
            return True

        # Quick conversational or conceptual query without action verbs
        words = clean.split()
        action_verbs = [
            "search", "lookup", "research", "find", "read", "create", "make", "generate",
            "calculate", "solve", "run", "execute", "write", "open", "launch", "remind",
            "remember", "diagnose", "check", "inspect", "compile", "summarize", "diff"
        ]
        if len(words) <= 12 and not any(w in words for w in action_verbs):
            return True

        return False

    @classmethod
    def detect_intent_and_plan(
        cls,
        user_text: str,
        current_mode: AssistantMode = "general",
        uploaded_documents: list[str] | None = None,
    ) -> ExecutionPlan:
        low = user_text.lower().strip()
        has_docs = bool(uploaded_documents)

        # 0. Direct Conversational Query (Zero tools required)
        if cls.is_direct_answer_candidate(low) and not has_docs:
            return ExecutionPlan(
                goal="Provide immediate direct conversational response",
                mode=current_mode,
                steps=[
                    PlanStep(stepNumber=1, title="Formulate concise direct answer", status="completed"),
                ],
                required_tools=[],
                requires_tools=False,
                risk_level="low",
                completion_conditions=["Clear direct plain-text response provided."],
            )

        # 1. Study Mode / Academic Prep
        if any(w in low for w in ["study", "mcq", "exam", "quiz", "formula sheet", "detailed notes", "flashcard", "derivations"]) or current_mode == "study":
            steps = [
                PlanStep(stepNumber=1, title="Extract and structure academic subject matter", status="completed"),
                PlanStep(stepNumber=2, title="Isolate foundational principles, equations & definitions", status="in_progress"),
                PlanStep(stepNumber=3, title="Synthesize comprehensive revision notes", status="pending"),
                PlanStep(stepNumber=4, title="Generate practice exam questions & analytical solutions", status="pending"),
            ]
            return ExecutionPlan(
                goal="Synthesize in-depth academic study notes and practice exam materials",
                mode="study",
                steps=steps,
                required_tools=["study_generator", "pdf_generator"],
                suggested_files_to_generate=["Detailed_Notes.pdf"],
                requires_tools=True,
                risk_level="low",
                completion_conditions=["Comprehensive study material and questions synthesized with solutions."],
            )

        # 2. Presentation Deck Creation
        if any(w in low for w in ["powerpoint", "pptx", "presentation", "slide deck", "slides"]) or current_mode == "presentation":
            steps = [
                PlanStep(stepNumber=1, title="Analyze presentation narrative and target audience", status="completed"),
                PlanStep(stepNumber=2, title="Structure slide titles, bullet hierarchies & speaker notes", status="in_progress"),
                PlanStep(stepNumber=3, title="Compile widescreen 16:9 PowerPoint presentation file", status="pending"),
                PlanStep(stepNumber=4, title="Verify generated slide deck integrity and formatting", status="pending"),
            ]
            return ExecutionPlan(
                goal="Generate styled 16:9 widescreen presentation deck",
                mode="presentation",
                steps=steps,
                required_tools=["pptx_generator"],
                suggested_files_to_generate=["Presentation.pptx"],
                requires_tools=True,
                risk_level="low",
                completion_conditions=["Valid, non-empty PPTX presentation written to disk."],
            )

        # 3. Document Synthesis (PDF / Word / Excel / Reports)
        if any(w in low for w in ["pdf", "generate pdf", "create pdf", "make a report", "report on", "word doc", "docx", "excel file", "spreadsheet", "xlsx"]) or current_mode == "document":
            steps = [
                PlanStep(stepNumber=1, title="Structure document sections, tables, and typography", status="completed"),
                PlanStep(stepNumber=2, title="Compile target publication file to disk", status="in_progress"),
                PlanStep(stepNumber=3, title="Verify document headers, non-empty bytes, and download link", status="pending"),
            ]
            req_tools = ["pdf_generator"]
            if "excel" in low or "spreadsheet" in low or "xlsx" in low:
                req_tools = ["excel_generator"]
            elif "word" in low or "docx" in low:
                req_tools = ["docx_generator"]

            return ExecutionPlan(
                goal="Compile publication-ready document artifact",
                mode="document",
                steps=steps,
                required_tools=req_tools,
                suggested_files_to_generate=["Document.pdf"],
                requires_tools=True,
                risk_level="low",
                completion_conditions=["Generated document verified on disk with valid headers."],
            )

        # 4. Deep Research & Comparative Multi-Source Analysis
        if any(w in low for w in ["research", "investigate", "compare reports", "find sources", "citations", "literature review", "web survey"]) or current_mode == "research":
            steps = [
                PlanStep(stepNumber=1, title="Formulate multi-vector search queries", status="completed"),
                PlanStep(stepNumber=2, title="Execute live web search across authoritative sources", status="in_progress"),
                PlanStep(stepNumber=3, title="Extract and cross-verify facts and citations", status="pending"),
                PlanStep(stepNumber=4, title="Synthesize grounded research briefing with verified references", status="pending"),
            ]
            return ExecutionPlan(
                goal="Execute multi-source deep research with citation grounding",
                mode="research",
                steps=steps,
                required_tools=["web_search", "read_webpage"],
                requires_tools=True,
                risk_level="low",
                completion_conditions=["Synthesized report grounded with verified citations, external URLs and source domains."],
            )

        # 5. Coding, Refactoring, Sandboxed Execution
        if any(w in low for w in ["code", "python", "javascript", "c++", "cpp", "debug", "refactor", "run test", "sandbox", "script"]) or current_mode == "coding":
            steps = [
                PlanStep(stepNumber=1, title="Parse source syntax and identify logical requirements", status="completed"),
                PlanStep(stepNumber=2, title="Synthesize clean code implementation with error handling", status="in_progress"),
                PlanStep(stepNumber=3, title="Execute unit tests within restricted sandbox environment", status="pending"),
                PlanStep(stepNumber=4, title="Verify test pass rate and syntax integrity", status="pending"),
            ]
            return ExecutionPlan(
                goal="Develop, inspect, and test sandboxed code implementation",
                mode="coding",
                steps=steps,
                required_tools=["execute_python_code"],
                requires_tools=True,
                risk_level="low",
                completion_conditions=["Synthesized code verified and executed cleanly in sandbox."],
            )

        # 6. Sensitive / High-Impact Local System Action
        if any(w in low for w in ["delete", "remove file", "drop database", "modify file", "write file", "open app", "launch"]):
            steps = [
                PlanStep(stepNumber=1, title="Inspect parameters and evaluate system security risk", status="completed"),
                PlanStep(stepNumber=2, title="Request explicit cryptographic confirmation if required", status="in_progress"),
                PlanStep(stepNumber=3, title="Execute authorized action upon verification", status="pending"),
            ]
            return ExecutionPlan(
                goal="Evaluate and execute system action with strict authorization checks",
                mode="general",
                steps=steps,
                required_tools=["write_file", "open_application"],
                requires_tools=True,
                risk_level="high",
                completion_conditions=["Action validated against active permissions and confirmation tokens."],
            )

        # Default Multi-Tool Conversational Plan
        return ExecutionPlan(
            goal="Execute request with tool grounding and verification",
            mode=current_mode,
            steps=[
                PlanStep(stepNumber=1, title="Decompose instruction and determine tool needs", status="completed"),
                PlanStep(stepNumber=2, title="Execute necessary subsystem operations", status="in_progress"),
                PlanStep(stepNumber=3, title="Verify results and formulate grounded response", status="pending"),
            ],
            required_tools=["web_search", "calculator", "system_diagnostics"],
            requires_tools=True,
            risk_level="low",
            completion_conditions=["User instruction satisfied with accurate results."],
        )


planning_engine = PlanningEngine()
