"""Composition root of the HTTP application. The only module of the application that knows `GraniteEmbedder`.

Run from `backend/` (one process, so one model in memory):

    ..\\.venv\\Scripts\\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
        --lifespan on --loop asyncio --http h11 --no-access-log --timeout-graceful-shutdown 10

Startup builds the embedder once (its constructor enforces offline mode and checks the model), then the service and
the public model metadata; any failure stops the startup before a request is accepted. Shutdown happens after Uvicorn
has drained the connections, and only closes the service: the weights are not unloaded explicitly.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.errors import EXCEPTION_HANDLERS
from app.api.middleware import configure_logger, install_middleware
from app.api.routes import router
from app.api.schemas import ModelResponse
from app.engine import Embedder, GraniteEmbedder
from app.services import AnalysisService
from app.settings import AppSettings

# FastAPI 0.162 telemetry, fully disabled; these keys override the defaults, including FASTAPI_OTEL_AUTO_CONFIGURE.
TELEMETRY = {"auto_configure": False, "tracing": False, "metrics": False, "logs": False, "operation_spans": False}


def create_app(settings: AppSettings | None = None, *,
               embedder_factory: Callable[[], Embedder] = GraniteEmbedder) -> FastAPI:
    settings = AppSettings.from_env() if settings is None else settings
    logger = configure_logger(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        embedder = embedder_factory()
        service = AnalysisService(embedder, **({"max_words": settings.max_words} if settings.max_words is not None else {}))
        try:
            model_response = ModelResponse.from_info(service.model_info())
        except BaseException:
            service.close()  # never leave a service READY that the application will not use
            raise
        app.state.analysis_service = service
        app.state.model_response = model_response
        try:
            yield
        finally:
            service.close()

    app = FastAPI(title="Diverge", version=__version__, telemetry=TELEMETRY, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan,
                  exception_handlers=dict(EXCEPTION_HANDLERS))
    app.include_router(router)
    install_middleware(app, max_body_bytes=settings.max_body_bytes, cors_origins=settings.cors_origins, logger=logger)
    return app
