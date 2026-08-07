"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import agents, hitl, ingest, runs
from .api.routes import rag as rag_router
from .config import get_settings
from .integrations.publisher import create_publisher
from .orchestration.orchestrator import ReviewOrchestrator
from .persistence.memory import InMemoryRunRepository
from .rag.embeddings import FeatureHashEmbedder
from .rag.service import RagService
from .rag.vector_store import InMemoryVectorStore
from .services.event_bus import EventBus
from .services.llm_gateway import create_gateway


def _seed_guidelines(rag: RagService, directory: Path) -> int:
    """Index every ``*.md`` guideline file; missing directory is a no-op."""
    if not directory.is_dir():
        return 0
    total = 0
    for path in sorted(directory.glob("*.md")):
        total += rag.index_document(
            source_type="guideline", path=path.name, content=path.read_text()
        )
    return total


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.cors_origins.split(",")
            if origin.strip()
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    repo = InMemoryRunRepository()
    bus = EventBus()
    gateway = create_gateway(settings)
    rag = RagService(InMemoryVectorStore(), FeatureHashEmbedder(settings.embedding_dim))
    _seed_guidelines(rag, Path(settings.rag_guidelines_dir))
    orchestrator = ReviewOrchestrator(
        repo=repo,
        bus=bus,
        gateway=gateway,
        settings=settings,
        rag=rag,
        publisher=create_publisher(settings),
    )

    app.state.repo = repo
    app.state.bus = bus
    app.state.gateway = gateway
    app.state.rag = rag
    app.state.orchestrator = orchestrator
    app.state.settings = settings

    app.include_router(ingest.router)
    app.include_router(runs.router)
    app.include_router(hitl.router)
    app.include_router(rag_router.router)
    app.include_router(agents.router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
