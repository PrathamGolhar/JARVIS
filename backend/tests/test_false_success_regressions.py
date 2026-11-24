import io
import json
import sys
from importlib import import_module
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.schemas import ResearchResponse
from app.main import app
from app.services.agents.document_agent import document_agent
from app.services.agents.verifier import output_verifier
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.local_provider import LocalProvider
from app.services.coding.assistant import analyze_code_task
from app.services.file_processing.multi_doc import MultiDocumentReasoner
from app.services.file_processing.extractor import extract_file_text_and_meta
from app.services.file_processing.ocr_service import extract_text_from_image_ocr
from app.services.file_processing.vision_analyzer import analyze_image_or_diagram
from app.services.research.researcher import perform_deep_research
from app.services.study_mode.exam_prep import generate_exam_mcqs
from app.services.study_mode.notes_generator import generate_structured_study_notes
from app.services.tools.registry import _dispatch_tool, execute_tool_call
from app.settings import settings

document_agent_module = import_module("app.services.agents.document_agent")
client = TestClient(app)


class StubProvider:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self.content = content
        self.error = error

    def chat(self, **kwargs):
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.content or "")


def _search_results(*args, **kwargs):
    return {
        "ok": True,
        "results": [
            {
                "title": "Example source",
                "url": "https://example.com/research",
                "snippet": "An unverified search-result snippet.",
            }
        ],
    }


def test_presentation_generation_failure_does_not_create_generic_slides(monkeypatch) -> None:
    monkeypatch.setattr(document_agent_module, "get_ai_provider", lambda: StubProvider(error=RuntimeError("provider unavailable")))
    generator = lambda **kwargs: pytest.fail("The PPTX generator must not run after AI failure.")
    monkeypatch.setattr(document_agent_module, "generate_pptx_presentation", generator)

    with pytest.raises(RuntimeError, match="no presentation was created"):
        document_agent.create_presentation_from_prompt("Requested topic", num_slides=2)


def test_presentation_rejects_incomplete_ai_slides(monkeypatch) -> None:
    monkeypatch.setattr(
        document_agent_module,
        "get_ai_provider",
        lambda: StubProvider(content=json.dumps({"slides": [{"title": "Only one"}]})),
    )
    generator = lambda **kwargs: pytest.fail("The PPTX generator must not receive incomplete slides.")
    monkeypatch.setattr(document_agent_module, "generate_pptx_presentation", generator)

    with pytest.raises(RuntimeError, match="no presentation was created"):
        document_agent.create_presentation_from_prompt("Requested topic", num_slides=2)


def test_presentation_generation_still_succeeds_with_complete_ai_slides(tmp_path, monkeypatch) -> None:
    slides = [
        {"title": "Introduction", "bullets": ["Purpose"], "speakerNotes": "Introduce the topic."},
        {"title": "Conclusion", "bullets": ["Summary"], "speakerNotes": "Close the presentation."},
    ]
    monkeypatch.setattr(
        document_agent_module,
        "get_ai_provider",
        lambda: StubProvider(content=json.dumps({"slides": slides})),
    )

    def generate_presentation(**kwargs):
        assert len(kwargs["slides"]) == 2
        path = tmp_path / "presentation.pptx"
        path.write_bytes(b"PK\x03\x04" + b"x" * 100)
        return path

    monkeypatch.setattr(document_agent_module, "generate_pptx_presentation", generate_presentation)

    result = document_agent.create_presentation_from_prompt("Requested topic", num_slides=2)

    assert result["slides_count"] == 2
    assert result["file"]["sizeBytes"] > 0


def test_presentation_api_returns_error_when_ai_generation_fails(monkeypatch) -> None:
    def fail_generation(**kwargs):
        raise RuntimeError("AI presentation generation failed.")

    monkeypatch.setattr(document_agent_module.document_agent, "create_presentation_from_prompt", fail_generation)

    response = client.post("/api/generate/pptx", json={"topic": "Requested topic", "slides": []})

    assert response.status_code == 500
    assert "PowerPoint generation failed" in response.json()["detail"]


def test_multi_document_failure_returns_no_fabricated_findings(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.file_processing.multi_doc.get_ai_provider",
        lambda: StubProvider(error=RuntimeError("provider unavailable")),
    )

    result = MultiDocumentReasoner.compare_documents(
        [
            {"filename": "a.txt", "content": "First document content."},
            {"filename": "b.txt", "content": "Second document content."},
        ]
    )

    assert result.status == "failure"
    assert result.documents_analyzed == []
    assert result.commonalities == []
    assert result.differences == []
    assert result.comparison_table == []
    assert result.synthesis_markdown == ""
    assert result.confidence is None


def test_multi_document_comparison_requires_two_readable_documents() -> None:
    result = MultiDocumentReasoner.compare_documents(
        [{"filename": "empty.txt", "content": ""}]
    )

    assert result.status == "failure"
    assert result.documents_analyzed == []
    assert result.error


def test_ocr_unavailable_does_not_return_placeholder_text(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "scan.png"
    image_path.write_bytes(b"image")
    monkeypatch.setitem(sys.modules, "pytesseract", None)

    with pytest.raises(RuntimeError, match="OCR is unavailable"):
        extract_text_from_image_ocr(image_path)


def test_ocr_success_still_returns_extracted_text(tmp_path, monkeypatch) -> None:
    from PIL import Image

    image_path = tmp_path / "scan.png"
    Image.new("RGB", (2, 2), color="white").save(image_path)
    monkeypatch.setitem(sys.modules, "pytesseract", SimpleNamespace(image_to_string=lambda image: "Recognized text"))

    assert extract_text_from_image_ocr(image_path) == "Recognized text"


def test_vision_without_provider_does_not_claim_image_understanding(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "diagram.png"
    image_path.write_bytes(b"image")
    monkeypatch.setattr(settings, "google_api_key", "")

    with pytest.raises(RuntimeError, match="Visual analysis is unavailable"):
        analyze_image_or_diagram(image_path)


def test_vision_empty_provider_response_is_not_image_analysis(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "diagram.png"
    image_path.write_bytes(b"image")
    monkeypatch.setattr(settings, "google_api_key", "test-key")
    response = SimpleNamespace(status_code=200, json=lambda: {"candidates": []})
    monkeypatch.setattr("app.services.file_processing.vision_analyzer.requests.post", lambda *a, **k: response)

    with pytest.raises(RuntimeError, match="Image analysis failed"):
        analyze_image_or_diagram(image_path)


def test_vision_success_returns_provider_analysis(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "diagram.png"
    image_path.write_bytes(b"image")
    monkeypatch.setattr(settings, "google_api_key", "test-key")
    response = SimpleNamespace(
        status_code=200,
        json=lambda: {"candidates": [{"content": {"parts": [{"text": "The diagram shows a circuit."}]}}]},
    )
    monkeypatch.setattr("app.services.file_processing.vision_analyzer.requests.post", lambda *a, **k: response)

    assert analyze_image_or_diagram(image_path) == "The diagram shows a circuit."


def test_image_upload_does_not_claim_ocr_or_text_indexing(monkeypatch, tmp_path) -> None:
    files_api = import_module("app.api.files")
    monkeypatch.setattr(files_api.settings, "uploads_dir", tmp_path)
    monkeypatch.setattr(files_api.settings, "permission_mode", "assisted")
    monkeypatch.setattr(
        files_api,
        "extract_file_text_and_meta",
        lambda path: {"text": "", "total_units": 1, "topics": ["Image attachment"]},
    )
    monkeypatch.setattr(files_api.rag_store, "chunk_and_index", lambda **kwargs: 0)

    response = client.post(
        "/api/files/upload",
        files={"file": ("diagram.png", io.BytesIO(b"image-bytes"), "image/png")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["ok"] is True
    assert "uploaded" in result["message"].lower()
    assert "ocr" in result["message"].lower()
    assert "indexed" not in result["message"].lower()


def test_scanned_pdf_without_text_does_not_index_page_markers(tmp_path) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with pdf_path.open("wb") as file:
        writer.write(file)

    extracted = extract_file_text_and_meta(pdf_path)

    assert extracted["total_units"] == 1
    assert extracted["text"] == ""


def test_research_synthesis_failure_is_partial_and_sources_are_not_verified(monkeypatch) -> None:
    monkeypatch.setattr("app.services.research.researcher.live_web_search", _search_results)
    monkeypatch.setattr("app.services.research.researcher.extract_webpage_text", lambda *a, **k: "")
    monkeypatch.setattr(
        "app.services.research.researcher.get_ai_provider",
        lambda: StubProvider(error=RuntimeError("provider unavailable")),
    )
    make_pdf = lambda **kwargs: pytest.fail("A failed synthesis must not generate a research PDF.")
    monkeypatch.setattr("app.services.research.researcher.generate_pdf_document", make_pdf)

    result = perform_deep_research("test query", depth="quick", generate_doc="pdf")

    assert result.status == "partial_success"
    assert result.synthesis_status == "failure"
    assert result.source_status == "search_results"
    assert result.document_status == "not_generated"
    assert result.generated_file_url is None
    assert "AI synthesis failed" in result.summary
    assert "not verified findings" in result.findings_markdown
    assert "verified sources" not in result.findings_markdown.lower()


def test_research_without_citations_does_not_attempt_synthesis(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.research.researcher.live_web_search",
        lambda *args, **kwargs: {"ok": False, "results": []},
    )
    monkeypatch.setattr(
        "app.services.research.researcher.get_ai_provider",
        lambda: pytest.fail("Synthesis must not run without source citations."),
    )

    result = perform_deep_research("test query", depth="quick")

    assert result.status == "failure"
    assert result.synthesis_status == "not_attempted"
    assert result.source_status == "none"
    assert result.citations == []
    assert "synthesis was not attempted" in result.summary


def test_research_succeeds_with_valid_ai_synthesis_and_search_citations(monkeypatch) -> None:
    synthesis = {
        "topic": "Test topic",
        "summary": "A source-linked summary.",
        "keyTakeaways": ["A source-linked finding."],
        "findingsMarkdown": "# Findings\n\nA finding linked to the supplied source.",
    }
    monkeypatch.setattr("app.services.research.researcher.live_web_search", _search_results)
    monkeypatch.setattr("app.services.research.researcher.extract_webpage_text", lambda *a, **k: "")
    monkeypatch.setattr(
        "app.services.research.researcher.get_ai_provider",
        lambda: StubProvider(content=json.dumps(synthesis)),
    )

    result = perform_deep_research("test query", depth="quick")

    assert result.status == "success"
    assert result.synthesis_status == "success"
    assert result.source_status == "search_results"
    assert len(result.citations) == 1
    assert result.generated_file_url is None


def test_research_api_exposes_partial_synthesis_status(monkeypatch) -> None:
    partial_result = ResearchResponse(
        topic="test",
        summary="AI synthesis failed.",
        findingsMarkdown="# Search results",
        citations=[],
        status="partial_success",
        synthesisStatus="failure",
        sourceStatus="search_results",
        diagnostic="AI synthesis failed.",
    )
    monkeypatch.setattr("app.api.research.perform_deep_research", lambda **kwargs: partial_result)

    response = client.post(
        "/api/research/deep",
        json={"query": "test", "depth": "quick", "generate_document": "none"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "partial_success"
    assert response.json()["synthesisStatus"] == "failure"
    assert response.json()["diagnostic"] == "AI synthesis failed."


def test_research_rejects_unsupported_document_format_as_partial(monkeypatch) -> None:
    synthesis = {
        "topic": "Test topic",
        "summary": "A sourced summary.",
        "keyTakeaways": ["A sourced finding."],
        "findingsMarkdown": "# Findings\n\nA sourced finding.",
    }
    monkeypatch.setattr("app.services.research.researcher.live_web_search", _search_results)
    monkeypatch.setattr("app.services.research.researcher.extract_webpage_text", lambda *a, **k: "")
    monkeypatch.setattr(
        "app.services.research.researcher.get_ai_provider",
        lambda: StubProvider(content=json.dumps(synthesis)),
    )

    result = perform_deep_research("test query", depth="quick", generate_doc="docx")

    assert result.synthesis_status == "success"
    assert result.status == "partial_success"
    assert result.document_status == "unsupported"
    assert result.generated_file_url is None
    assert result.diagnostic == "Requested document format is not supported."


def test_partial_research_tool_result_is_not_reported_as_success(monkeypatch) -> None:
    partial_result = ResearchResponse(
        topic="test",
        summary="Synthesis failed.",
        findingsMarkdown="# Search results",
        citations=[],
        status="partial_success",
        synthesisStatus="failure",
        sourceStatus="search_results",
        diagnostic="AI synthesis failed.",
    )
    monkeypatch.setattr(
        "app.services.tools.registry.perform_deep_research",
        lambda **kwargs: partial_result,
    )

    result = _dispatch_tool("deep_web_research", {"query": "test"})

    assert result["ok"] is False
    assert result["status"] == "partial_success"
    assert "verified sources" not in result["message"].lower()


def test_code_analysis_failure_does_not_return_fake_test_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.coding.assistant.get_ai_provider",
        lambda: StubProvider(error=RuntimeError("provider unavailable")),
    )

    with pytest.raises(RuntimeError, match="no analysis or test result"):
        analyze_code_task("print('hello')", task="generate_tests")


def test_study_generators_do_not_return_fallback_content(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.study_mode.notes_generator.get_ai_provider",
        lambda: StubProvider(error=RuntimeError("provider unavailable")),
    )
    monkeypatch.setattr(
        "app.services.study_mode.exam_prep.get_ai_provider",
        lambda: StubProvider(error=RuntimeError("provider unavailable")),
    )

    with pytest.raises(RuntimeError, match="no fallback notes"):
        generate_structured_study_notes("A topic")
    with pytest.raises(RuntimeError, match="no fallback questions"):
        generate_exam_mcqs("A topic", count=2)


def test_local_provider_discloses_limits_and_tool_failures() -> None:
    provider = LocalProvider()
    general = provider.chat([{"role": "user", "content": "Explain quantum mechanics."}])
    assert "no local general-purpose language model is active" in general.content

    failed_tool = provider.chat(
        [
            {"role": "user", "content": "Calculate 2 / 0"},
            {
                "role": "tool",
                "name": "calculator",
                "content": '{"ok": false, "error": "division by zero", "traceId": "trace-123"}',
            },
        ]
    )
    assert "failed" in failed_tool.content.lower()
    assert "successfully" not in failed_tool.content.lower()
    assert "trace-123" in failed_tool.content


def test_local_provider_does_not_label_search_results_verified() -> None:
    response = LocalProvider().chat(
        [
            {"role": "user", "content": "Search for a source"},
            {
                "role": "tool",
                "name": "web_search",
                "content": json.dumps({"ok": True, "results": [{"title": "Example", "url": "https://example.com"}]}),
            },
        ]
    )

    assert "not independently verified" in response.content
    assert "verified results" not in response.content.lower()


def test_tool_results_require_explicit_success(monkeypatch) -> None:
    assert output_verifier.verify_tool_result("example", {"result": "data"}) is False
    monkeypatch.setattr(
        "app.services.tools.registry._dispatch_tool",
        lambda *args, **kwargs: {"result": "data"},
    )

    result = execute_tool_call(
        "calculator",
        {"expression": "2 + 2"},
        session_id="false-success-regression",
    )

    assert result["ok"] is False
    assert "explicit success status" in result["error"]

    monkeypatch.setattr(
        "app.services.tools.registry._dispatch_tool",
        lambda *args, **kwargs: {"ok": False, "stderr": "Import of prohibited module 'os'."},
    )
    failed_result = execute_tool_call(
        "execute_python_code",
        {"code": "import os"},
        session_id="false-success-explicit-failure",
    )

    assert failed_result["ok"] is False
    assert "prohibited module" in failed_result["error"]


def test_gemini_empty_response_triggers_provider_failure(monkeypatch) -> None:
    provider = GeminiProvider(api_key="test-key")
    response = SimpleNamespace(status_code=200, json=lambda: {"candidates": []})
    monkeypatch.setattr("app.services.ai.gemini_provider.requests.post", lambda *a, **k: response)

    with pytest.raises(RuntimeError, match="no response candidates"):
        provider.chat([{"role": "user", "content": "Generate a response."}])
