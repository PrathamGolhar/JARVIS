from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _get_first_env(*keys: str, default: str = "") -> str:
    for k in keys:
        v = os.getenv(k)
        if v is not None and v.strip():
            return v.strip()
    return default


def parse_origins(value: str) -> tuple[str, ...]:
    return tuple(origin.strip().rstrip("/") for origin in value.split(",") if origin.strip())


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    # 1. Environment & Host
    env: str = field(
        default_factory=lambda: _get_first_env("JARVIS_ENV", "ENVIRONMENT", default="development")
    )
    backend_host: str = field(
        default_factory=lambda: _get_first_env("JARVIS_HOST", "JARVIS_BACKEND_HOST", "HOST", default="127.0.0.1")
    )
    backend_port: int = field(
        default_factory=lambda: int(_get_first_env("JARVIS_PORT", "JARVIS_BACKEND_PORT", "PORT", default="8765"))
    )

    # 2. AI Providers & Model Configuration
    ai_provider: str = field(
        default_factory=lambda: _get_first_env("JARVIS_AI_PROVIDER", "AI_PROVIDER", default="auto").lower()
    )
    gemini_api_key: str = field(
        default_factory=lambda: _get_first_env("JARVIS_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", default="")
    )
    gemini_model: str = field(
        default_factory=lambda: _get_first_env("JARVIS_GEMINI_MODEL", "GEMINI_MODEL", default="gemini-2.5-flash")
    )
    groq_api_key: str = field(
        default_factory=lambda: _get_first_env("JARVIS_GROQ_API_KEY", "GROQ_API_KEY", default="")
    )
    groq_chat_model: str = field(
        default_factory=lambda: _get_first_env("JARVIS_GROQ_MODEL", "GROQ_CHAT_MODEL", "GROQ_MODEL", default="openai/gpt-oss-120b")
    )
    groq_fallback_model: str = field(
        default_factory=lambda: _get_first_env("JARVIS_GROQ_FALLBACK_MODEL", "GROQ_FALLBACK_MODEL", default="openai/gpt-oss-20b")
    )
    openai_api_key: str = field(
        default_factory=lambda: _get_first_env("JARVIS_OPENAI_API_KEY", "OPENAI_API_KEY", default="")
    )
    openai_model: str = field(
        default_factory=lambda: _get_first_env("JARVIS_OPENAI_MODEL", "OPENAI_MODEL", default="gpt-4o")
    )
    anthropic_api_key: str = field(
        default_factory=lambda: _get_first_env("JARVIS_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY", default="")
    )
    anthropic_model: str = field(
        default_factory=lambda: _get_first_env("JARVIS_ANTHROPIC_MODEL", "ANTHROPIC_MODEL", default="claude-3-5-sonnet-20241022")
    )
    elevenlabs_api_key: str = field(
        default_factory=lambda: _get_first_env("JARVIS_ELEVENLABS_API_KEY", "ELEVENLABS_API_KEY", default="")
    )

    # 3. Speech & Voice Pipeline
    stt_provider: str = field(
        default_factory=lambda: _get_first_env("JARVIS_STT_PROVIDER", default="groq-whisper")
    )
    tts_provider: str = field(
        default_factory=lambda: _get_first_env("JARVIS_TTS_PROVIDER", default="edge-tts")
    )
    default_tts_voice: str = field(
        default_factory=lambda: _get_first_env("EDGE_TTS_VOICE", default="en-US-GuyNeural")
    )

    # 4. Storage & Database
    database_url: str = field(
        default_factory=lambda: _get_first_env("JARVIS_DATABASE_URL", "DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'data' / 'jarvis_memory.db'}")
    )
    workspace_root: Path = field(
        default_factory=lambda: Path(
            _get_first_env(
                "JARVIS_WORKSPACE_ROOT",
                "JARVIS_WORKSPACE_DIR",
                default=str(BASE_DIR.parent),  # Defaults to JARVIS repo root
            )
        ).resolve()
    )
    data_dir: Path = field(
        default_factory=lambda: (BASE_DIR / "data").resolve()
    )
    uploads_dir: Path = field(init=False)
    generated_dir: Path = field(init=False)
    projects_dir: Path = field(init=False)

    # 5. Security, Permissions & Sandbox
    allowed_origins: tuple[str, ...] = field(
        default_factory=lambda: parse_origins(
            _get_first_env(
                "JARVIS_ALLOWED_ORIGINS",
                "CORS_ORIGINS",
                default="http://localhost:1420,http://127.0.0.1:1420,http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
            )
        )
    )
    local_actions_enabled: bool = field(
        default_factory=lambda: parse_bool(_get_first_env("JARVIS_LOCAL_ACTIONS_ENABLED", default="true"))
    )
    web_search_enabled: bool = field(
        default_factory=lambda: parse_bool(_get_first_env("JARVIS_WEB_SEARCH_ENABLED", default="true"))
    )
    permission_mode: str = field(
        default_factory=lambda: _get_first_env("JARVIS_PERMISSION_MODE", "JARVIS_SAFETY_TIER", default="assisted").lower()
    )
    max_tool_iterations: int = 8
    sandbox_timeout_seconds: int = field(
        default_factory=lambda: int(_get_first_env("JARVIS_SANDBOX_TIMEOUT", default="15"))
    )
    sandbox_memory_limit_mb: int = field(
        default_factory=lambda: int(_get_first_env("JARVIS_SANDBOX_MEMORY_LIMIT", default="512"))
    )
    sandbox_cpu_limit_pct: int = field(
        default_factory=lambda: int(_get_first_env("JARVIS_SANDBOX_CPU_LIMIT", default="80"))
    )

    # Compatibility property for google_api_key
    @property
    def google_api_key(self) -> str:
        return self.gemini_api_key

    @google_api_key.setter
    def google_api_key(self, value: str) -> None:
        self.gemini_api_key = value

    def __post_init__(self) -> None:
        custom_uploads = os.getenv("JARVIS_UPLOAD_ROOT")
        custom_generated = os.getenv("JARVIS_GENERATED_ROOT")

        self.uploads_dir = Path(custom_uploads).resolve() if custom_uploads else self.data_dir / "uploads"
        self.generated_dir = Path(custom_generated).resolve() if custom_generated else self.data_dir / "generated"
        self.projects_dir = self.data_dir / "projects"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
