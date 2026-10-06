from pathlib import Path
from app.schemas import SlideContent
from app.services.document_generation.docx_generator import generate_docx_document
from app.services.document_generation.excel_generator import generate_excel_spreadsheet
from app.services.document_generation.pdf_generator import generate_pdf_document
from app.services.document_generation.pptx_generator import generate_pptx_presentation


def test_generate_pdf_document_creates_valid_file(tmp_path) -> None:
    pdf_path = generate_pdf_document(
        title="Test PDF Document",
        content_markdown="# Heading 1\n\nThis is a test paragraph.\n\n- Bullet item 1\n- Bullet item 2\n\n```python\nprint('hello')\n```",
        subtitle="Verification Subtitle",
    )
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 500
    assert pdf_path.suffix == ".pdf"


def test_generate_pptx_presentation_creates_valid_deck() -> None:
    slides = [
        SlideContent(title="Slide 1", subtitle="Sub 1", bullets=["Point A", "Point B"], speakerNotes="Note 1"),
        SlideContent(title="Slide 2", subtitle="Sub 2", bullets=["Point C", "Point D"], speakerNotes="Note 2"),
    ]
    pptx_path = generate_pptx_presentation(topic="AI Architecture", slides=slides, theme_color="cyan")
    assert pptx_path.exists()
    assert pptx_path.stat().st_size > 1000
    assert pptx_path.suffix == ".pptx"


def test_generate_docx_document_creates_valid_file() -> None:
    docx_path = generate_docx_document(
        title="Test Word Document",
        content_markdown="# Chapter 1\n\nContent here.\n\n- List item\n\n```python\nx = 42\n```",
        subtitle="Report Subtitle",
    )
    assert docx_path.exists()
    assert docx_path.stat().st_size > 500
    assert docx_path.suffix == ".docx"


def test_generate_excel_spreadsheet_creates_valid_file() -> None:
    headers = ["Item", "Quantity", "Price", "Total"]
    rows = [
        ["Microcontroller", 5, 25.0, 125.0],
        ["Servo Motor", 10, 12.5, 125.0],
        ["LiPo Battery", 2, 45.0, 90.0],
    ]
    xlsx_path = generate_excel_spreadsheet(filename="Robotics_BOM.xlsx", headers=headers, rows=rows)
    assert xlsx_path.exists()
    assert xlsx_path.stat().st_size > 1000
    assert xlsx_path.suffix == ".xlsx"
