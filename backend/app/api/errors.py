"""Error responses of the HTTP API: one JSON shape, fixed messages per code, and no text sent by the user.

Validation errors from Pydantic keep only their `type` code and a sanitized location: `input`, `msg`, `ctx`, `url` and
the request body (`exc.body`) are never used, and a field name that is not part of the schemas becomes `<extra>`,
because an unknown field name is itself text written by the client. Rejected entries are described by the service's
`EntryIssue` (positions, reason codes, token counts), so no word is reintroduced.

Handlers here run inside `ExceptionMiddleware`; unexpected exceptions are handled by the `ErrorBoundary` middleware,
never by a handler registered for `Exception` (Starlette would route it to the outermost `ServerErrorMiddleware`,
outside the request-ID and CORS middleware, and would re-raise it to the server).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services import AnalysisBusy, EntriesRejected, ServiceError, ServiceUnavailable, TooManyWords

from .schemas import ErrorResponse

MESSAGES = {
    "request_invalid": "The request is not valid.",
    "invalid_entries": "One or more entries are invalid.",
    "too_few_words": "At least two valid words are needed.",
    "too_many_words": "Too many words in one request.",
    "analysis_busy": "Another analysis is running. Try again shortly.",
    "service_unavailable": "The analysis service is not available.",
    "payload_too_large": "The request body is too large.",
    "not_found": "Not found.",
    "method_not_allowed": "Method not allowed.",
    "internal_error": "Internal error.",
}
SCHEMA_FIELDS = frozenset({"body", "word_a", "word_b", "words"})
EXTRA_FIELD = "<extra>"


class PayloadTooLarge(HTTPException):
    """Raised by the BodyLimit middleware when the received body exceeds the limit.

    It is an HTTPException so that FastAPI re-raises it from its body reader (any other exception there becomes a 400)
    and the handler below answers it; ErrorBoundary also recognizes it if it ever escapes the handlers.
    """

    def __init__(self, max_bytes: int) -> None:
        super().__init__(status_code=413)
        self.max_bytes = max_bytes


def request_id_of(scope) -> str | None:
    state = scope.get("state")
    return state.get("request_id") if isinstance(state, dict) else None


def error_response(scope, status: int, code: str, details: dict[str, Any] | None = None,
                   headers: dict[str, str] | None = None) -> JSONResponse:
    """The single place where an error body is built. Records the code for the request log."""
    state = scope.setdefault("state", {})
    state["error_code"] = code
    body = ErrorResponse(request_id=request_id_of(scope), code=code, message=MESSAGES[code], details=details or {})
    return JSONResponse(body.model_dump(), status_code=status, headers=headers)


def payload_too_large(scope, max_bytes: int | None) -> JSONResponse:
    # Connection: close, so the rest of a rejected body is never read or kept on a persistent connection.
    return error_response(scope, 413, "payload_too_large", {"max_bytes": max_bytes} if max_bytes is not None else {},
                          headers={"Connection": "close"})


def sanitize_location(location: Sequence[Any]) -> list[str | int]:
    return [part if (isinstance(part, int) and not isinstance(part, bool)) or part in SCHEMA_FIELDS else EXTRA_FIELD
            for part in location]


def sanitize_validation_errors(errors: Sequence[Any]) -> list[dict[str, Any]]:
    """Only the validation type code and the sanitized location of each error."""
    clean = []
    for error in errors:
        kind = error.get("type") if isinstance(error, dict) else None
        location = error.get("loc", ()) if isinstance(error, dict) else ()
        clean.append({"loc": sanitize_location(location if isinstance(location, (list, tuple)) else ()),
                      "type": kind if isinstance(kind, str) and kind.isidentifier() else "invalid"})
    return clean


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(request.scope, 422, "request_invalid", {"errors": sanitize_validation_errors(exc.errors())})


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc, PayloadTooLarge) or exc.status_code == 413:
        return payload_too_large(request.scope, getattr(exc, "max_bytes", None))
    if exc.status_code == 404:
        return error_response(request.scope, 404, "not_found")
    if exc.status_code == 405:
        allow = (exc.headers or {}).get("Allow") or (exc.headers or {}).get("allow")
        return error_response(request.scope, 405, "method_not_allowed", headers={"Allow": allow} if allow else None)
    if 400 <= exc.status_code < 500:  # for example 400 when the body cannot be read
        return error_response(request.scope, exc.status_code, "request_invalid")
    return error_response(request.scope, 500, "internal_error")


async def handle_service_error(request: Request, exc: ServiceError) -> JSONResponse:
    scope = request.scope
    if isinstance(exc, EntriesRejected):
        details = {"entries": [dataclasses.asdict(issue) for issue in exc.issues]} if exc.issues else {}
        return error_response(scope, 422, exc.code, details)
    if isinstance(exc, TooManyWords):
        return error_response(scope, 422, "too_many_words",
                              {"max_words": exc.max_words, "received_at_least": exc.received_at_least})
    if isinstance(exc, AnalysisBusy):
        return error_response(scope, 503, "analysis_busy", headers={"Retry-After": "1"})
    if isinstance(exc, ServiceUnavailable):
        return error_response(scope, 503, "service_unavailable", {"state": getattr(exc.state, "value", str(exc.state))})
    return error_response(scope, 500, "internal_error")


EXCEPTION_HANDLERS = {
    RequestValidationError: handle_validation_error,
    HTTPException: handle_http_exception,
    ServiceError: handle_service_error,
}
