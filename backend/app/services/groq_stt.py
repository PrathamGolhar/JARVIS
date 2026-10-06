import io
import requests

from app.settings import settings

GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
WHISPER_MODELS = ["whisper-large-v3-turbo", "whisper-large-v3", "distil-whisper-large-v3-en"]


class GroqSttError(RuntimeError):
    pass


class GroqAuthError(GroqSttError):
    pass


class GroqRateLimitError(GroqSttError):
    pass


class GroqNetworkError(GroqSttError):
    pass


def transcribe(audio: bytes, filename: str, content_type: str) -> str:
    """
    Send user audio recording bytes to Groq Whisper and return transcribed text.
    Includes multi-model fallback, classified exceptions, and clean error messages.
    """
    if not settings.groq_api_key or not settings.groq_api_key.strip():
        raise GroqAuthError("Groq API key is not configured in backend .env.")

    last_error_msg = ""

    for model_name in WHISPER_MODELS:
        try:
            response = requests.post(
                GROQ_TRANSCRIBE_URL,
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                files={"file": (filename, io.BytesIO(audio), content_type)},
                data={"model": model_name, "response_format": "json"},
                timeout=18,
            )
        except requests.Timeout as exc:
            raise GroqNetworkError("Groq STT request timed out (18s).") from exc
        except requests.RequestException as exc:
            raise GroqNetworkError(f"Network error communicating with Groq STT: {exc}") from exc

        if response.status_code == 200:
            try:
                data = response.json()
                transcript = data.get("text", "").strip()
                return transcript
            except ValueError as exc:
                raise GroqSttError("Invalid JSON received from Groq STT.") from exc

        if response.status_code == 401:
            raise GroqAuthError("Groq API authentication failed. Verify GROQ_API_KEY.")

        if response.status_code == 429:
            raise GroqRateLimitError("Groq STT rate limit exceeded. Please wait a moment.")

        last_error_msg = f"Groq STT error ({response.status_code}): {response.text}"

    raise GroqSttError(last_error_msg or "All Groq Whisper STT models failed.")
