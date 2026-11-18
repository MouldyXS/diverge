"""ASGI middleware of the HTTP API, and the `diverge.api` logger.

Effective order, outermost first (registered in reverse by `app.main`, because `add_middleware` inserts at the front):

    ServerErrorMiddleware        Starlette's last resort; nothing should reach it
    ExceptionTelemetryMiddleware FastAPI's; inert while telemetry is disabled
    RequestContext               request ID, X-Request-ID on every response, one log line per request
    CORSMiddleware               answers preflights; adds CORS headers to every response, 413 and 500 included
    ErrorBoundary                unexpected exceptions -> generic 500, logged without message or locals; PayloadTooLarge -> 413
    BodyLimit                    the API's body-size limit, applied to every request body (read before the route runs)
    ExceptionMiddleware          handlers of app.api.errors
    router

Nothing logged here contains request bodies, words, query strings, exception messages or local variables.
"""

from __future__ import annotations

import logging
import sys
import time
import traceback
import uuid
from pathlib import Path

from starlette.requests import ClientDisconnect

from .errors import PayloadTooLarge, error_response, payload_too_large, request_id_of

LOGGER_NAME = "diverge.api"
_KNOWN_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})


class _StderrHandler(logging.StreamHandler):
    """Writes to the current `sys.stderr` at each emit (so a replaced stream, for example under pytest, is followed)."""

    _diverge = True

    def __init__(self) -> None:
        super().__init__()

    @property
    def stream(self):
        return sys.stderr

    @stream.setter
    def stream(self, value) -> None:
        pass


def configure_logger(level: str) -> logging.Logger:
    """Idempotent: one handler of its own, however many applications are created; never touches the root logger."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    if not any(getattr(handler, "_diverge", False) for handler in logger.handlers):
        handler = _StderrHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)
    return logger


def _state(scope) -> dict:
    return scope.setdefault("state", {})


def _route_template(scope) -> str:
    path = getattr(scope.get("route"), "path", None)
    return path if isinstance(path, str) else "<unmatched>"  # never the received URL


class RequestContext:
    """One server-generated UUID4 per request, stored in `scope["state"]["request_id"]` for every inner layer."""

    def __init__(self, app, logger: logging.Logger | None = None) -> None:
        self.app = app
        self.logger = logger or logging.getLogger(LOGGER_NAME)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid.uuid4())  # a client's X-Request-ID is ignored
        state = _state(scope)
        state["request_id"] = request_id
        header = (b"x-request-id", request_id.encode("ascii"))
        status = None
        started = time.perf_counter()

        async def send_with_id(message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [item for item in message.get("headers", []) if item[0].lower() != b"x-request-id"]
                message = {**message, "headers": [*headers, header]}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            method = scope.get("method")
            self.logger.info(
                "request request_id=%s method=%s route=%s status=%s duration_ms=%.1f operation=%s entries=%s error=%s%s",
                request_id, method if method in _KNOWN_METHODS else "<other>", _route_template(scope),
                status if status is not None else "-", (time.perf_counter() - started) * 1000.0,
                state.get("operation", "-"), state.get("entries", "-"), state.get("error_code", "-"),
                " interrupted=yes" if state.get("interrupted") else "",
            )


class _SendFailed(Exception):
    """The client connection failed while a response was being sent (an OSError from `send`)."""


class ErrorBoundary:
    """Turns unexpected exceptions into a generic 500 and logs only sanitized diagnostics; never re-raises them.

    * Before `http.response.start`: a 500 `internal_error` body with the request ID (CORS, outside, adds its headers).
    * After it: no second response; the request is ended by returning, and the server closes the connection
      without the exception's message ("returned without completing response").
    * A failure of `send` (OSError) or a disconnect seen by `receive` is logged as an interrupted request, not as an
      internal error; an OSError raised by the application itself is an internal error.
    """

    def __init__(self, app, logger: logging.Logger | None = None) -> None:
        self.app = app
        self.logger = logger or logging.getLogger(LOGGER_NAME)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        state = _state(scope)
        flags = {"started": False}

        async def receive_tracked():
            message = await receive()
            if message["type"] == "http.disconnect" and not flags["started"]:
                state["interrupted"] = True
            return message

        async def send_tracked(message) -> None:
            if message["type"] == "http.response.start":
                flags["started"] = True
            try:
                await send(message)
            except OSError:
                raise _SendFailed() from None

        try:
            await self.app(scope, receive_tracked, send_tracked)
        except _SendFailed:
            state["interrupted"] = True
            self.logger.warning("client connection failed while sending request_id=%s", request_id_of(scope))
        except PayloadTooLarge as exc:
            if not flags["started"]:
                await payload_too_large(scope, exc.max_bytes)(scope, receive, send)
            else:
                self._log_internal(scope, exc, started=True)
        except ClientDisconnect:
            state["interrupted"] = True
        except Exception as exc:  # noqa: BLE001 - the boundary of the application
            self._log_internal(scope, exc, started=flags["started"])
            if not flags["started"]:
                await error_response(scope, 500, "internal_error")(scope, receive, send)
            else:
                state["error_code"] = "internal_error"

    def _log_internal(self, scope, exc: BaseException, started: bool) -> None:
        frames = traceback.extract_tb(exc.__traceback__)
        last = frames[-1] if frames else None
        service = getattr(getattr(scope.get("app"), "state", None), "analysis_service", None)
        try:
            service_state = service.status().value if service is not None else "-"
        except Exception:  # noqa: BLE001 - diagnostics must not fail
            service_state = "unknown"
        self.logger.error(
            "internal error request_id=%s exception=%s module=%s function=%s line=%s service_state=%s response_started=%s",
            request_id_of(scope), type(exc).__name__, Path(last.filename).stem if last else "-", last.name if last else "-",
            last.lineno if last else "-", service_state, "yes" if started else "no",
        )


class BodyLimit:
    """Applies `max_body_bytes` to every HTTP request, whatever its method and whether or not the route reads the body.

    * A valid Content-Length above the limit is rejected at once, without calling `receive` or the application.
    * Otherwise the body is read **before** the application runs, message by message, counting the bytes actually
      received (the declared length is not trusted). Each message is checked before it is kept, so at most
      `max_body_bytes` are retained; the first message that would pass the limit stops the reading (it is not stored)
      and the request is rejected with `PayloadTooLarge`, which ErrorBoundary (outside) turns into the 413 response.
    * A body within the limit is replayed to the application unchanged: the same messages, in order, with their
      `more_body` flags, and then the original `receive` for whatever follows (for example `http.disconnect`).
    * If the client disconnects before the body is complete, the application is not called and nothing is sent.
    """

    def __init__(self, app, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = _content_length(scope)
        if declared is not None and declared > self.max_body_bytes:
            await payload_too_large(scope, self.max_body_bytes)(scope, receive, send)
            return
        stored, total = [], 0
        while True:
            message = await receive()
            if message["type"] != "http.request":  # http.disconnect: the body is incomplete
                _state(scope)["interrupted"] = True
                return
            total += len(message.get("body", b""))
            if total > self.max_body_bytes:
                raise PayloadTooLarge(self.max_body_bytes)  # nothing more is read or kept
            stored.append(message)
            if not message.get("more_body", False):
                break
        replay = iter(stored)

        async def receive_replayed():
            return next(replay, None) or await receive()

        await self.app(scope, receive_replayed, send)


def install_middleware(app, *, max_body_bytes: int, cors_origins: tuple[str, ...], logger: logging.Logger) -> None:
    """Register the middleware so that the effective order is the one in the module docstring.

    `add_middleware` inserts at the front of the list, so the innermost layer is registered first.
    """
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(BodyLimit, max_body_bytes=max_body_bytes)
    app.add_middleware(ErrorBoundary, logger=logger)
    if cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(cors_origins), allow_methods=["GET", "POST"],
                           allow_headers=["Content-Type"], allow_credentials=False, expose_headers=["X-Request-ID"],
                           max_age=600)
    app.add_middleware(RequestContext, logger=logger)


def middleware_chain(app) -> list[str]:
    """Class names of the built ASGI stack, outermost first (for tests and diagnostics)."""
    names, layer = [], app.build_middleware_stack()
    while layer is not None and not getattr(layer, "routes", None):
        names.append(type(layer).__name__)
        layer = getattr(layer, "app", None)
    return names


def _content_length(scope) -> int | None:
    values = [value for name, value in scope.get("headers", []) if name.lower() == b"content-length"]
    if len(values) != 1 or not values[0].isdigit():
        return None
    return int(values[0])
