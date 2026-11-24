import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger("jarvis.ocr")


def extract_text_from_image_ocr(image_path: Path | str) -> str:
    """
    Extract readable text from an image or scanned document using OCR.
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"OCR input file was not found: {path}")

    try:
        import pytesseract
    except ImportError as exc:
        logger.warning("OCR engine is unavailable: %s", exc)
        raise RuntimeError("OCR is unavailable because pytesseract is not installed.") from exc

    try:
        with Image.open(str(path)) as image:
            return pytesseract.image_to_string(image).strip()
    except Exception as exc:
        logger.warning("OCR processing failed for %s: %s", path.name, exc)
        raise RuntimeError(f"OCR processing failed for '{path.name}'.") from exc
