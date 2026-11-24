import json
from types import SimpleNamespace

from app.services.study_mode.exam_prep import generate_exam_mcqs
from app.services.study_mode.notes_generator import generate_structured_study_notes


class StubProvider:
    def __init__(self, content: str) -> None:
        self.content = content

    def chat(self, **kwargs):
        return SimpleNamespace(content=self.content)


def test_generate_structured_study_notes(monkeypatch) -> None:
    response = {
        "title": "Ohm's Law",
        "subject": "Physics",
        "summary": "Voltage, current, and resistance are related by V = I * R.",
        "keyConcepts": ["Voltage", "Current", "Resistance"],
        "definitions": [{"term": "Current", "definition": "Charge flow per unit time."}],
        "formulas": [{"name": "Ohm's Law", "formula": "V = I * R"}],
        "detailedNotesMarkdown": (
            "# Ohm's Law\n\nV = I * R describes the relationship between voltage, "
            "current, and resistance in a conductor."
        ),
        "practiceQuestions": [
            {
                "id": 1,
                "question": "Which equation represents Ohm's Law?",
                "options": ["V = I * R", "V = I + R"],
                "correctOptionIndex": 0,
            }
        ],
        "flashcards": [{"front": "Ohm's Law", "back": "V = I * R"}],
    }
    monkeypatch.setattr(
        "app.services.study_mode.notes_generator.get_ai_provider",
        lambda: StubProvider(json.dumps(response)),
    )

    res = generate_structured_study_notes(
        topic_or_text="Ohm's Law states that the current through a conductor between two points is directly proportional to the voltage across the two points. V = I * R.",
        subject="Physics",
    )
    assert res.title
    assert "Physics" in res.subject
    assert len(res.key_concepts) > 0
    assert len(res.definitions) > 0
    assert len(res.detailed_notes_markdown) > 50


def test_generate_exam_mcqs(monkeypatch) -> None:
    response = [
        {
            "id": index,
            "question": f"Question {index}?",
            "options": ["Correct", "Incorrect"],
            "correctOptionIndex": 0,
            "difficulty": "Medium",
        }
        for index in range(1, 4)
    ]
    monkeypatch.setattr(
        "app.services.study_mode.exam_prep.get_ai_provider",
        lambda: StubProvider(json.dumps(response)),
    )

    mcqs = generate_exam_mcqs(
        topic_or_text="Newton's Second Law states that force equals mass times acceleration (F = m * a).",
        count=3,
        difficulty="Medium",
    )
    assert len(mcqs) == 3
    assert mcqs[0].question
    assert len(mcqs[0].options) >= 2
    assert mcqs[0].difficulty == "Medium"
