"""HTTP API (stage 3B.7) with synthetic embedders and the real AnalysisService. No model.

Every test builds its own application. Threads are coordinated with events; timeouts are safeguards only.
"""

import pytest

from app.settings import DEFAULT_CORS_ORIGINS, DEFAULT_MAX_BODY_BYTES, AppSettings, SettingsError

# A. Settings


def test_defaults_when_no_variable_is_set():
    settings = AppSettings.from_env({})
    assert settings == AppSettings()
    assert settings.max_words is None  # the service keeps its own default
    assert settings.max_body_bytes == DEFAULT_MAX_BODY_BYTES == 262144
    assert settings.cors_origins == DEFAULT_CORS_ORIGINS == ("http://localhost:5173", "http://127.0.0.1:5173")
    assert settings.log_level == "INFO"


def test_valid_variables_are_read():
    settings = AppSettings.from_env({
        "DIVERGE_MAX_WORDS": "16", "DIVERGE_MAX_BODY_BYTES": "1024",
        "DIVERGE_CORS_ORIGINS": "http://localhost:3000, https://example.test:8443", "DIVERGE_LOG_LEVEL": "warning",
        "UNRELATED": "ignored",
    })
    assert (settings.max_words, settings.max_body_bytes, settings.log_level) == (16, 1024, "WARNING")
    assert settings.cors_origins == ("http://localhost:3000", "https://example.test:8443")


def test_empty_cors_variable_disables_cors():
    assert AppSettings.from_env({"DIVERGE_CORS_ORIGINS": ""}).cors_origins == ()
    assert AppSettings.from_env({"DIVERGE_CORS_ORIGINS": "   "}).cors_origins == ()


SECRET = "SECRET_VALUE_84"


@pytest.mark.parametrize("name, value", [
    ("DIVERGE_MAX_WORDS", ""), ("DIVERGE_MAX_WORDS", "-3"), ("DIVERGE_MAX_WORDS", "3.0"), ("DIVERGE_MAX_WORDS", "٣"),
    ("DIVERGE_MAX_WORDS", SECRET), ("DIVERGE_MAX_BODY_BYTES", ""), ("DIVERGE_MAX_BODY_BYTES", "0"),
    ("DIVERGE_MAX_BODY_BYTES", "-1"), ("DIVERGE_MAX_BODY_BYTES", "1e6"), ("DIVERGE_MAX_BODY_BYTES", SECRET),
    ("DIVERGE_CORS_ORIGINS", "*"), ("DIVERGE_CORS_ORIGINS", "http://localhost:5173/"),
    ("DIVERGE_CORS_ORIGINS", "http://localhost:5173/app"), ("DIVERGE_CORS_ORIGINS", "http://localhost:5173?x=1"),
    ("DIVERGE_CORS_ORIGINS", "http://localhost:5173#f"), ("DIVERGE_CORS_ORIGINS", "ftp://localhost"),
    ("DIVERGE_CORS_ORIGINS", "http://user:pw@localhost"), ("DIVERGE_CORS_ORIGINS", "http://localhost:99999"),
    ("DIVERGE_CORS_ORIGINS", "localhost:5173"), ("DIVERGE_CORS_ORIGINS", "http://a.test,,http://b.test"),
    ("DIVERGE_CORS_ORIGINS", "http://*.test"), ("DIVERGE_CORS_ORIGINS", f"http://{SECRET}.test/x"),
    ("DIVERGE_LOG_LEVEL", "VERBOSE"), ("DIVERGE_LOG_LEVEL", ""), ("DIVERGE_LOG_LEVEL", SECRET),
])
def test_invalid_variables_raise_without_repeating_the_value(name, value):
    with pytest.raises(SettingsError) as info:
        AppSettings.from_env({name: value})
    assert name in str(info.value)
    assert SECRET not in str(info.value) and (not value.strip() or value not in str(info.value))
    assert isinstance(info.value, ValueError)


@pytest.mark.parametrize("fields", [dict(max_words=True), dict(max_words="32"), dict(max_body_bytes=0),
                                    dict(max_body_bytes=True), dict(cors_origins=["http://a.test"]),
                                    dict(cors_origins=("*",)), dict(log_level="info")])
def test_direct_construction_is_validated_too(fields):
    with pytest.raises(SettingsError):
        AppSettings(**fields)


def test_the_value_32_is_not_repeated_in_the_settings():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app" / "settings.py").read_text(encoding="utf-8")
    assert "32" not in source.replace("262144", "")


# B. Schemas and errors (no application)

import ast  # noqa: E402
import asyncio  # noqa: E402
import json  # noqa: E402
import threading  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from starlette.requests import Request  # noqa: E402

from app.api import errors as api_errors  # noqa: E402
from app.api.schemas import (MODEL_DESCRIPTION_FIELDS, VERSION_KEYS, ModelResponse, PairRequest, PairResponse,  # noqa: E402
                             SetRequest, SetResponse)
from app.services import (AnalysisBusy, AnalysisService, EntriesRejected, EntryIssue, ServiceState,  # noqa: E402
                          ServiceUnavailable, TooManyWords)

BACKEND = Path(__file__).resolve().parents[1]
PRIVATE = "PRIVATE_WORD_9f73"
PASSWORD = "hunter2"
SECRET_FIELD = "SECRET_FIELD_84"
MARKERS = (PRIVATE, PRIVATE.lower(), PASSWORD, SECRET_FIELD)
WAIT = 10


def real_like_description():
    """Same keys as GraniteEmbedder.describe() (asdict(ModelSpec) plus the engine's own keys)."""
    return {
        "model_id": "fake/model", "revision": "declared-rev", "device": "cpu", "dtype": "float32", "batch_size": 32,
        "expected_dimension": 8, "expected_pooling": "cls", "expected_modules": ("Transformer", "Pooling", "Normalize"),
        "snapshot_revision": "snapshot-rev", "modules": ["Transformer", "Pooling", "Normalize"], "pooling_mode": "cls",
        "embedding_dimension": 8, "max_seq_length": 512, "attention_implementation": "sdpa", "can_flatten_inputs": False,
        "torch_threads": 12, "normalize_embeddings_argument": False, "hf_hub_offline": True,
        "versions": {"python": "3.12.10", "torch": "2.15.0+cpu", "transformers": "5.22.1",
                     "sentence_transformers": "6.2.0", "numpy": "2.5.4"},
    }


class FakeEmbedder:
    """`len(text) + 2` tokens against a 512-token limit; deterministic vectors; optional hook in `encode`."""

    max_input_tokens = 512

    def __init__(self, info=None, on_encode=None):
        self.info = real_like_description() if info is None else info
        self.on_encode = on_encode
        self.encode_calls = 0

    def count_tokens(self, texts):
        return [len(text) + 2 for text in texts]

    def encode(self, texts):
        self.encode_calls += 1
        if self.on_encode:
            self.on_encode(texts)
        rows = [np.random.default_rng(sum(ord(c) * (k + 1) for k, c in enumerate(t))).normal(size=8) for t in texts]
        return np.vstack(rows).astype(np.float32)

    def describe(self):
        return self.info


def raising(error):
    def hook(texts):
        raise error
    return hook


def test_requests_are_strict():
    assert PairRequest.model_validate({"word_a": "casa", "word_b": "hogar"}).word_b == "hogar"
    assert SetRequest.model_validate({"words": ["casa", "hogar"]}).words == ["casa", "hogar"]
    for bad in ({"words": "casa"}, {"words": [1, "casa"]}, {"words": ["casa"], "extra": 1}, {"words": ("casa",)}, {}):
        with pytest.raises(ValidationError):
            SetRequest.model_validate(bad)
    for bad in ({"word_a": 1, "word_b": "x"}, {"word_a": "x"}, {"word_a": "x", "word_b": "y", "z": 0},
                {"word_a": ["x"], "word_b": "y"}):
        with pytest.raises(ValidationError):
            PairRequest.model_validate(bad)


def test_schemas_apply_no_semantic_rule():
    # P0, token counts and the entry limit belong to the engine and the service, not to the schemas.
    assert SetRequest.model_validate({"words": ["", "dos palabras", "c4sa"] + ["x"] * 100}).words[0] == ""


def describe_keys_in_the_engine_source():
    """String keys of the dict returned by GraniteEmbedder.describe(), plus the ModelSpec fields, read with ast."""
    tree = ast.parse((BACKEND / "app" / "engine" / "embedder.py").read_text(encoding="utf-8"))
    spec = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ModelSpec")
    keys = {n.target.id for n in spec.body if isinstance(n, ast.AnnAssign)}
    granite = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "GraniteEmbedder")
    describe = next(n for n in granite.body if isinstance(n, ast.FunctionDef) and n.name == "describe")
    returned = next(n.value for n in ast.walk(describe) if isinstance(n, ast.Return))
    keys |= {k.value for k in returned.keys if isinstance(k, ast.Constant)}
    versions = next(v for k, v in zip(returned.keys, returned.values) if isinstance(k, ast.Constant) and k.value == "versions")
    return keys, {k.value for k in versions.keys}


def test_model_response_fields_correspond_to_real_description_keys():
    keys, version_keys = describe_keys_in_the_engine_source()
    assert {key for key, _ in MODEL_DESCRIPTION_FIELDS.values()} <= keys
    assert set(VERSION_KEYS) <= version_keys
    assert set(real_like_description()) == keys  # the test double mirrors the real description


def model_info(info=None):
    return AnalysisService(FakeEmbedder(info)).model_info()


def test_model_response_exposes_only_the_selected_fields():
    body = ModelResponse.from_info(model_info()).model_dump()
    assert body == {
        "model_id": "fake/model", "declared_revision": "declared-rev", "snapshot_revision": "snapshot-rev",
        "embedding_dimension": 8, "pooling_mode": "cls", "modules": ["Transformer", "Pooling", "Normalize"],
        "device": "cpu", "dtype": "float32", "attention_implementation": "sdpa", "batch_size": 32, "offline": True,
        "limits": {"max_words": 32, "max_input_tokens": 512},
        "versions": {"python": "3.12.10", "torch": "2.15.0+cpu", "transformers": "5.22.1",
                     "sentence_transformers": "6.2.0", "numpy": "2.5.4"},
        "api_version": "v1",
    }
    text = json.dumps(body)
    assert "expected" not in text and "torch_threads" not in text and "can_flatten" not in text


def test_optional_model_fields_are_null_when_missing_or_mistyped():
    info = real_like_description()
    for key in ("pooling_mode", "embedding_dimension", "versions", "snapshot_revision"):
        info.pop(key)
    info["modules"] = "Transformer"  # mistyped
    info["batch_size"] = True  # a bool is not a size
    body = ModelResponse.from_info(model_info(info)).model_dump()
    assert (body["pooling_mode"], body["embedding_dimension"], body["modules"], body["batch_size"]) == (None,) * 4
    assert body["snapshot_revision"] is None and body["declared_revision"] == "declared-rev"
    assert set(body["versions"].values()) == {None}


def test_pair_and_set_responses_keep_the_engine_values_exactly():
    service = AnalysisService(FakeEmbedder())
    pair = service.analyze_pair(" Casa", "PERRO")
    body = PairResponse.from_result(pair).model_dump()
    assert (body["word_a"], body["word_b"]) == ("casa", "perro")
    assert body["similarity"] == pair.analysis.similarity and body["distance"] == pair.analysis.distance
    assert json.loads(PairResponse.from_result(pair).model_dump_json())["distance"] == pair.analysis.distance
    result = service.analyze_set(["guerra", "paz", "noche"])
    body = SetResponse.from_result(result).model_dump()
    assert body["n_words"] == 3 and body["n_pairs"] == 3 and "distance_matrix" not in body
    assert [(p["i"], p["j"]) for p in body["pairs"]] == [(0, 1), (0, 2), (1, 2)]
    assert [p["distance"] for p in body["pairs"]] == [s.distance for s in result.analysis.pairs]
    assert body["mean_distance"] == result.analysis.mean_distance  # unscaled
    assert body["closest"]["distance"] == result.analysis.closest.distance
    assert body["model"] == {"model_id": "fake/model", "declared_revision": "declared-rev", "snapshot_revision": "snapshot-rev"}


def test_validation_errors_keep_only_type_and_safe_location():
    errors = [
        {"type": "extra_forbidden", "loc": ("body", SECRET_FIELD), "msg": "Extra inputs", "input": PASSWORD, "ctx": {"a": PRIVATE}},
        {"type": "string_type", "loc": ("body", "words", 3), "msg": f"bad {PRIVATE}", "input": 7, "url": "https://x"},
        {"type": "json_invalid", "loc": ("body", 11), "msg": "JSON decode error", "input": {}, "ctx": {"error": "Expecting value"}},
        {"type": f"{PRIVATE} not a type", "loc": "body"},
    ]
    clean = api_errors.sanitize_validation_errors(errors)
    assert clean == [{"loc": ["body", "<extra>"], "type": "extra_forbidden"}, {"loc": ["body", "words", 3], "type": "string_type"},
                     {"loc": ["body", 11], "type": "json_invalid"}, {"loc": [], "type": "invalid"}]
    assert not any(marker in json.dumps(clean) for marker in MARKERS)


def http_scope(request_id="rid-1"):
    return {"type": "http", "method": "POST", "path": "/", "headers": [], "query_string": b"", "state": {"request_id": request_id}}


def render(response):
    return response.status_code, json.loads(response.body), dict(response.headers)


def handle(exc):
    scope = http_scope()
    return (*render(asyncio.run(api_errors.handle_service_error(Request(scope), exc))), scope)


def test_service_errors_map_to_stable_codes_without_text():
    status, body, headers, scope = handle(EntriesRejected("invalid_entries", (EntryIssue(2, ("duplicate",), 12, 512),)))
    assert status == 422 and body == {"request_id": "rid-1", "code": "invalid_entries", "message": "One or more entries are invalid.",
                                      "details": {"entries": [{"position": 2, "reasons": ["duplicate"], "tokens": 12, "max_tokens": 512}]}}
    assert scope["state"]["error_code"] == "invalid_entries"
    assert handle(EntriesRejected("too_few_words"))[:2] == (422, {"request_id": "rid-1", "code": "too_few_words",
                                                                 "message": "At least two valid words are needed.", "details": {}})
    status, body, headers, _ = handle(TooManyWords(32, 33))
    assert (status, body["code"], body["details"]) == (422, "too_many_words", {"max_words": 32, "received_at_least": 33})
    status, body, headers, _ = handle(AnalysisBusy())
    assert (status, body["code"], headers.get("retry-after")) == (503, "analysis_busy", "1")
    for state in (ServiceState.FAILED, ServiceState.STOPPING):
        status, body, headers, _ = handle(ServiceUnavailable(state))
        assert (status, body["code"], body["details"], "retry-after" in headers) == (503, "service_unavailable", {"state": state.value}, False)


def test_every_code_has_a_fixed_message():
    assert set(api_errors.MESSAGES) == {"request_invalid", "invalid_entries", "too_few_words", "too_many_words", "analysis_busy",
                                        "service_unavailable", "payload_too_large", "not_found", "method_not_allowed", "internal_error"}


# C. Middleware, on isolated applications

import logging  # noqa: E402
import uuid  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.middleware import LOGGER_NAME, configure_logger, install_middleware, middleware_chain  # noqa: E402

ORIGIN = "http://localhost:5173"


class Records(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record.getMessage())


@pytest.fixture
def logs():
    logger = configure_logger("INFO")
    handler = Records()
    logger.addHandler(handler)
    yield handler.records
    logger.removeHandler(handler)


def isolated_app(max_body_bytes=100, cors=(ORIGIN,)):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, exception_handlers=api_errors.EXCEPTION_HANDLERS)

    @app.post("/echo")
    def echo(body: SetRequest):
        return {"n": len(body.words)}

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError(f"failure with {PRIVATE}")

    @app.get("/oserror")
    def oserror():
        raise OSError(f"disk {PRIVATE}")

    @app.get("/stream")
    def stream():
        def chunks():
            yield b"partial"
            raise RuntimeError(f"late {PRIVATE}")
        return StreamingResponse(chunks(), media_type="text/plain")

    install_middleware(app, max_body_bytes=max_body_bytes, cors_origins=cors, logger=logging.getLogger(LOGGER_NAME))
    return app


def assert_request_id(response):
    values = response.headers.get_list("x-request-id")
    assert len(values) == 1
    assert uuid.UUID(values[0]).version == 4
    return values[0]


def no_markers(*texts):
    return not any(marker in text for marker in MARKERS for text in texts)


def test_effective_middleware_order():
    assert middleware_chain(isolated_app()) == [
        "ServerErrorMiddleware", "ExceptionTelemetryMiddleware", "RequestContext", "CORSMiddleware", "ErrorBoundary",
        "BodyLimit", "ExceptionMiddleware", "AsyncExitStackMiddleware"]
    assert "CORSMiddleware" not in middleware_chain(isolated_app(cors=()))


def test_request_id_is_server_generated_and_on_every_response():
    client = TestClient(isolated_app())
    responses = [client.get("/ok", headers={"X-Request-ID": "client-chosen"}), client.get("/nope"), client.post("/ok"),
                 client.post("/echo", json={"words": 1}), client.get("/boom"),
                 client.post("/echo", content=b"x" * 200, headers={"content-type": "application/json"}),
                 client.options("/echo", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"})]
    assert [r.status_code for r in responses] == [200, 404, 405, 422, 500, 413, 200]
    ids = [assert_request_id(r) for r in responses]
    assert "client-chosen" not in ids and len(set(ids)) == len(ids)
    for response, request_id in zip(responses[1:6], ids[1:6]):
        assert response.json()["request_id"] == request_id  # the same ID in the body as in the header


def test_unexpected_errors_become_a_generic_500_with_cors_and_safe_logs(logs):
    client = TestClient(isolated_app())
    for path in ("/boom", "/oserror"):
        response = client.get(path, headers={"Origin": ORIGIN})
        assert response.status_code == 500
        assert response.json() == {"request_id": response.headers["x-request-id"], "code": "internal_error",
                                   "message": "Internal error.", "details": {}}
        assert response.headers["access-control-allow-origin"] == ORIGIN
        assert no_markers(response.text, str(response.headers))
    errors = [line for line in logs if line.startswith("internal error")]
    assert len(errors) == 2 and "exception=RuntimeError" in errors[0] and "exception=OSError" in errors[1]
    assert "function=boom" in errors[0] and "module=test_api" in errors[0]
    assert all("interrupted" not in line for line in logs)  # an OSError of the application is not a disconnect
    assert no_markers(*logs)


def test_not_found_and_method_not_allowed():
    client = TestClient(isolated_app())
    response = client.get(f"/{PRIVATE}?q={PASSWORD}")
    assert (response.status_code, response.json()["code"]) == (404, "not_found")
    response = client.delete("/ok")
    assert (response.status_code, response.json()["code"], response.headers.get("allow")) == (405, "method_not_allowed", "GET")
    assert no_markers(response.text)


def test_validation_errors_do_not_echo_input(logs):
    client = TestClient(isolated_app(max_body_bytes=10_000))
    cases = [
        client.post("/echo", json={"words": ["casa"], SECRET_FIELD: PASSWORD}),
        client.post("/echo", json={"words": PRIVATE}),
        client.post("/echo", json={"words": [PRIVATE, 7]}),
        client.post("/echo", content=f'{{"words": ["{PRIVATE}"'.encode(), headers={"content-type": "application/json"}),
        client.post("/echo", content=f'{{"words": ["{PRIVATE}"]}}'.encode()),  # no Content-Type
    ]
    for response in cases:
        assert response.status_code == 422 and response.json()["code"] == "request_invalid"
        assert no_markers(response.text, str(response.headers))
        assert all(set(error) == {"loc", "type"} for error in response.json()["details"]["errors"])
    assert cases[0].json()["details"]["errors"] == [{"loc": ["body", "<extra>"], "type": "extra_forbidden"}]
    assert cases[3].json()["details"]["errors"][0]["type"] == "json_invalid"
    assert cases[4].json()["details"]["errors"][0]["type"] == "model_attributes_type"
    assert no_markers(*logs)


def body_of(size):
    """A valid SetRequest JSON body of exactly `size` bytes."""
    head, tail = b'{"words":["', b'"]}'
    return head + b"a" * (size - len(head) - len(tail)) + tail


def test_body_limit_boundaries_and_contract():
    client = TestClient(isolated_app(max_body_bytes=100))
    json_header = {"content-type": "application/json"}
    assert client.post("/echo", content=body_of(99), headers=json_header).status_code == 200
    assert client.post("/echo", content=body_of(100), headers=json_header).status_code == 200  # exactly the limit
    for response in (client.post("/echo", content=body_of(101), headers={**json_header, "Origin": ORIGIN}),
                     client.post("/echo", content=iter([body_of(101)[:50], body_of(101)[50:]]), headers={**json_header, "Origin": ORIGIN}),
                     client.request("GET", "/ok", content=b"x" * 101, headers={"Origin": ORIGIN})):
        assert response.status_code == 413
        assert response.json() == {"request_id": assert_request_id(response), "code": "payload_too_large",
                                   "message": "The request body is too large.", "details": {"max_bytes": 100}}
        assert response.headers["connection"] == "close"
        assert response.headers["access-control-allow-origin"] == ORIGIN
    assert client.get("/ok").status_code == 200  # no body
    response = client.post("/echo", content=b'{"words": [', headers=json_header)
    assert (response.status_code, response.json()["code"]) == (422, "request_invalid")  # invalid JSON within the limit


def test_chunked_body_is_counted_without_content_length():
    client = TestClient(isolated_app(max_body_bytes=100))

    def chunks(total):
        body = body_of(total)
        for start in range(0, len(body), 7):
            yield body[start:start + 7]

    response = client.post("/echo", content=chunks(100), headers={"content-type": "application/json"})
    assert response.status_code == 200 and response.request.headers.get("transfer-encoding") == "chunked"
    response = client.post("/echo", content=chunks(5000), headers={"content-type": "application/json"})
    assert response.status_code == 413 and "content-length" not in response.request.headers


def run_asgi(app, method, path, messages, headers=(), fail_send=None):
    """Call the ASGI app directly. `messages` are returned by receive in order; afterwards receive waits briefly."""
    sent = []
    queue = list(messages)

    async def receive():
        if queue:
            return queue.pop(0)
        await asyncio.sleep(WAIT)
        return {"type": "http.disconnect"}

    async def send(message):
        if fail_send and message["type"] == fail_send:
            raise OSError("connection reset")
        sent.append(message)

    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"}, "http_version": "1.1", "method": method,
             "scheme": "http", "path": path, "raw_path": path.encode(), "root_path": "", "query_string": b"",
             "headers": [(b"host", b"testserver"), *headers], "client": ("127.0.0.1", 50000), "server": ("127.0.0.1", 80)}
    asyncio.run(asyncio.wait_for(app(scope, receive, send), WAIT))
    return sent


def test_client_disconnect_while_reading_is_an_interrupted_request(logs):
    app = isolated_app(max_body_bytes=1000)
    sent = run_asgi(app, "POST", "/echo", [{"type": "http.request", "body": b'{"words":', "more_body": True},
                                           {"type": "http.disconnect"}], headers=[(b"content-type", b"application/json")])
    # 3B.7.2-R1: BodyLimit reads the body first; on a disconnect nothing reaches the route and nothing is sent
    # (before, the route's own read produced a 400 that a real server discarded).
    assert sent == []
    assert any("interrupted=yes" in line for line in logs)
    assert not any(line.startswith("internal error") for line in logs)


def test_oserror_while_sending_is_not_an_internal_error(logs):
    sent = run_asgi(isolated_app(), "GET", "/ok", [{"type": "http.request", "body": b""}], fail_send="http.response.start")
    assert sent == []  # nothing else is attempted
    assert any(line.startswith("client connection failed") for line in logs)
    assert any("interrupted=yes" in line for line in logs)
    assert not any(line.startswith("internal error") for line in logs)


def test_error_after_the_response_started_sends_no_second_response(logs):
    sent = run_asgi(isolated_app(), "GET", "/stream", [{"type": "http.request", "body": b""}])
    starts = [m for m in sent if m["type"] == "http.response.start"]
    assert len(starts) == 1 and starts[0]["status"] == 200
    bodies = [m for m in sent if m["type"] == "http.response.body"]
    assert [b.get("body") for b in bodies if b.get("body")] == [b"partial"]
    assert all(b.get("more_body", False) for b in bodies)  # never completed as if it were a valid response
    errors = [line for line in logs if line.startswith("internal error")]
    assert len(errors) == 1 and "response_started=yes" in errors[0]
    assert no_markers(*logs)


def test_logger_configuration_is_idempotent(logs):
    logger = logging.getLogger(LOGGER_NAME)
    root_handlers = list(logging.getLogger().handlers)
    for level in ("INFO", "WARNING", "INFO"):
        configure_logger(level)
    own = [h for h in logger.handlers if getattr(h, "_diverge", False)]
    assert len(own) == 1 and logger.propagate is False and logger.level == logging.INFO
    assert logging.getLogger().handlers == root_handlers
    clients = [TestClient(isolated_app()) for _ in range(3)]
    for client in clients:
        client.get("/ok")
    request_lines = [line for line in logs if line.startswith("request ")]
    assert len(request_lines) == 3  # one line per request, however many applications exist
    assert all("route=/ok" in line and "status=200" in line for line in request_lines)


def test_request_log_never_contains_the_url_or_query(logs):
    client = TestClient(isolated_app())
    client.get(f"/{PRIVATE}?token={PASSWORD}")
    client.request("PRIVATEMETHOD", "/ok")
    assert any("route=<unmatched>" in line for line in logs)
    assert any("method=<other>" in line for line in logs)
    assert no_markers(*logs) and not any("PRIVATEMETHOD" in line for line in logs)


# C2. BodyLimit applies to every request body, even when the route never reads it

from app.api.middleware import BodyLimit, ErrorBoundary, RequestContext  # noqa: E402


def request_messages(*chunks):
    return [{"type": "http.request", "body": c, "more_body": i < len(chunks) - 1} for i, c in enumerate(chunks)]


class Recorder:
    """Inner ASGI app: reads the whole body (or none) and records what it saw."""

    def __init__(self, read=True):
        self.read, self.called, self.seen = read, False, []

    async def __call__(self, scope, receive, send):
        self.called = True
        while self.read:
            message = await receive()
            self.seen.append(message)
            if message["type"] != "http.request" or not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


class CountingReceive:
    """A receive that serves the given messages and records how many times it was called."""

    def __init__(self, messages, then_disconnect=False):
        self.messages, self.calls, self.then_disconnect = list(messages), 0, then_disconnect

    async def __call__(self):
        self.calls += 1
        if self.messages:
            return self.messages.pop(0)
        if self.then_disconnect:
            return {"type": "http.disconnect"}
        raise AssertionError("receive called after the body was consumed")


def stack(inner, limit, cors=True, logger=None):
    """RequestContext > CORS > ErrorBoundary > BodyLimit > inner, as installed by the application."""
    from starlette.middleware.cors import CORSMiddleware

    log = logger or logging.getLogger(LOGGER_NAME)
    app = BodyLimit(inner, max_body_bytes=limit)
    app = ErrorBoundary(app, logger=log)
    if cors:
        app = CORSMiddleware(app, allow_origins=[ORIGIN], allow_methods=["GET", "POST"], expose_headers=["X-Request-ID"])
    return RequestContext(app, logger=log)


def call(app, method, path, receive, headers=()):
    sent = []

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "scheme": "http",
             "path": path, "raw_path": path.encode(), "root_path": "", "query_string": b"",
             "headers": [(b"host", b"testserver"), (b"origin", ORIGIN.encode()), *headers], "client": ("127.0.0.1", 1),
             "server": ("127.0.0.1", 80)}
    asyncio.run(asyncio.wait_for(app(scope, receive, send), WAIT))
    return sent, scope


def rejected_413(sent):
    start = sent[0]
    assert start["status"] == 413
    headers = {k.decode().lower(): v.decode() for k, v in start["headers"]}
    body = json.loads(b"".join(m.get("body", b"") for m in sent[1:]))
    assert body["code"] == "payload_too_large" and body["message"] == "The request body is too large."
    assert body["details"] == {"max_bytes": 100} and body["request_id"] == headers["x-request-id"]
    uuid.UUID(body["request_id"])
    assert headers["connection"] == "close"  # HTTP/1.1: the connection must not be reused
    assert headers["access-control-allow-origin"] == ORIGIN  # CORS also on the rejection
    return body


def test_get_without_content_length_is_counted_even_if_the_route_ignores_the_body():
    inner = Recorder(read=False)
    receive = CountingReceive(request_messages(b"a" * 60, b"b" * 40, b"c"))  # 101 bytes in three chunks
    sent, _ = call(stack(inner, 100), "GET", "/ok", receive)
    rejected_413(sent)
    assert not inner.called and receive.calls == 3  # stopped at the chunk that crossed the limit


@pytest.mark.parametrize("size, accepted", [(0, True), (99, True), (100, True), (101, False)])
def test_get_body_limit_is_inclusive_and_independent_of_the_route(size, accepted):
    inner = Recorder(read=False)
    chunks = [b"x" * min(40, size - start) for start in range(0, size, 40)] or [b""]
    sent, _ = call(stack(inner, 100), "GET", "/ok", CountingReceive(request_messages(*chunks)))
    assert (sent[0]["status"] == 200) is accepted and inner.called is accepted


def test_post_fragmented_within_and_over_the_limit():
    inner = Recorder()
    sent, _ = call(stack(inner, 100), "POST", "/echo", CountingReceive(request_messages(*[b"y" * 10] * 10)))
    assert sent[0]["status"] == 200 and sum(len(m["body"]) for m in inner.seen) == 100
    inner = Recorder()
    receive = CountingReceive(request_messages(*[b"y" * 10] * 11))
    sent, _ = call(stack(inner, 100), "POST", "/echo", receive)
    rejected_413(sent)
    assert not inner.called and receive.calls == 11


def test_content_length_over_the_limit_never_calls_receive_or_the_application():
    inner = Recorder()
    receive = CountingReceive([])
    for method in ("GET", "POST"):
        sent, _ = call(stack(inner, 100), method, "/x", receive, headers=[(b"content-length", b"101")])
        rejected_413(sent)
    assert receive.calls == 0 and not inner.called


def test_declared_size_within_the_limit_does_not_exempt_the_real_count():
    inner = Recorder()
    receive = CountingReceive(request_messages(b"a" * 60, b"b" * 60))  # announces 10 bytes, sends 120
    sent, _ = call(stack(inner, 100), "POST", "/echo", receive, headers=[(b"content-length", b"10")])
    rejected_413(sent)
    assert not inner.called


def test_a_single_chunk_larger_than_the_limit_is_not_stored_and_stops_the_reading():
    from app.api.errors import PayloadTooLarge

    inner = Recorder()
    box = BodyLimit(inner, max_body_bytes=100)
    receive = CountingReceive(request_messages(b"z" * 5000, b"never read"))

    async def run():
        with pytest.raises(PayloadTooLarge):
            await box({"type": "http", "headers": []}, receive, None)

    asyncio.run(run())
    assert receive.calls == 1 and not inner.called
    assert len(receive.messages) == 1  # the second chunk was never taken from the connection


def test_a_valid_body_is_replayed_unchanged_and_in_order():
    original = request_messages(b'{"words":', b' ["a",', b' "b"]}')
    inner = Recorder()
    receive = CountingReceive([dict(m) for m in original])
    sent, _ = call(stack(inner, 100), "POST", "/echo", receive)
    assert sent[0]["status"] == 200
    assert inner.seen == original  # same chunks, same order, same more_body flags
    assert b"".join(m["body"] for m in inner.seen) == b'{"words": ["a", "b"]}'
    assert [m["more_body"] for m in inner.seen] == [True, True, False]
    assert receive.calls == 3  # the original receive was consumed exactly once per message


def test_after_the_replay_receive_is_delegated_to_the_original():
    class Waits:
        async def __call__(self, scope, receive, send):
            await receive()
            self.next = await receive()  # after the body: the original receive (a disconnect)
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

    inner = Waits()
    call(stack(inner, 100), "GET", "/x", CountingReceive(request_messages(b""), then_disconnect=True))
    assert inner.next == {"type": "http.disconnect"}


def test_disconnect_while_reading_delivers_no_partial_body(logs):
    inner = Recorder()
    receive = CountingReceive(request_messages(b"partial " + PRIVATE.encode(), b"more")[:1], then_disconnect=True)
    sent, scope = call(stack(inner, 100), "POST", "/echo", receive)
    assert not inner.called and sent == []  # nothing delivered, nothing sent to a client that is gone
    assert scope["state"]["interrupted"] is True
    assert any("interrupted=yes" in line for line in logs) and not any(line.startswith("internal error") for line in logs)
    assert no_markers(*logs)


def test_http_stack_413_has_request_id_cors_and_close_for_every_method():
    client = TestClient(isolated_app(max_body_bytes=100))

    def chunks():
        for _ in range(5):
            yield b"q" * 30

    for method in ("GET", "POST", "PUT", "DELETE"):
        response = client.request(method, "/ok", content=chunks(), headers={"Origin": ORIGIN})
        assert response.status_code == 413, method
        assert response.json()["request_id"] == assert_request_id(response)
        assert response.headers["connection"] == "close" and response.headers["access-control-allow-origin"] == ORIGIN
    exact = client.request("GET", "/ok", content=iter([b"q" * 50, b"q" * 50]))
    assert exact.status_code == 200 and exact.json() == {"ok": True}


def test_preflight_options_does_not_reach_the_body_limit_but_other_options_do():
    inner = Recorder(read=False)
    app = stack(inner, 100)
    sent, _ = call(app, "OPTIONS", "/echo", CountingReceive([]), headers=[(b"access-control-request-method", b"POST")])
    assert sent[0]["status"] == 200 and not inner.called  # answered by CORS
    sent, _ = call(app, "OPTIONS", "/echo", CountingReceive(request_messages(b"o" * 101)))
    rejected_413(sent)  # a plain OPTIONS with a large body is subject to the limit


# D. The composed application (create_app, lifespan, the four endpoints)

from app import main as app_main  # noqa: E402
from app.engine import EngineConfigError  # noqa: E402  (the tests may use the engine; the API may not)
from app.main import create_app  # noqa: E402


class Factory:
    """Counts the embedders it builds."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.built = []

    def __call__(self):
        embedder = FakeEmbedder(**self.kwargs)
        self.built.append(embedder)
        return embedder


def settings(**fields):
    return AppSettings(**{"cors_origins": (ORIGIN,), **fields})


def application(factory=None, **fields):
    factory = factory or Factory()
    return create_app(settings(**fields), embedder_factory=factory), factory


def test_startup_builds_one_embedder_and_one_service_and_shutdown_closes_it(monkeypatch):
    closes = []

    class CountingService(AnalysisService):
        instances = []

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            CountingService.instances.append(self)

        def close(self):
            closes.append(self)
            super().close()

    monkeypatch.setattr(app_main, "AnalysisService", CountingService)
    app, factory = application()
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "ready"}
        client.post("/api/v1/pairs", json={"word_a": "casa", "word_b": "perro"})
        service = app.state.analysis_service
        assert len(factory.built) == 1 and CountingService.instances == [service]
        assert app.state.model_response.model_id == "fake/model"
    assert closes == [service] and service.status() is ServiceState.STOPPING


@pytest.mark.parametrize("error", [EngineConfigError("the pinned revision is not in the local cache"),
                                   OSError("model files missing"), RuntimeError("offline mode is not active")])
def test_a_model_that_cannot_load_stops_startup(error):
    def factory():
        raise error

    app = create_app(settings(), embedder_factory=factory)
    with pytest.raises(type(error)):
        with TestClient(app):
            pytest.fail("requests must not be accepted")
    assert not hasattr(app.state, "analysis_service")


def test_invalid_service_settings_or_metadata_stop_startup():
    app, factory = application(max_words=1)  # the service owns the range check
    with pytest.raises(ValueError):
        with TestClient(app):
            pytest.fail("requests must not be accepted")
    info = real_like_description()
    del info["model_id"]
    app = create_app(settings(), embedder_factory=Factory(info=info))
    with pytest.raises(ValueError):
        with TestClient(app):
            pytest.fail("requests must not be accepted")


def test_a_failure_after_the_service_exists_closes_it(monkeypatch):
    built = []

    class Recording(AnalysisService):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            built.append(self)

    def broken(info):
        raise ValueError("cannot build the public metadata")

    monkeypatch.setattr(app_main, "AnalysisService", Recording)
    monkeypatch.setattr(app_main.ModelResponse, "from_info", broken)
    app, _ = application()
    with pytest.raises(ValueError):
        with TestClient(app):
            pytest.fail("requests must not be accepted")
    assert len(built) == 1 and built[0].status() is ServiceState.STOPPING  # not left READY


def test_configuration_errors_prevent_creating_the_application(monkeypatch):
    monkeypatch.setenv("DIVERGE_LOG_LEVEL", "LOUD")
    with pytest.raises(SettingsError):
        create_app(embedder_factory=Factory())
    monkeypatch.setenv("DIVERGE_LOG_LEVEL", "INFO")
    monkeypatch.setenv("DIVERGE_MAX_WORDS", "5")
    app = create_app(embedder_factory=Factory())
    with TestClient(app) as client:
        assert client.get("/api/v1/model").json()["limits"] == {"max_words": 5, "max_input_tokens": 512}
        response = client.post("/api/v1/sets", json={"words": ["uno", "dos", "tres", "cuatro", "cinco", "seis"]})
        assert response.json()["details"] == {"max_words": 5, "received_at_least": 6}


def test_telemetry_stays_disabled_even_if_the_environment_asks_for_it(monkeypatch):
    monkeypatch.setenv("FASTAPI_OTEL_AUTO_CONFIGURE", "true")
    app, _ = application()
    assert {key: app._telemetry[key] for key in app_main.TELEMETRY} == app_main.TELEMETRY
    assert app._native_telemetry.enabled() is False
    assert (app.docs_url, app.redoc_url, app.openapi_url) == (None, None, None)


def test_application_identifies_itself_with_the_package_version():
    import re

    import app as package

    app, _ = application()
    assert re.fullmatch(r"\d+\.\d+\.\d+(a|b|rc)\d+", package.__version__)  # PEP 440 pre-release
    assert package.__version__ == "0.1.0b1"
    assert (app.title, app.version) == ("Diverge", package.__version__)


def test_health_reports_every_state():
    app, factory = application(factory=Factory(on_encode=raising(EngineConfigError("unexpected embeddings"))))
    with TestClient(app) as client:
        assert (client.get("/api/v1/health").status_code, client.get("/api/v1/health").json()) == (200, {"status": "ready"})
        assert client.post("/api/v1/pairs", json={"word_a": "casa", "word_b": "perro"}).status_code == 500
        response = client.get("/api/v1/health")
        assert (response.status_code, response.json()) == (503, {"status": "failed"})
        assert client.get("/api/v1/model").status_code == 200  # available while failed
        app.state.analysis_service.close()
        response = client.get("/api/v1/health")
        assert (response.status_code, response.json()) == (503, {"status": "stopping"})
        assert client.get("/api/v1/model").json()["model_id"] == "fake/model"
        assert factory.built[0].encode_calls == 1  # health and model never touch the embedder


def test_model_endpoint_returns_the_public_fields():
    app, _ = application()
    with TestClient(app) as client:
        body = client.get("/api/v1/model").json()
    assert body == ModelResponse.from_info(AnalysisService(FakeEmbedder()).model_info()).model_dump()
    assert "torch_threads" not in body and not any(key.startswith("expected") for key in body)


def test_pairs_and_sets_match_the_service():
    app, _ = application()
    reference = AnalysisService(FakeEmbedder())
    with TestClient(app) as client:
        pair = client.post("/api/v1/pairs", json={"word_a": " Casa", "word_b": "HOGAR"})
        words = ["casa", "hogar", "edificio", "nube"]
        result = client.post("/api/v1/sets", json={"words": words})
    assert pair.status_code == 200 and pair.json() == PairResponse.from_result(reference.analyze_pair(" Casa", "HOGAR")).model_dump()
    expected = reference.analyze_set(words)
    assert result.status_code == 200 and result.json() == SetResponse.from_result(expected).model_dump()
    assert result.json()["mean_distance"] == expected.analysis.mean_distance  # unscaled, exact
    assert result.json()["n_pairs"] == 6 and "distance_matrix" not in result.json()


def test_service_errors_through_http(logs):
    app, _ = application()
    with TestClient(app) as client:
        post = client.post
        # PRIVATE has digits and "_" (digit_or_symbol); "privadaxyz" is a valid word repeated in another case.
        response = post("/api/v1/sets", json={"words": [PRIVATE, "dos palabras", "privadaxyz", "PRIVADAXYZ", "x" * 511]})
        assert response.status_code == 422 and response.json()["code"] == "invalid_entries"
        assert response.json()["details"]["entries"] == [
            {"position": 1, "reasons": ["digit_or_symbol"], "tokens": 19, "max_tokens": 512},
            {"position": 2, "reasons": ["multiple_words"], "tokens": 14, "max_tokens": 512},
            {"position": 4, "reasons": ["duplicate"], "tokens": 12, "max_tokens": 512},
            {"position": 5, "reasons": ["exceeds_model_context"], "tokens": 513, "max_tokens": 512}]
        assert no_markers(response.text, str(response.headers))
        assert "privadaxyz" not in response.text.lower() and "dos palabras" not in response.text
        response = post("/api/v1/pairs", json={"word_a": PRIVATE, "word_b": PRIVATE})
        assert (response.status_code, response.json()["code"]) == (422, "invalid_entries") and no_markers(response.text)
        response = post("/api/v1/sets", json={"words": ["solitaria"]})
        assert (response.status_code, response.json()["code"], response.json()["details"]) == (422, "too_few_words", {})
        assert "solitaria" not in response.text
        response = post("/api/v1/sets", json={"words": [f"w{chr(97 + k // 26)}{chr(97 + k % 26)}" for k in range(33)]})
        assert (response.status_code, response.json()["code"]) == (422, "too_many_words")
        assert response.json()["details"] == {"max_words": 32, "received_at_least": 33}
        assert all("retry-after" not in r.headers for r in (response,))
    assert no_markers(*logs)
    assert any("operation=analyze_set entries=5 error=invalid_entries" in line for line in logs)
    assert not any("privadaxyz" in line.lower() for line in logs)


def test_busy_and_unavailable_through_http():
    entered, release = threading.Event(), threading.Event()

    def hold(texts):
        entered.set()
        assert release.wait(WAIT)

    app, factory = application(factory=Factory(on_encode=hold))
    with TestClient(app) as client:
        service = app.state.analysis_service
        holder = threading.Thread(target=service.analyze_pair, args=("casa", "perro"), daemon=True)
        holder.start()
        assert entered.wait(WAIT)
        response = client.post("/api/v1/pairs", json={"word_a": "sol", "word_b": "luna"})
        assert (response.status_code, response.json()["code"], response.headers.get("retry-after")) == (503, "analysis_busy", "1")
        release.set()
        holder.join(WAIT)
        service.close()
        response = client.post("/api/v1/sets", json={"words": ["uno", "dos"]})
        assert (response.status_code, response.json()["code"], response.json()["details"]) == (503, "service_unavailable",
                                                                                                {"state": "stopping"})
        assert "retry-after" not in response.headers


def test_engine_failure_is_a_generic_500_and_the_service_becomes_unavailable(logs):
    app, _ = application(factory=Factory(on_encode=raising(EngineConfigError(f"broken model {PRIVATE}"))))
    with TestClient(app) as client:
        response = client.post("/api/v1/pairs", json={"word_a": "casa", "word_b": "perro"}, headers={"Origin": ORIGIN})
        assert response.status_code == 500 and response.json()["code"] == "internal_error" and response.json()["details"] == {}
        assert response.headers["access-control-allow-origin"] == ORIGIN
        assert no_markers(response.text, str(response.headers)) and "EngineConfigError" not in response.text
        response = client.post("/api/v1/pairs", json={"word_a": "casa", "word_b": "perro"})
        assert (response.status_code, response.json()["details"]) == (503, {"state": "failed"})
    errors = [line for line in logs if line.startswith("internal error")]
    assert len(errors) == 1 and "exception=EngineConfigError" in errors[0] and "service_state=failed" in errors[0]
    assert no_markers(*logs)


def test_privacy_markers_never_appear_in_api_output(logs):
    app, _ = application(max_body_bytes=2048)
    bodies = [
        {"word_a": PRIVATE, "word_b": "x", SECRET_FIELD: PASSWORD},
        {"words": [PRIVATE, 3]},
        {"words": PRIVATE},
    ]
    with TestClient(app) as client:
        responses = [client.post("/api/v1/sets" if "words" in b else "/api/v1/pairs", json=b) for b in bodies]
        responses.append(client.post("/api/v1/pairs", content=json.dumps({"word_a": PASSWORD, "word_b": PRIVATE}).encode()))
        responses.append(client.post("/api/v1/sets", content=json.dumps({"words": [PRIVATE] * 300}).encode(),
                                     headers={"content-type": "application/json"}))
    assert [r.status_code for r in responses] == [422, 422, 422, 422, 413]
    for response in responses:
        assert no_markers(response.text, str(dict(response.headers)))
    assert no_markers(*logs)


def test_cors_policy():
    app, _ = application()
    with TestClient(app) as client:
        preflight = client.options("/api/v1/sets", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST",
                                                            "Access-Control-Request-Headers": "content-type"})
        assert preflight.status_code == 200 and preflight.headers["access-control-allow-origin"] == ORIGIN
        assert set(preflight.headers["access-control-allow-methods"].replace(" ", "").split(",")) == {"GET", "POST"}
        assert "content-type" in preflight.headers["access-control-allow-headers"].lower()
        assert "access-control-allow-credentials" not in preflight.headers
        assert_request_id(preflight)
        simple = client.get("/api/v1/health", headers={"Origin": ORIGIN})
        assert simple.headers["access-control-allow-origin"] == ORIGIN
        assert simple.headers["access-control-expose-headers"].lower() == "x-request-id"
        rejected = client.options("/api/v1/sets", headers={"Origin": "http://evil.test", "Access-Control-Request-Method": "POST"})
        assert rejected.status_code == 400 and "access-control-allow-origin" not in rejected.headers
        other = client.get("/api/v1/health", headers={"Origin": "http://evil.test"})
        assert "access-control-allow-origin" not in other.headers
    app, _ = application(cors_origins=())
    assert "CORSMiddleware" not in middleware_chain(app)


def test_api_modules_never_use_the_engine():
    for file in sorted((BACKEND / "app" / "api").glob("*.py")):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            assert not any(name == "app.engine" or name.startswith("app.engine.") for name in names), file.name
        assert "GraniteEmbedder" not in file.read_text(encoding="utf-8")
    users = [f.relative_to(BACKEND).as_posix() for f in (BACKEND / "app").rglob("*.py")
             if "GraniteEmbedder" in f.read_text(encoding="utf-8") and "engine" not in f.parts]
    assert users == ["app/main.py"]


def test_composed_application_middleware_order():
    app, _ = application()
    assert middleware_chain(app) == ["ServerErrorMiddleware", "ExceptionTelemetryMiddleware", "RequestContext",
                                     "CORSMiddleware", "ErrorBoundary", "BodyLimit", "ExceptionMiddleware",
                                     "AsyncExitStackMiddleware"]


# E. The interpretation field of /sets (3B.9)

from app.api import schemas as api_schemas  # noqa: E402
from app.api.schemas import SetInterpretationOut  # noqa: E402
from app.services import interpretation as interpretation_module  # noqa: E402
from app.services import interpret_set  # noqa: E402

INTERPRETATION_KEYS = ["flags", "max_distance", "max_pairs", "min_distance", "min_pairs", "n_above_mean", "n_at_mean",
                       "n_below_mean", "n_max_pairs", "n_min_pairs", "n_pairs", "notes", "precision_decimals", "range",
                       "version"]


def test_sets_include_the_interpretation_with_exactly_the_contract_fields():
    app, _ = application()
    with TestClient(app) as client:
        body = client.post("/api/v1/sets", json={"words": ["guerra", "paz", "noche", "martillo", "ciencia"]}).json()
    assert sorted(body) == ["closest", "interpretation", "mean_distance", "model", "most_distant", "n_pairs", "n_words",
                            "pairs", "words"]
    interpretation = body["interpretation"]
    assert sorted(interpretation) == INTERPRETATION_KEYS
    assert interpretation["version"] == 1 and interpretation["precision_decimals"] == 4 and interpretation["n_pairs"] == 10
    assert interpretation["notes"] == ["relative_to_this_set", "no_reference_distribution", "mean_is_experimental"]
    assert all(sorted(ref) == ["i", "j"] for ref in interpretation["min_pairs"] + interpretation["max_pairs"])
    assert not any(isinstance(value, str) for key, value in interpretation.items() if key not in ("flags", "notes"))


def test_the_interpretation_matches_the_response_it_belongs_to():
    app, _ = application()
    with TestClient(app) as client:
        body = client.post("/api/v1/sets", json={"words": ["casa", "hogar", "edificio", "nube", "sol"]}).json()
    it, pairs = body["interpretation"], body["pairs"]
    distances = [p["distance"] for p in pairs]
    assert (it["min_distance"], it["max_distance"]) == (min(distances), max(distances))
    assert it["range"] == it["max_distance"] - it["min_distance"]
    assert (it["min_pairs"][0]["i"], it["min_pairs"][0]["j"]) == (body["closest"]["i"], body["closest"]["j"])
    assert (it["max_pairs"][0]["i"], it["max_pairs"][0]["j"]) == (body["most_distant"]["i"], body["most_distant"]["j"])
    assert it["n_above_mean"] + it["n_below_mean"] + it["n_at_mean"] == body["n_pairs"]
    assert it["n_pairs"] == body["n_pairs"]
    listed = {(ref["i"], ref["j"]) for ref in it["min_pairs"] + it["max_pairs"]}
    assert all(0 <= i < j < body["n_words"] for i, j in listed)


def test_the_response_equals_the_service_plus_the_pure_function():
    app, _ = application()
    reference = AnalysisService(FakeEmbedder())
    words = ["casa", "hogar", "edificio", "nube"]
    with TestClient(app) as client:
        body = client.post("/api/v1/sets", json={"words": words}).json()
    expected = reference.analyze_set(words)
    assert body["interpretation"] == SetInterpretationOut.from_interpretation(interpret_set(expected)).model_dump()


def test_pairs_health_and_model_responses_are_unchanged():
    app, _ = application()
    with TestClient(app) as client:
        pair = client.post("/api/v1/pairs", json={"word_a": "casa", "word_b": "perro"}).json()
        model = client.get("/api/v1/model").json()
        health = client.get("/api/v1/health").json()
    assert sorted(pair) == ["distance", "model", "similarity", "word_a", "word_b"]
    assert "interpretation" not in model and sorted(health) == ["status"]


def test_serialization_of_the_interpretation_schema():
    out = SetInterpretationOut.from_interpretation(interpret_set(AnalysisService(FakeEmbedder()).analyze_set(["uno", "dos", "tres"])))
    dumped = json.loads(out.model_dump_json())
    assert sorted(dumped) == INTERPRETATION_KEYS
    assert SetInterpretationOut.model_validate(dumped) == out
    with pytest.raises(ValidationError):
        SetInterpretationOut.model_validate({**dumped, "extra": 1})
    with pytest.raises(ValidationError):
        SetInterpretationOut.model_validate({**dumped, "flags": ["not_a_code"]})


def test_the_schema_codes_match_the_service_codes():
    from typing import get_args

    assert set(get_args(api_schemas.InterpretationFlag)) == set(interpretation_module.FLAGS)
    assert set(get_args(api_schemas.InterpretationNote)) == set(interpretation_module.NOTES)


def test_a_failing_interpretation_is_a_generic_500_and_leaves_the_service_ready(monkeypatch, logs):
    from app.api import routes

    def failing(result):
        raise interpretation_module.InterpretationError(f"inconsistent {PRIVATE}")

    monkeypatch.setattr(routes, "interpret_set", failing)
    app, _ = application()
    with TestClient(app) as client:
        response = client.post("/api/v1/sets", json={"words": ["casa", "hogar", "sol"]})
        assert response.status_code == 500
        assert response.json() == {"request_id": response.headers["x-request-id"], "code": "internal_error",
                                   "message": "Internal error.", "details": {}}
        assert "words" not in response.json() and no_markers(response.text, str(response.headers))
        assert client.get("/api/v1/health").json() == {"status": "ready"}  # an interpretation failure is not a service failure
        monkeypatch.undo()
        assert client.post("/api/v1/sets", json={"words": ["casa", "hogar", "sol"]}).status_code == 200
    errors = [line for line in logs if line.startswith("internal error")]
    assert len(errors) == 1 and "exception=InterpretationError" in errors[0] and no_markers(*logs)


def test_the_interpretation_runs_after_the_exclusive_section_of_the_service(monkeypatch):
    from app.api import routes

    seen = {}
    app, _ = application()

    def spy(result):
        seen["analysis_lock_held"] = app.state.analysis_service._analysis_lock.locked()
        return interpret_set(result)

    monkeypatch.setattr(routes, "interpret_set", spy)
    with TestClient(app) as client:
        assert client.post("/api/v1/sets", json={"words": ["casa", "hogar", "sol"]}).status_code == 200
    assert seen == {"analysis_lock_held": False}
