"""The four endpoints of the HTTP API v1. They call `AnalysisService` only, never the engine or the embedder.

The endpoints are synchronous `def` functions: FastAPI runs them in a worker thread, so the service's thread lock is
acquired and released in the same thread, and the event loop is never blocked by an analysis.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.services import AnalysisService, ServiceState, interpret_set

from .schemas import HealthResponse, ModelResponse, PairRequest, PairResponse, SetRequest, SetResponse

router = APIRouter(prefix="/api/v1")


def get_service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


Service = Annotated[AnalysisService, Depends(get_service)]


@router.get("/health", response_model=HealthResponse)
def health(response: Response, service: Service) -> HealthResponse:
    state = service.status()
    if state is not ServiceState.READY:
        response.status_code = 503
    return HealthResponse(status=state.value)


@router.get("/model", response_model=ModelResponse)
def model(request: Request) -> ModelResponse:
    return request.app.state.model_response  # built once at startup


@router.post("/pairs", response_model=PairResponse)
def pairs(body: PairRequest, request: Request, service: Service) -> PairResponse:
    request.state.operation, request.state.entries = "analyze_pair", 2
    return PairResponse.from_result(service.analyze_pair(body.word_a, body.word_b))


@router.post("/sets", response_model=SetResponse)
def sets(body: SetRequest, request: Request, service: Service) -> SetResponse:
    request.state.operation, request.state.entries = "analyze_set", len(body.words)
    result = service.analyze_set(body.words)  # the analysis, and its exclusive section, end here
    # A pure function over the numbers just computed. If it fails, nothing partial is sent: the exception reaches
    # ErrorBoundary (generic 500, sanitized log) and the service state is untouched.
    return SetResponse.from_result(result, interpret_set(result))
