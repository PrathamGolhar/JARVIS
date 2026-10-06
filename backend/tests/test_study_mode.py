from app.services.study_mode.exam_prep import generate_exam_mcqs
from app.services.study_mode.notes_generator import generate_structured_study_notes


def test_generate_structured_study_notes() -> None:
    res = generate_structured_study_notes(
        topic_or_text="Ohm's Law states that the current through a conductor between two points is directly proportional to the voltage across the two points. V = I * R.",
        subject="Physics",
    )
    assert res.title
    assert "Physics" in res.subject
    assert len(res.key_concepts) > 0
    assert len(res.definitions) > 0
    assert len(res.detailed_notes_markdown) > 50


def test_generate_exam_mcqs() -> None:
    mcqs = generate_exam_mcqs(
        topic_or_text="Newton's Second Law states that force equals mass times acceleration (F = m * a).",
        count=3,
        difficulty="Medium",
    )
    assert len(mcqs) >= 1
    assert mcqs[0].question
    assert len(mcqs[0].options) >= 2
    assert mcqs[0].difficulty == "Medium"
