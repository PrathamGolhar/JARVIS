import csv
import json
from pathlib import Path
from typing import Any
import docx
from openpyxl import load_workbook
from pptx import Presentation
from pypdf import PdfReader


def extract_file_text_and_meta(file_path: Path | str) -> dict[str, Any]:
    """
    Universally extract text content, metadata, and structural breakdown from any supported file.
    Supports PDF, DOCX, PPTX, XLSX, CSV, JSON, Markdown, TXT, and Code files.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File '{path}' does not exist.")

    ext = path.suffix.lower()
    text = ""
    pages_or_units = 1
    topics = []

    try:
        if ext == ".pdf":
            reader = PdfReader(str(path))
            pages_or_units = len(reader.pages)
            extracted_pages = []
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                extracted_pages.append(f"--- Page {idx + 1} ---\n{page_text}")
            text = "\n\n".join(extracted_pages)
            topics = [f"PDF Document with {pages_or_units} pages"]

        elif ext == ".docx":
            doc = docx.Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            pages_or_units = len(paragraphs)
            text = "\n".join(paragraphs)
            topics = [h.text for h in doc.paragraphs if h.style.name.startswith("Heading")]

        elif ext == ".pptx":
            prs = Presentation(str(path))
            pages_or_units = len(prs.slides)
            slide_texts = []
            for idx, slide in enumerate(prs.slides):
                stext = []
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        stext.append(shape.text_frame.text)
                slide_texts.append(f"--- Slide {idx + 1} ---\n" + "\n".join(stext))
            text = "\n\n".join(slide_texts)
            topics = [f"Presentation with {pages_or_units} slides"]

        elif ext in (".xlsx", ".xlsm"):
            wb = load_workbook(str(path), data_only=True)
            pages_or_units = len(wb.sheetnames)
            sheet_summaries = []
            for name in wb.sheetnames:
                ws = wb[name]
                rows_data = []
                for row in ws.iter_rows(max_row=20, values_only=True):
                    if any(row):
                        rows_data.append(" | ".join(str(c or "") for c in row))
                sheet_summaries.append(f"Sheet: {name}\n" + "\n".join(rows_data))
            text = "\n\n".join(sheet_summaries)
            topics = wb.sheetnames

        elif ext == ".csv":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = [", ".join(r) for r in list(reader)[:50]]
                pages_or_units = len(rows)
                text = "\n".join(rows)
                topics = ["CSV Dataset"]

        elif ext == ".json":
            raw = path.read_text(encoding="utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
                text = json.dumps(parsed, indent=2)
                topics = list(parsed.keys()) if isinstance(parsed, dict) else ["JSON Array"]
            except Exception:
                text = raw

        else:
            # Plain text, code, markdown, logs
            text = path.read_text(encoding="utf-8", errors="replace")
            pages_or_units = len(text.splitlines())
            topics = [f"{ext.lstrip('.').upper()} source file ({pages_or_units} lines)"]

    except Exception as exc:
        text = f"Error extracting content: {exc}"

    return {
        "text": text,
        "total_units": pages_or_units,
        "topics": topics,
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }
