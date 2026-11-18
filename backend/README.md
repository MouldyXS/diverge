# Diverge backend: semantic engine (stages 3A, 3A.1 and 3B.2)

The engine exists, in `app/engine/`, pure Python with no FastAPI imports, together with a service layer over it (`app/services/`, see [Service layer](#service-layer)) and a local HTTP API (`app/api/`, see [HTTP API](#http-api)). There is no user interface or persistence yet.

| Module | Role |
|---|---|
| `normalize.py` | `strip`, NFC, `casefold`, NFC |
| `validation/deterministic.py` | P0 format rules: `empty`, `multiple_words`, `digit_or_symbol`, `duplicate`; nothing is dropped |
| `validation/length.py` | Model-context check: token count of each normalized entry against the embedder's limit (`exceeds_model_context`) |
| `distances.py` | Cosine similarity and distance (`1 − cos`, in [0, 2]) in float64, no clipping; NumPy only |
| `embedder.py` | `ModelSpec`, the `Embedder` interface, and `GraniteEmbedder` (reference model, CPU, fp32, offline, batch size 32) |
| `analysis.py` | Pair analysis (main unit) and set analysis (all n(n − 1)/2 pairs; mean distance as an experimental indicator) |
| `protocol.py` | DAT7, historical and optional: first seven eligible words, index = mean distance × 100 |

## Dependencies

Run these commands from `backend/`, inside the project virtual environment (`.venv`, Python 3.12).

| File | Purpose |
|---|---|
| `requirements.txt` | Direct runtime dependencies of the engine and of the API layer, pinned to exact versions. It adds the PyTorch CPU index (`--extra-index-url https://download.pytorch.org/whl/cpu`) and pins `torch==2.15.0+cpu`, the CPU variant |
| `requirements-dev.txt` | Includes `requirements.txt` and adds the tools needed to run the tests: `pytest` and `httpx2` (used by Starlette's `TestClient`) |
| `environment.freeze.txt` | Output of `pip freeze --all` for the 60 distributions of the environment used during development and experimentation; a snapshot, not a lockfile and not the installation specification (that is `requirements.txt` and `requirements-dev.txt`) |

```powershell
python -m pip install -r requirements.txt
```

```powershell
python -m pip install -r requirements-dev.txt
```

- **Runtime.** Only direct dependencies are declared. `tokenizers` is explicit because its behavior takes part in token counting and in the model-context validation. `starlette` is pinned explicitly because FastAPI does not set an upper bound for it.
- **Transitive dependencies** (for example `scipy`, `anyio`, `pydantic-core`, `opentelemetry-api`) are not declared; they arrive through the packages above.
- **`environment.freeze.txt` is a snapshot, not a lock.** It is a snapshot of the environment used during development and experimentation, not a lockfile and not the installation specification (that is `requirements.txt` and `requirements-dev.txt`). It is not the list of direct dependencies, it does not record the wheels' hashes, and it must not be installed in place of `requirements.txt` or `requirements-dev.txt`.
- **No guarantee of identical numbers.** Installing from these files does not by itself guarantee results numerically identical to the DAT7 baseline. The tests marked `model` and `baseline` are what check that: they are deselected by default and run only with `--baseline`, with the private reference files in place (see [Tests](#tests)). A run of `pytest -m model` without `--baseline` does not check the baseline.
- **Status.** `fastapi`, `starlette`, `pydantic` and `uvicorn` are used by the HTTP API (see [HTTP API](#http-api)); the engine and the service layer import none of them.

## Service layer

`app/services/` holds `AnalysisService`, which sits between the engine and a future API. It imports no HTTP library (FastAPI, Starlette, Pydantic, Uvicorn, httpx2) and no torch; it is tested with synthetic embedders in `tests/test_analysis_service.py`. The HTTP API uses it as its only access to the model (see [HTTP API](#http-api)).

- **What it does.** `analyze_pair` and `analyze_set` call the engine's `analyze_pair` and `analyze_set` once and return the engine's result objects unchanged, with the model identity (`ModelRef`: `model_id`, `declared_revision`, `snapshot_revision`). `model_info()` returns the identity, the limits and `describe()` read once at construction and frozen recursively. The engine keeps every semantic rule: normalization, P0, the token count and the distances.
- **Construction.** The service receives an embedder that is already loaded. It does not load models, does not call `ensure_offline()` and does no warm-up; whoever builds the application builds `GraniteEmbedder` first.
- **The embedder is used only through the service.** Its internal lock does not protect against direct calls to the embedder from elsewhere.
- **Limit: 32 entries per set** (`DEFAULT_MAX_WORDS`, a constructor argument). It counts every entry received, valid or not, before any is read. 32 entries give 496 pairs in one encoding batch, as in the DAT7 baseline; the policy above 32 words is still pending (D21 §10). The token limit per entry (512) belongs to the engine, and the HTTP body limit belongs to the API.
- **One analysis at a time.** A second analysis while one runs is rejected at once with `AnalysisBusy`; nothing is queued. The exclusive section covers the whole engine call, including the token count, because the tokenizer's truncation settings are shared by `count_tokens` and `encode`. The methods are synchronous: an API must call them from worker threads (for example FastAPI `def` endpoints).
- **States.** `ready` after construction. `failed` after an `EngineConfigError` during an analysis (the engine also reports any failure of `count_tokens` that way); that analysis propagates the error and later ones get `ServiceUnavailable`. `stopping` after `close()`, which is idempotent, does not wait for an analysis already admitted and is never replaced by `failed`. `status()` and `model_info()` answer in every state.
- **Errors without user text.** `EntriesRejected` (`invalid_entries` or `too_few_words`) keeps only positions, reason codes from a closed set (an unknown engine reason becomes `unrecognized_reason`) and token counts, and no reference to the engine error. `TooManyWords` gives `max_words` and `received_at_least`, a lower bound. The guarantee covers the exception objects; a traceback's local variables can still hold the request, so tracebacks of validation errors must not be logged.

## HTTP API

A local HTTP API v1 over `AnalysisService` (`app/api/`, composed in `app/main.py`). It has no authentication, no persistence and no background processing. `app/main.py` is the only application module that knows `GraniteEmbedder`; the API modules import the service layer, never the engine.

Run from `backend/`, inside the project environment. It listens on `127.0.0.1:8000` only, so other devices cannot reach it:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --lifespan on --loop asyncio --http h11 --no-access-log --timeout-graceful-shutdown 10
```

| Method and path | Result |
|---|---|
| `GET /api/v1/health` | `{"status": "ready"}` with 200; `failed` or `stopping` with 503. Never touches the model |
| `GET /api/v1/model` | Model identity (`model_id`, `declared_revision`, `snapshot_revision`, which is the snapshot resolved in the local cache, not a hash of the weights), selected configuration, limits (`max_words`, `max_input_tokens`) and versions. Built once at startup |
| `POST /api/v1/pairs` | `{"word_a": "...", "word_b": "..."}` gives the normalized words, `similarity`, `distance` and the model identity |
| `POST /api/v1/sets` | `{"words": [...]}` gives the normalized words, every pair (`i`, `j` are 0-based indexes into `words`), `mean_distance` (unscaled, an experimental indicator, not a measure of creativity), the closest and most distant pairs, an `interpretation` object (see below) and the model identity. The distance matrix is not sent: the pairs determine it |

- **Startup and shutdown.** One process, one model. Startup builds the embedder once (its constructor enforces offline mode and checks the model, see [Offline mode](#offline-mode)), then the service and the public metadata; any failure stops the server before it listens. On shutdown Uvicorn stops accepting connections and waits for those in progress (up to 10 s), then the service is closed. Uvicorn's exit code 3 appears both after a failed startup and after Ctrl+Break, so read the log ("Application startup complete", "Application startup failed", "Application shutdown complete") rather than the code alone.
- **Requests.** Strict JSON with `Content-Type: application/json`: unknown fields, a number instead of a string or a string instead of a list are rejected. The P0 rules, the token limit and the entry limit are not repeated in the schemas: the engine and the service apply them.
- **Errors.** Always `{"request_id", "code", "message", "details"}`, with a fixed English `message` per `code`; the interface translates from `code`. Codes: `request_invalid` (422, or 400 when the body cannot be read), `invalid_entries` and `too_few_words` (422, `details.entries` with `position` (1-based), `reasons`, `tokens`, `max_tokens`), `too_many_words` (422), `analysis_busy` (503, `Retry-After: 1`), `service_unavailable` (503), `payload_too_large` (413), `not_found` (404), `method_not_allowed` (405) and `internal_error` (500). No error repeats the text sent: validation errors keep only the Pydantic error type and a location in which unknown field names become `<extra>`.
- **Request ID.** Every response carries `X-Request-ID`, a UUID4 generated by the server (a client's value is ignored); error bodies repeat it.
- **Body limit.** `DIVERGE_MAX_BODY_BYTES` (default 262144 bytes). A larger body is rejected with 413 from its `Content-Length`, or while its bytes are counted when there is no `Content-Length` (chunked transfer). The 413 response closes the connection.
- **CORS.** Only the listed origins, methods `GET` and `POST`, header `Content-Type`, no credentials, and `X-Request-ID` exposed. CORS is not authentication.
- **Logging.** The `diverge.api` logger writes one line per request: request ID, method, route template (`<unmatched>` for unknown paths), status, duration, operation, number of entries and error code. It never writes bodies, words, query strings, exception messages or local variables; an internal error logs only the exception type, module, function, line and service state. Uvicorn's access log is disabled with `--no-access-log`.
- **Telemetry.** FastAPI's telemetry is disabled in code, even if `FASTAPI_OTEL_AUTO_CONFIGURE` is set; the interactive documentation and the OpenAPI schema are not served.

| Variable | Default | Meaning |
|---|---|---|
| `DIVERGE_MAX_WORDS` | unset (the service's default, 32) | Entries per set request; checked by `AnalysisService` |
| `DIVERGE_MAX_BODY_BYTES` | 262144 | Request body limit of the API |
| `DIVERGE_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed origins, comma separated; empty disables CORS; `*`, paths and trailing slashes are rejected |
| `DIVERGE_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`, for the `diverge.api` logger only |

An invalid value stops the application before it starts; the error names the variable without repeating its value. Tests: `tests/test_api.py`, with synthetic embedders and no model.

### Interpretation of a set

`POST /api/v1/sets` also returns `interpretation`, always present: **facts about the distribution of the set's distances, as numbers, pair indexes and codes, never sentences** (the interface writes the Spanish text). It is computed by `interpret_set` in `app/services/interpretation.py`, a pure function over the numbers the engine already produced: no model, no network, no state, standard library only. The route calls it after `analyze_set` has returned, outside the service's exclusive section; `AnalysisService`, the engine and `/pairs`, `/model` and `/health` are unchanged. The pair interpretation is written by the frontend from the values `/pairs` already returns.

| Field | Meaning |
|---|---|
| `version`, `precision_decimals` | Version of the rules, and the decimals at which values are compared (4, those the interface shows) |
| `n_pairs`, `min_distance`, `max_distance`, `range` | Number of pairs; exact smallest and largest distance and their difference |
| `min_pairs`, `max_pairs` | Pairs (`i`, `j`, as in `pairs`) equal to the smallest or largest distance **at four decimals**, at most five; the first is `closest` or `most_distant` |
| `n_min_pairs`, `n_max_pairs` | Total tied at each extreme, which may exceed the listed pairs |
| `n_above_mean`, `n_below_mean`, `n_at_mean` | Pairs above, below or equal to `mean_distance`, comparing the values rounded to four decimals |
| `flags` | Edge cases: `single_pair`, `all_equal_at_precision`, `all_exactly_equal`, `tie_at_min`, `exact_tie_at_min`, `tie_at_max`, `exact_tie_at_max` (a tie at the shown value is told apart from an exact tie) |
| `notes` | Fixed warnings by code: `relative_to_this_set`, `no_reference_distribution`, `mean_is_experimental` |

- **Rounding rule.** `Decimal(repr(x)).quantize(Decimal("0.0001"), ROUND_HALF_UP)`, which agrees with the four decimals the interface shows (`Intl.NumberFormat`) in all 201,716 values checked, boundary cases included; Python's `round(x, 4)` disagreed in 535 of them. A shared table of values is tested on both sides.
- **Order of the extremes.** The engine reports, among exactly tied pairs, the first as `closest` and the **last** as `most_distant`; the listed pairs follow the same rule, so the first listed is always the pair the interface already shows.
- **Errors.** An incoherent result (wrong number of pairs, invalid or repeated indexes, non-finite values, extremes that do not match) raises `InterpretationError`, which reaches the generic 500 `internal_error` with a sanitized log; the service state is untouched and no partial response is sent.
- **What it does not do.** No classification, no threshold, no percentile, no reference distribution, no clusters or isolated concepts (future work), and no statement about what the words mean. Tests: `tests/test_interpretation.py` and the interpretation tests of `tests/test_api.py`.

## Tests

Run from `backend/` with the project environment:

```powershell
..\.venv\Scripts\python.exe -B -m pytest -m "not model"
```

```powershell
..\.venv\Scripts\python.exe -B -m pytest -m model
```

```powershell
..\.venv\Scripts\python.exe -B -m pytest -m model --baseline
```

`--baseline` is an option of this project's `tests/conftest.py`. pytest only recognizes it when it starts in `backend/` (or is given the `tests` directory); a plain `pytest` run from the repository root answers "unrecognized arguments".

- **`-m "not model"`:** synthetic tests and offline checks that never load the model.
  - It needs no reference file and no model weights.
  - Two of these tests start a separate Python process that imports `huggingface_hub`, to check that the engine refuses to load when offline mode is not effectively active. They also check that torch is never imported.
- **`-m model`:** loads the reference model from the local Hugging Face cache, offline.
  - It checks the model identity and configuration and the tolerances the regression uses.
  - It also checks, in a separate process, that a normal start sets offline mode before the libraries load.
  - It checks the model-context boundary with the real tokenizer (511, 512 and 513 tokens) and that a 513-token input is rejected before `encode()`.
  - **It does not run the baseline reproduction.** The two tests marked `baseline` are deselected by default: pytest reports them as *deselected*, not as skipped.
- **`-m model --baseline`:** also selects the tests marked `baseline`.
  - They reproduce the DAT7 baseline: 14 indices, 294 pair similarities and distances, and the stored embeddings. They need the private reference files listed under [Reference files](#reference-files).
  - **If any reference file is missing, these tests fail. They never skip.** The message lists the missing paths.
- **What a successful run means.** A run without `--baseline`, including a plain `pytest -m model`, can exit successfully without the baseline having been compared. Only a successful run with `--baseline` and the reference files in place means the baseline was compared.
- **With no marker** and without `--baseline`, every test runs except the two marked `baseline`. With `--baseline`, all of them run, and the run needs the model and the reference files.
- **Counts.** The expected counts under this selection (369 tests with `-m "not model"`, 11 with `-m model`, 13 with `-m model --baseline`, 2 deselected) are historical figures carried over from the private research repository. They have not been recalculated for this distribution.

## Reference files

The baseline regression (the tests marked `baseline`) compares against the DAT7 baseline v0.1. Its files are private reference files and are **not included in this distribution**, so a clone does not have them. To run the regression you need your own copy of them, unchanged, at these paths relative to the repository root:

| File | SHA-256 |
|---|---|
| `experiments/results/semantic_baseline_dat7_v0.1/baseline_results.csv` | `55db0def52b51cd7cbe84ba7578c110a968bf6244624bd3c8c22d5d0671c9967` |
| `experiments/results/semantic_baseline_dat7_v0.1/pairwise_distances.csv` | `cf6cec877854441d36ff842345ae0b3d618346c348d443445dc4dc2746243681` |
| `experiments/results/semantic_baseline_dat7_v0.1/embeddings_dat7.npz` | `5bc34f9dcaa1a79bf23d0b0c651a9729fa548b52808be22a4595e2259d24d2ac` |
| `experiments/wordsets/curated/diverse_sets_v0.1.csv` | `6dbcf2d0f3736dfbfab51ba805f713040cdd19acaff916def2b60eaf8c2cf142` (computed after converting CRLF to LF); this word set is not included in this distribution either |

- **Availability:** the reproduction of the DAT7 baseline was verified against a private baseline that is not included in this distribution. The hashes above are kept as a record of what that baseline contained.
- **Do not regenerate them:** a new run would not be the preserved reference.
- **How they are checked:** the tests verify every hash before reading.

## Model context

An embedding model reads a limited number of tokens per input, and Sentence Transformers truncates longer inputs silently: with the reference model, an input of 513 tokens gives exactly the same vector as its first 512. The engine therefore rejects such inputs before encoding them.

- **Contract.** Every `Embedder` exposes `max_input_tokens` and `count_tokens(texts)`. The limit comes from the loaded model's effective configuration (for `GraniteEmbedder`, `model.max_seq_length`), not from a fixed number. It is 512 for the reference model, special tokens included; another model or configuration may have another limit.
- **Counting.** `GraniteEmbedder.count_tokens` uses the same tokenizer object as `encode()`, with special tokens, no truncation, no padding and no prompt, on the same normalized text. Counts are returned in input order. A tokenizer failure is an `EngineConfigError`, never a valid entry.
- **Equivalence.** At load time the embedder checks that the tokenizer is the module's processor, that there are no extra processing arguments or default prompt, that the tokenizer limit equals `max_input_tokens`, and, on two short probes through the public `preprocess` (tokenization only, no inference), that counting matches the encoding path and that a longer input would be truncated. The `model` tests check the exact boundary: 511 and 512 tokens are accepted, and their ids equal those of the encoding path; 513 tokens are rejected before `encode()`.
- **Limit.** Inclusive: `tokens <= max_input_tokens` is valid.
- **One validation per analysis.** `analyze_pair` and `analyze_set` apply the P0 rules and the token count once, combine the reasons per entry in order (P0 reasons first), and, if any entry is invalid, raise `EngineValidationError` before encoding anything. The whole request is rejected; nothing is encoded partially. `analyze_vectors` takes vectors and does no length check.
- **Errors.** `EngineValidationError` is a subclass of `EngineInputError`. It carries one `EntryReport` per entry (`index`, `position`, `entry`, `normalized`, `reasons`, `tokens`, `max_tokens`) and a `problem` (`invalid_entries` or `too_few_words`). Invalid vectors still raise a plain `EngineInputError`.
- **DAT7.** P0-invalid entries are skipped, as historically, and the selection is the first seven P0-eligible entries. Only those selected entries are counted. If one of them is above the context, the whole request is rejected with `EngineValidationError` before encoding: the entry is neither truncated nor skipped, and no later entry replaces it. Entries after the selection play no part. `select_dat7` without an embedder applies the P0 rules only.

## Offline mode

`GraniteEmbedder` sets `HF_HUB_OFFLINE=1` only if the variable is unset. It then checks the state huggingface_hub actually uses (`huggingface_hub.constants.is_offline_mode()`) **before** importing torch or Sentence Transformers.

huggingface_hub reads the variable only once, when it is first imported. If something imported it earlier without offline mode, or the variable is set to a false value, the engine raises `EngineConfigError` and loads nothing. In an application, create the embedder, or set `HF_HUB_OFFLINE=1`, before any other code imports huggingface_hub, transformers or sentence_transformers.

## Decisions still pending (D21 §10)

- Maximum words per request, and behavior above 32 words. Sentence Transformers splits a request larger than the batch size into several batches.
- Whether a pair encoded alone and the same pair inside a larger request give identical vectors. This is not assumed.
- Final policy for several pairs in one request.
- Presentation scale of the set indicator.
- Heuristic warnings, such as diacritic-only matches.
