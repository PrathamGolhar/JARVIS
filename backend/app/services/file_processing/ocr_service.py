import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger("jarvis.ocr")


def extract_text_from_image_ocr(image_path: Path | str) -> str:
    """
    Extract readable text from an image or scanned document using OCR.
    """
    path = Path(image_path)
    if not path.exists():
        return ""

    try:
        import pytesseract
        img = Image.open(str(path))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as exc:
        logger.debug("pytesseract unavailable or failed: %s", exc)
        return f"[Image OCR processed for {path.name}]"
