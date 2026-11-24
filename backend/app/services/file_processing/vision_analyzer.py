import base64
import logging
from pathlib import Path

import requests

from app.endpoints import GEMINI_API_BASE_URL
from app.settings import settings

logger = logging.getLogger("jarvis.vision")


def analyze_image_or_diagram(
    image_path: Path | str,
    prompt: str = "Explain this diagram, circuit, or image step-by-step and solve any embedded question.",
) -> str:
    """Analyze an image with Gemini Vision; fail explicitly when analysis is unavailable."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image file was not found: {path}")
    if not settings.google_api_key:
        raise RuntimeError("Visual analysis is unavailable because no vision provider is configured.")

    try:
        image_bytes = path.read_bytes()
        encoded_b64 = base64.b64encode(image_bytes).decode("utf-8")
        suffix = path.suffix.lower().lstrip(".")
        mime_type = f"image/{'jpeg' if suffix in ('jpg', 'jpeg') else suffix}"
        url = f"{GEMINI_API_BASE_URL}/models/{settings.gemini_model}:generateContent?key={settings.google_api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded_b64,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            },
        }

        response = requests.post(url, json=payload, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"Vision provider returned HTTP {response.status_code}.")

        candidates = response.json().get("candidates", [])
        if not candidates:
            raise RuntimeError("Vision provider returned no analysis.")
        parts = candidates[0].get("content", {}).get("parts", [])
        analysis = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part.get("text"), str)
        ).strip()
        if not analysis:
            raise RuntimeError("Vision provider returned empty analysis.")
        return analysis
    except Exception as exc:
        logger.warning("Image analysis failed for %s: %s", path.name, exc)
        raise RuntimeError(f"Image analysis failed for '{path.name}'.") from exc
