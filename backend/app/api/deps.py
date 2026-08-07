"""FastAPI dependency accessors for app singletons."""

from typing import Annotated

from fastapi import Depends, Request

from ..config import Settings
from ..orchestration.orchestrator import ReviewOrchestrator
from ..persistence.memory import InMemoryRunRepository
from ..rag.service import RagService
from ..services.event_bus import EventBus


def get_repo(request: Request) -> InMemoryRunRepository:
    return request.app.state.repo


def get_bus(request: Request) -> EventBus:
    return request.app.state.bus


def get_orchestrator(request: Request) -> ReviewOrchestrator:
    return request.app.state.orchestrator


def get_rag(request: Request) -> RagService:
    return request.app.state.rag


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


RepoDep = Annotated[InMemoryRunRepository, Depends(get_repo)]
BusDep = Annotated[EventBus, Depends(get_bus)]
OrchestratorDep = Annotated[ReviewOrchestrator, Depends(get_orchestrator)]
RagDep = Annotated[RagService, Depends(get_rag)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
