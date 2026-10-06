from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()


def parse_origins(value: str) -> tuple[str, ...]:
    return tuple(origin.strip().rstrip("/") for origin in value.split(",") if origin.strip())


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    backend_host: str = os.getenv("JARVIS_BACKEND_HOST", "127.0.0.1")
    backend_port: int = int(os.getenv("JARVIS_BACKEND_PORT", "8765"))
    
    # AI Providers & Keys
    ai_provider: str = os.getenv("JARVIS_AI_PROVIDER", "auto")  # "auto", "gemini", "groq", "openai", "anthropic", "local"
    google_api_key: str = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_chat_model: str = os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-120b")
    groq_fallback_model: str = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")

    # Application & Origins
    allowed_origins: tuple[str, ...] = parse_origins(
        os.getenv(
            "JARVIS_ALLOWED_ORIGINS",
            "http://localhost:1420,http://127.0.0.1:1420,http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
        )
    )
    local_actions_enabled: bool = parse_bool(os.getenv("JARVIS_LOCAL_ACTIONS_ENABLED", "true"))
    web_search_enabled: bool = parse_bool(os.getenv("JARVIS_WEB_SEARCH_ENABLED", "true"))
    permission_mode: str = os.getenv("JARVIS_PERMISSION_MODE", "assisted")  # "read_only", "assisted", "full_control"

    # Workspace & Directories
    workspace_root: Path = Path(os.getenv("JARVIS_WORKSPACE_ROOT", str(BASE_DIR.parent.parent))).resolve()
    data_dir: Path = (BASE_DIR / "data").resolve()
    uploads_dir: Path = field(init=False)
    generated_dir: Path = field(init=False)
    projects_dir: Path = field(init=False)
    max_tool_iterations: int = 6
    sandbox_timeout_seconds: int = 10

    def __post_init__(self) -> None:
        self.uploads_dir = self.data_dir / "uploads"
        self.generated_dir = self.data_dir / "generated"
        self.projects_dir = self.data_dir / "projects"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
