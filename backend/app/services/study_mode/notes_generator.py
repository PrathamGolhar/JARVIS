import json
import logging
import re
from typing import Any

from app.schemas import DefinitionItem, FlashcardItem, FormulaItem, MCQItem, StudyNotesResponse
from app.services.ai.factory import get_ai_provider

logger = logging.getLogger("jarvis.study_mode")


def generate_structured_study_notes(
    topic_or_text: str,
    subject: str = "General",
    include_formulas: bool = True,
    include_practice_questions: bool = True,
) -> StudyNotesResponse:
    """
    Generate comprehensive, structured academic study notes from input text or topic.
    Includes concepts, definitions, formulas, derivations, diagrams descriptions, and exam questions.
    """
    provider = get_ai_provider()

    system_prompt = (
        "You are JARVIS in dedicated STUDY MODE — an elite, patient, and razor-sharp academic tutor and professor.\n"
        "Your goal is to transform the provided topic or document into supreme, comprehensive study notes.\n"
        "Output MUST be valid JSON matching this schema:\n"
        "{\n"
        '  "title": "Title of the topic/document",\n'
        '  "subject": "Academic field / subject",\n'
        '  "summary": "Crisp 2-3 paragraph conceptual summary",\n'
        '  "keyConcepts": ["Concept 1", "Concept 2", ...],\n'
        '  "definitions": [\n'
        '    {"term": "Term Name", "definition": "Precise definition", "example": "Real-world example"}\n'
        "  ],\n"
        '  "formulas": [\n'
        '    {"name": "Law/Formula Name", "formula": "LaTeX or plain formula", "explanation": "Derivation/explanation", "variables": {"V": "Voltage (Volts)", "I": "Current (Amps)"}}\n'
        "  ],\n"
        '  "detailedNotesMarkdown": "# Comprehensive Notes\\n\\n### 1. Introduction\\n...",\n'
        '  "practiceQuestions": [\n'
        '    {"id": 1, "question": "Question text", "options": ["A", "B", "C", "D"], "correctOptionIndex": 0, "difficulty": "Medium", "hint": "Think about...", "solution": "Option A", "explanation": "Detailed explanation"}\n'
        "  ],\n"
        '  "flashcards": [\n'
        '    {"front": "Question/Prompt", "back": "Answer/Definition", "topic": "Subtopic"}\n'
        "  ]\n"
        "}"
    )

    user_prompt = f"Subject: {subject}\n\nMaterial / Topic to study:\n{topic_or_text[:12000]}"

    try:
        res = provider.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=4000,
        )

        content = res.content.strip()
        # Clean any markdown json wrapper
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        data = json.loads(content.strip())
        if not isinstance(data, dict):
            raise ValueError("The provider response was not a JSON object.")
        required_fields = {
            "title",
            "subject",
            "summary",
            "keyConcepts",
            "definitions",
            "detailedNotesMarkdown",
            "flashcards",
        }
        if include_formulas:
            required_fields.add("formulas")
        if include_practice_questions:
            required_fields.add("practiceQuestions")
        missing_fields = required_fields - data.keys()
        if missing_fields:
            raise ValueError(f"The provider response is missing fields: {', '.join(sorted(missing_fields))}.")
        for field_name in ("title", "subject", "summary", "detailedNotesMarkdown"):
            if not isinstance(data[field_name], str) or not data[field_name].strip():
                raise ValueError(f"The provider response has no usable {field_name}.")
        if not isinstance(data["keyConcepts"], list) or not data["keyConcepts"]:
            raise ValueError("The provider response did not include key concepts.")
        for field_name in ("definitions", "flashcards"):
            if not isinstance(data[field_name], list):
                raise ValueError(f"The provider response has an invalid {field_name} list.")
        if include_formulas and not isinstance(data["formulas"], list):
            raise ValueError("The provider response has an invalid formulas list.")
        if include_practice_questions and (
            not isinstance(data["practiceQuestions"], list) or not data["practiceQuestions"]
        ):
            raise ValueError("The provider response did not include practice questions.")

        definitions = [
            DefinitionItem(
                term=d["term"],
                definition=d["definition"],
                example=d.get("example", ""),
            )
            for d in data.get("definitions", [])
            if isinstance(d, dict) and isinstance(d.get("term"), str) and d["term"].strip()
            and isinstance(d.get("definition"), str) and d["definition"].strip()
        ]

        formulas = [
            FormulaItem(
                name=f["name"],
                formula=f["formula"],
                explanation=f.get("explanation", ""),
                variables=f.get("variables", {}),
            )
            for f in data.get("formulas", [])
            if isinstance(f, dict) and isinstance(f.get("name"), str) and f["name"].strip()
            and isinstance(f.get("formula"), str) and f["formula"].strip()
        ]

        practice_questions = [
            MCQItem(
                id=q.get("id", i + 1),
                question=q["question"],
                options=q["options"],
                correctOptionIndex=q["correctOptionIndex"],
                difficulty=q.get("difficulty", "Medium"),
                hint=q.get("hint", ""),
                solution=q.get("solution", ""),
                explanation=q.get("explanation", ""),
            )
            for i, q in enumerate(data.get("practiceQuestions", []))
            if isinstance(q, dict)
            and isinstance(q.get("question"), str)
            and q["question"].strip()
            and isinstance(q.get("options"), list)
            and len(q["options"]) >= 2
            and isinstance(q.get("correctOptionIndex"), int)
            and 0 <= q["correctOptionIndex"] < len(q["options"])
        ]

        flashcards = [
            FlashcardItem(
                front=fc["front"],
                back=fc["back"],
                topic=fc.get("topic", ""),
            )
            for fc in data.get("flashcards", [])
            if isinstance(fc, dict)
            and isinstance(fc.get("front"), str)
            and fc["front"].strip()
            and isinstance(fc.get("back"), str)
            and fc["back"].strip()
        ]
        if len(definitions) != len(data["definitions"]) or len(flashcards) != len(data["flashcards"]):
            raise ValueError("The provider response contains invalid definition or flashcard entries.")
        if include_practice_questions and len(practice_questions) != len(data["practiceQuestions"]):
            raise ValueError("The provider response contains invalid practice-question entries.")
        if include_formulas and len(formulas) != len(data["formulas"]):
            raise ValueError("The provider response contains invalid formula entries.")

        return StudyNotesResponse(
            title=data["title"],
            subject=data["subject"],
            summary=data["summary"],
            keyConcepts=data.get("keyConcepts", []),
            definitions=definitions,
            formulas=formulas,
            detailedNotesMarkdown=data["detailedNotesMarkdown"],
            practiceQuestions=practice_questions,
            flashcards=flashcards,
        )
    except Exception as exc:
        logger.warning("AI structured study generation failed: %s", exc)
        raise RuntimeError("Study notes generation failed; no fallback notes were generated.") from exc
