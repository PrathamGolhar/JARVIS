from app.services.agents.planner import planning_engine
from app.services.agents.verifier import output_verifier
from app.services.document_generation.pdf_generator import generate_pdf_document


def test_planner_detects_study_intent() -> None:
    plan = planning_engine.detect_intent_and_plan("JARVIS, analyze this PDF and create 30 practice exam MCQs with formulas")
    assert plan.mode == "study"
    assert len(plan.steps) > 0


def test_planner_detects_presentation_intent() -> None:
    plan = planning_engine.detect_intent_and_plan("Create a 10 slide PowerPoint presentation on Quantum Computing")
    assert plan.mode == "presentation"
    assert "pptx_generator" in plan.required_tools


def test_output_verifier_validates_existing_file() -> None:
    pdf = generate_pdf_document(title="Verification Check", content_markdown="# Test Report\n\nVerified content.")
    result = output_verifier.verify_generated_file(pdf)
    assert result["verified"] is True
    assert result["size_bytes"] > 0


def test_output_verifier_rejects_missing_file() -> None:
    result = output_verifier.verify_generated_file("non_existent_file_12345.pdf")
    assert result["verified"] is False
