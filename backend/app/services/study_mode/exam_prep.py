import json
import logging
from typing import Literal

from app.schemas import MCQItem
from app.services.ai.factory import get_ai_provider

logger = logging.getLogger("jarvis.exam_prep")


def generate_exam_mcqs(
    topic_or_text: str,
    count: int = 10,
    difficulty: Literal["Easy", "Medium", "Hard", "Exam Level"] = "Medium",
) -> list[MCQItem]:
    """
    Generate tailored multiple-choice practice questions with hints, solutions, and explanations.
    """
    provider = get_ai_provider()

    system_prompt = (
        f"You are JARVIS Exam Preparation Core. Generate exactly {count} rigorous multiple choice questions "
        f"at difficulty level '{difficulty}'.\n"
        "Return ONLY a JSON array of objects with schema:\n"
        "[\n"
        "  {\n"
        '    "id": 1,\n'
        '    "question": "Question text...",\n'
        '    "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        '    "correctOptionIndex": 0,\n'
        f'    "difficulty": "{difficulty}",\n'
        '    "hint": "Subtle clue without giving away the answer",\n'
        '    "solution": "Correct option text",\n'
        '    "explanation": "Clear step-by-step rationale for why this is correct and others are wrong"\n'
        "  }\n"
        "]"
    )

    try:
        res = provider.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Material:\n{topic_or_text[:10000]}"},
            ],
            temperature=0.3,
            max_tokens=3000,
        )

        content = res.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        items = json.loads(content.strip())
        results = []
        for i, item in enumerate(items):
            results.append(MCQItem(
                id=item.get("id", i + 1),
                question=item.get("question", f"Question {i+1}"),
                options=item.get("options", ["Option A", "Option B", "Option C", "Option D"]),
                correctOptionIndex=int(item.get("correctOptionIndex", 0)),
                difficulty=item.get("difficulty", difficulty),
                hint=item.get("hint", ""),
                solution=item.get("solution", ""),
                explanation=item.get("explanation", ""),
            ))
        return results
    except Exception as exc:
        logger.warning("MCQ generation fallback: %s", exc)
        return [
            MCQItem(
                id=1,
                question=f"Regarding {topic_or_text[:50]}, which statement represents best practice?",
                options=[
                    "Implement verified principles with systematic error checks",
                    "Execute operations blindly without testing",
                    "Ignore theoretical boundaries",
                    "Disregard standard equations",
                ],
                correctOptionIndex=0,
                difficulty=difficulty,
                hint="Recall the core safety and engineering guidelines.",
                solution="Implement verified principles with systematic error checks",
                explanation="Systematic testing and boundary verification ensure rigorous execution.",
            )
        ]
