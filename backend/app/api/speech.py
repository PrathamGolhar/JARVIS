import asyncio

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from app.schemas import TranscriptResponse, TtsRequest, VoicesResponse
from app.services.edge_tts_service import EdgeTtsError, available_voices, generate_speech
from app.services.groq_stt import (
    GroqAuthError,
    GroqNetworkError,
    GroqRateLimitError,
    GroqSttError,
    transcribe,
)

router = APIRouter(prefix="/api", tags=["speech"])

ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mpeg",
    "audio/mp3",
    "video/webm",
    "application/octet-stream",
}
MAX_AUDIO_BYTES = 10 * 1024 * 1024


def normalize_content_type(raw_type: str | None, filename: str | None) -> str:
    """
    Sanitize MIME types by stripping codec parameters (e.g., 'audio/webm;codecs=opus' -> 'audio/webm')
    and falling back to file extension mapping if needed.
    """
    if raw_type:
        clean = raw_type.split(";")[0].strip().lower()
        if clean in ALLOWED_AUDIO_TYPES:
            return clean

    if filename and "." in filename:
        ext = filename.lower().rsplit(".", 1)[-1]
        ext_map = {
            "webm": "audio/webm",
            "ogg": "audio/ogg",
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "mp4": "audio/mp4",
            "m4a": "audio/mp4",
        }
        if ext in ext_map:
            return ext_map[ext]

    return "audio/webm"


# ==============================================================================
# PHASE 0: SPEECH SUBSYSTEM HEALTH CHECK
# ==============================================================================
@router.get("/speech/health")
async def speech_health():
    """
    Check availability of TTS and STT providers.
    """
    voices_list = available_voices()
    from app.settings import settings

    stt_configured = bool(settings.groq_api_key and settings.groq_api_key.strip())
    return {
        "status": "ready" if stt_configured else "degraded",
        "sttProvider": "groq-whisper" if stt_configured else "none",
        "sttAvailable": stt_configured,
        "ttsAvailable": len(voices_list) > 0,
        "supportedFormats": list(ALLOWED_AUDIO_TYPES),
    }


# ==============================================================================
# PHASE 3: THE MOUTH (Voice Catalog Endpoint)
# ==============================================================================
@router.get("/voices", response_model=VoicesResponse)
async def voices() -> VoicesResponse:
    """
    Return available Edge-TTS neural voices.
    """
    return VoicesResponse(voices=available_voices())


# ==============================================================================
# PHASE 3: THE MOUTH (Text-to-Speech Streaming Endpoint)
# ==============================================================================
@router.post("/tts", response_class=Response)
async def tts(request: TtsRequest) -> Response:
    """
    Convert reply text into MP3 audio stream.
    1. Validate request.text is non-blank (raise 422 if blank).
    2. Await generate_speech(text, request.voice_id).
    3. Return Response(content=audio, media_type="audio/mpeg").
    """
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Text cannot be blank.",
        )

    try:
        audio = await generate_speech(request.text, request.voice_id)
        return Response(content=audio, media_type="audio/mpeg")
    except EdgeTtsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate speech audio.",
        ) from exc


# ==============================================================================
# PHASE 1: THE EARS (Audio Transcription Upload Endpoint)
# ==============================================================================
@router.post("/transcribe", response_model=TranscriptResponse)
async def transcribe_audio(audio: UploadFile = File(...)) -> TranscriptResponse:
    """
    Accept microphone audio recording and return transcribed text.
    1. Normalize audio content type and validate against ALLOWED_AUDIO_TYPES.
    2. Read payload bytes; validate non-empty (422) and under MAX_AUDIO_BYTES (413).
    3. Call transcribe() via asyncio.to_thread with model fallback.
    4. Return TranscriptResponse(transcript=transcript).
    """
    normalized_type = normalize_content_type(audio.content_type, audio.filename)

    payload = await audio.read()
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Audio recording was empty.",
        )
    if len(payload) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds size limit (10MB).",
        )

    filename = audio.filename or "recording.webm"
    try:
        transcript = await asyncio.to_thread(transcribe, payload, filename, normalized_type)
        return TranscriptResponse(transcript=transcript)
    except GroqAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except GroqRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except GroqNetworkError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except GroqSttError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Speech transcription failed.",
        ) from exc
