from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.automation import router as automation_router
from app.api.capabilities import router as capabilities_router
from app.api.chat import router as chat_router
from app.api.coding import router as coding_router
from app.api.diagnostics import router as diagnostics_router
from app.api.files import router as files_router
from app.api.generation import router as generation_router
from app.api.local_actions import router as local_actions_router
from app.api.memory import router as memory_router
from app.api.projects import router as projects_router
from app.api.research import router as research_router
from app.api.settings_api import router as settings_router
from app.api.speech import router as speech_router
from app.api.study import router as study_router
from app.api.web_actions import router as web_actions_router
from app.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("jarvis.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("==================================================")
    logger.info("  JARVIS PRODUCTION AI ASSISTANT CORE ONLINE")
    logger.info("  Workspace Root: %s", settings.workspace_root)
    logger.info("  Data Dir: %s", settings.data_dir)
    logger.info("  Active AI Provider: %s", settings.ai_provider)
    logger.info("==================================================")
    yield
    logger.info("JARVIS Assistant shutting down.")


app = FastAPI(
    title="JARVIS Production AI Assistant",
    description="An elite, highly capable, serious, and joyful AI personal assistant for Windows inspired by JARVIS.",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

from app.api.health import router as health_router

# Include All Routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(files_router)
app.include_router(generation_router)
app.include_router(study_router)
app.include_router(research_router)
app.include_router(coding_router)
app.include_router(projects_router)
app.include_router(memory_router)
app.include_router(automation_router)
app.include_router(settings_router)
app.include_router(diagnostics_router)
app.include_router(capabilities_router)
app.include_router(local_actions_router)
app.include_router(speech_router)
app.include_router(web_actions_router)


@app.get("/api/health")
async def health_api_alias() -> dict[str, str]:
    return {"status": "ok"}

