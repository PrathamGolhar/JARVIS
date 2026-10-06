from dataclasses import dataclass, field
import json
import logging
import re
from typing import Any

from app.schemas import AssistantMode, PlanStep
from app.services.ai.factory import get_ai_provider

logger = logging.getLogger("jarvis.planner")


@dataclass
class ExecutionPlan:
    goal: str
    mode: AssistantMode
    steps: list[PlanStep] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    suggested_files_to_generate: list[str] = field(default_factory=list)


class PlanningEngine:
    """
    Autonomous planning engine that classifies user intent, constructs discrete execution steps,
    and coordinates specialized sub-agents.
    """

    @staticmethod
    def detect_intent_and_plan(user_text: str, current_mode: AssistantMode = "general") -> ExecutionPlan:
        low = user_text.lower()

        # 1. Study Mode / PDF Notes / Exam Questions
        if any(w in low for w in ["study", "mcq", "exam", "quiz", "formula", "detailed notes", "flashcard", "derivations"]):
            steps = [
                PlanStep(stepNumber=1, title="Extract and understand academic material", status="completed"),
                PlanStep(stepNumber=2, title="Isolate key principles, formulas & definitions", status="in_progress"),
                PlanStep(stepNumber=3, title="Synthesize structured comprehensive notes", status="pending"),
                PlanStep(stepNumber=4, title="Generate practice questions & solution breakdown", status="pending"),
                PlanStep(stepNumber=5, title="Compile downloadable notes (PDF/DOCX)", status="pending"),
            ]
            return ExecutionPlan(
                goal="Generate in-depth academic study notes and practice exam questions",
                mode="study",
                steps=steps,
                required_tools=["study_generator", "pdf_generator"],
                suggested_files_to_generate=["Detailed_Notes.pdf"],
            )

        # 2. Presentation / PowerPoint Generation
        if any(w in low for w in ["powerpoint", "pptx", "presentation", "slides", "slide deck"]):
            steps = [
                PlanStep(stepNumber=1, title="Analyze presentation topic and audience", status="completed"),
                PlanStep(stepNumber=2, title="Create structured slide outline & agenda", status="in_progress"),
                PlanStep(stepNumber=3, title="Generate slide content & speaker notes", status="pending"),
                PlanStep(stepNumber=4, title="Compile styled 16:9 PowerPoint deck", status="pending"),
                PlanStep(stepNumber=5, title="Verify slide integrity & deliver file", status="pending"),
            ]
            return ExecutionPlan(
                goal="Create modern widescreen presentation deck",
                mode="presentation",
                steps=steps,
                required_tools=["pptx_generator"],
                suggested_files_to_generate=["Presentation.pptx"],
            )

        # 3. Document / Report Generation (PDF / DOCX)
        if any(w in low for w in ["generate pdf", "create pdf", "make a report", "word document", "docx", "excel file", "spreadsheet", "xlsx"]):
            steps = [
                PlanStep(stepNumber=1, title="Gather required information and data", status="completed"),
                PlanStep(stepNumber=2, title="Format structured headings, sections & tables", status="in_progress"),
                PlanStep(stepNumber=3, title="Render publication document", status="pending"),
                PlanStep(stepNumber=4, title="Verify generated document file", status="pending"),
            ]
            return ExecutionPlan(
                goal="Generate publication-grade document file",
                mode="document",
                steps=steps,
                required_tools=["pdf_generator", "docx_generator", "excel_generator"],
                suggested_files_to_generate=["Report.pdf"],
            )

        # 4. Deep Research
        if any(w in low for w in ["research", "investigate", "compare reports", "find sources", "citations"]):
            steps = [
                PlanStep(stepNumber=1, title="Execute multi-source web search", status="completed"),
                PlanStep(stepNumber=2, title="Extract authoritative content from top sources", status="in_progress"),
                PlanStep(stepNumber=3, title="Cross-verify facts and extract citations", status="pending"),
                PlanStep(stepNumber=4, title="Synthesize comprehensive research report", status="pending"),
            ]
            return ExecutionPlan(
                goal="Perform deep multi-source research with citations",
                mode="research",
                steps=steps,
                required_tools=["web_search", "read_webpage", "pdf_generator"],
            )

        # 5. Coding & Debugging
        if any(w in low for w in ["code", "python", "javascript", "c++", "cpp", "debug", "refactor", "run test", "script"]):
            steps = [
                PlanStep(stepNumber=1, title="Parse and analyze source code", status="completed"),
                PlanStep(stepNumber=2, title="Diagnose syntax, logic, and complexity", status="in_progress"),
                PlanStep(stepNumber=3, title="Refactor code and generate unit tests", status="pending"),
                PlanStep(stepNumber=4, title="Execute in sandbox environment", status="pending"),
            ]
            return ExecutionPlan(
                goal="Analyze, debug, and safely execute code",
                mode="coding",
                steps=steps,
                required_tools=["code_analyzer", "code_sandbox"],
            )

        # Default standard plan
        return ExecutionPlan(
            goal="Execute conversational command with tool grounding",
            mode=current_mode,
            steps=[
                PlanStep(stepNumber=1, title="Analyze user instruction", status="completed"),
                PlanStep(stepNumber=2, title="Execute required subsystem tools", status="in_progress"),
                PlanStep(stepNumber=3, title="Synthesize grounded response", status="pending"),
            ],
            required_tools=[],
        )


planning_engine = PlanningEngine()
