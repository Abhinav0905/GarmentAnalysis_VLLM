from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agent_tracing.tracer import AgentTracer
from app.api.routers.garments import router as garments_router
from app.api.routers.health import router as health_router
from app.api.routers.pages import router as pages_router
from app.llm_clients.mock_client import MockFashionLLMClient
from app.llm_clients.openai_client import OpenAIFashionLLMClient
from app.repositories.database import Database
from app.repositories.garment_repository import GarmentRepository
from app.services.annotation_service import AnnotationService
from app.services.classification_service import ClassificationService
from app.services.sample_data_service import SampleDataService
from app.services.search_service import SearchService
from app.token_calculation.token_calculator import TokenCalculator
from app.utils.config import Settings
from app.utils.file_store import FileStore

BASE_DIR = Path(__file__).resolve().parents[1]


def build_static_version(static_dir: Path) -> str:
    # Use the latest static asset modification time as a lightweight cache
    # buster for the browser.
    asset_paths = [static_dir / "app.js", static_dir / "styles.css"]
    mtimes = [int(path.stat().st_mtime) for path in asset_paths if path.exists()]
    return str(max(mtimes, default=0))


def build_llm_client(settings: Settings):
    # Keep provider selection in one place so the rest of the app only talks to
    # the shared BaseLLMClient interface.
    if settings.model_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("MODEL_PROVIDER=openai but OPENAI_API_KEY is empty. Add it to .env.")
        return OpenAIFashionLLMClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout_seconds=settings.openai_timeout_seconds,
        )
    if settings.model_provider == "mock":
        return MockFashionLLMClient()
    raise ValueError(f"Unsupported MODEL_PROVIDER: {settings.model_provider}")


def create_app() -> FastAPI:
    settings = Settings.from_env()
    settings.ensure_directories()

    # Build the app "container" once at startup and store shared services on
    # app.state so the routers can reuse them on every request.
    database = Database(settings.database_path)
    database.initialize()

    file_store = FileStore(settings.upload_dir)
    repository = GarmentRepository(database)
    tracer = AgentTracer(settings.trace_log_path)
    token_calculator = TokenCalculator()
    llm_client = build_llm_client(settings)
    search_service = SearchService(
        repository=repository,
        file_store=file_store,
        llm_client=llm_client,
    )
    annotation_service = AnnotationService(
        repository=repository,
        search_service=search_service,
    )
    classification_service = ClassificationService(
        repository=repository,
        file_store=file_store,
        llm_client=llm_client,
        tracer=tracer,
        token_calculator=token_calculator,
        search_service=search_service,
        settings=settings,
    )
    sample_data_service = SampleDataService(
        repository=repository,
        file_store=file_store,
        repo_root=BASE_DIR.parent,
    )
    if settings.seed_sample_data:
        sample_data_service.seed_from_pexels_if_needed()

    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    app.state.static_version = build_static_version(BASE_DIR / "static")
    app.state.services = {
        "search_service": search_service,
        "annotation_service": annotation_service,
        "classification_service": classification_service,
    }

    # Static assets serve the browser UI, while /uploads exposes saved images.
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")

    app.include_router(pages_router)
    app.include_router(health_router, prefix="/api")
    app.include_router(garments_router, prefix="/api")
    return app
