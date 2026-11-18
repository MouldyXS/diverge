"""`AnalysisService`: coordinates the semantic engine for a future transport layer. No HTTP, no torch import.

The engine keeps every semantic rule: normalization, the P0 rules, the token count against the model context,
encoding and distances. The service adds what the engine does not decide:

* a limit on entries per request (`max_words`, counted before the P0 rules);
* admission of **one analysis at a time**: a second request is rejected at once with `AnalysisBusy`, never queued;
* a state, `ready`, `failed` or `stopping`;
* the model identity and metadata, read once at construction and frozen;
* errors without user text (`errors.py`).

Precondition: the embedder is used only through this service while the service lives. The internal lock does not
protect against direct calls to the embedder from elsewhere.

Synchronization. `_state_lock` guards the state and admission; `_analysis_lock` guards the whole engine call. The
validation is inside the exclusive section, not only `encode`: the tokenizer keeps truncation and padding settings
that `count_tokens` and `encode` change on every call. Lock order: `_state_lock` first, then `_analysis_lock`, always
acquired without blocking; `_state_lock` is also taken briefly while `_analysis_lock` is held (to mark `failed`), but
no path ever waits for `_analysis_lock`, so no wait cycle can form. `_analysis_lock` is acquired and released in the
same thread, in a `finally`. All methods are synchronous: a transport must call them from a worker thread (for
example a FastAPI `def` endpoint) and never from an event loop.
"""

from __future__ import annotations

import itertools
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from app.engine import (Embedder, EngineConfigError, EngineValidationError, PairAnalysis, SetAnalysis, analyze_pair,
                        analyze_set)

from .errors import (ENGINE_REASONS, INVALID_ENTRIES, TOO_FEW_WORDS, UNRECOGNIZED_REASON, AnalysisBusy, EntriesRejected,
                     EntryIssue, ServiceUnavailable, TooManyWords)

# 32 entries give 496 pairs and one encoding batch (`batch_size = 32`), the encoding condition of the DAT7 baseline.
# Larger sets would decide implicitly the policy above 32 words, which D21 section 10 keeps pending.
DEFAULT_MAX_WORDS = 32


class ServiceState(str, Enum):
    READY = "ready"
    FAILED = "failed"  # an EngineConfigError happened during an analysis; no further analyses
    STOPPING = "stopping"  # close() was called; final


@dataclass(frozen=True)
class ModelRef:
    """Model identity carried by every result.

    `declared_revision` is the revision requested in the model specification; `snapshot_revision` is the snapshot the
    local cache resolved for it (a directory name, not a hash of the weights), or None when the embedder does not
    report one. The declared revision is never used in its place.
    """

    model_id: str
    declared_revision: str
    snapshot_revision: str | None


@dataclass(frozen=True)
class PairResult:
    analysis: PairAnalysis  # the engine's object, unchanged
    model: ModelRef


@dataclass(frozen=True)
class SetResult:
    analysis: SetAnalysis  # the engine's object, unchanged; mean_distance is an experimental indicator
    model: ModelRef


@dataclass(frozen=True)
class ServiceLimits:
    max_words: int  # entries per request (service)
    max_input_tokens: int  # tokens per entry (model context, from the engine)


@dataclass(frozen=True)
class ModelInfo:
    ref: ModelRef
    limits: ServiceLimits
    description: Mapping[str, object]  # embedder.describe() without the `expected_*` keys, frozen recursively


def _freeze(value: object) -> object:
    """Read-only copy: mappings become MappingProxyType, lists and tuples become tuples; scalars are kept."""
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("metadata keys must be strings")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"unsupported metadata value of type {type(value).__name__}")


def _text(description: Mapping, key: str, required: bool) -> str | None:
    value = description.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"the embedder description needs a non-empty string {key!r}")
    return value


def _sanitize(error: EngineValidationError) -> tuple[str, tuple[EntryIssue, ...]]:
    """Codes and numbers only: never the reports, the entries or the engine's message."""
    code = TOO_FEW_WORDS if error.problem == TOO_FEW_WORDS else INVALID_ENTRIES
    issues = tuple(
        EntryIssue(position=int(report.position),
                   reasons=tuple(reason if reason in ENGINE_REASONS else UNRECOGNIZED_REASON for reason in report.reasons),
                   tokens=report.tokens, max_tokens=report.max_tokens)
        for report in error.entries if report.reasons
    )
    return code, issues


class AnalysisService:
    def __init__(self, embedder: Embedder, *, max_words: int = DEFAULT_MAX_WORDS) -> None:
        """Wrap an embedder that is already loaded. Loads nothing, encodes nothing, counts no tokens."""
        if not isinstance(embedder, Embedder):
            raise TypeError("embedder must implement the Embedder interface")
        if isinstance(max_words, bool) or not isinstance(max_words, int):
            raise TypeError("max_words must be an integer")
        if max_words < 2:
            raise ValueError("max_words must be at least 2")
        max_input_tokens = embedder.max_input_tokens
        if isinstance(max_input_tokens, bool) or not isinstance(max_input_tokens, int) or max_input_tokens <= 0:
            raise ValueError(f"invalid context limit reported by the embedder: {max_input_tokens!r}")
        description = embedder.describe()
        if not isinstance(description, Mapping):
            raise ValueError("embedder.describe() must return a mapping")
        self._model_ref = ModelRef(model_id=_text(description, "model_id", True),
                                   declared_revision=_text(description, "revision", True),
                                   snapshot_revision=_text(description, "snapshot_revision", False))
        self._model_info = ModelInfo(
            ref=self._model_ref,
            limits=ServiceLimits(max_words=max_words, max_input_tokens=max_input_tokens),
            description=_freeze({key: value for key, value in description.items() if not str(key).startswith("expected_")}),
        )
        self._embedder = embedder
        self._max_words = max_words
        self._state = ServiceState.READY
        self._state_lock = threading.Lock()
        self._analysis_lock = threading.Lock()

    def analyze_pair(self, word_a: str, word_b: str) -> PairResult:
        """Similarity and distance of one pair, through `engine.analyze_pair`."""
        if not isinstance(word_a, str) or not isinstance(word_b, str):
            raise TypeError("both words must be strings")
        return PairResult(analysis=self._run(analyze_pair, word_a, word_b), model=self._model_ref)

    def analyze_set(self, words: Sequence[str]) -> SetResult:
        """All pairs of a set, through `engine.analyze_set`, on an immutable snapshot of at most `max_words` entries.

        The limit counts every entry received, valid or not, and is checked before any element is read and before any
        lock is taken. If `words` changes while it is copied, which elements are captured is not guaranteed; the copy
        is bounded either way.
        """
        if isinstance(words, (str, bytes, bytearray)) or not isinstance(words, Sequence):
            raise TypeError("words must be a sequence of strings, not a single string")
        if len(words) > self._max_words:
            raise TooManyWords(self._max_words, self._max_words + 1)
        snapshot = tuple(itertools.islice(words, self._max_words + 1))
        if len(snapshot) > self._max_words:
            raise TooManyWords(self._max_words, self._max_words + 1)
        if not all(isinstance(word, str) for word in snapshot):
            raise TypeError("every word must be a string")
        return SetResult(analysis=self._run(analyze_set, snapshot), model=self._model_ref)

    def model_info(self) -> ModelInfo:
        """Identity, limits and metadata stored at construction. Available in every state; takes no lock."""
        return self._model_info

    def status(self) -> ServiceState:
        with self._state_lock:
            return self._state

    def close(self) -> None:
        """Stop accepting analyses. Idempotent; does not wait for, or interrupt, an analysis already admitted."""
        with self._state_lock:
            self._state = ServiceState.STOPPING

    def _run(self, operation, *args):
        with self._state_lock:  # admission, atomic with respect to close() and to the failed transition
            if self._state is not ServiceState.READY:
                raise ServiceUnavailable(self._state)
            if not self._analysis_lock.acquire(blocking=False):
                raise AnalysisBusy()
        rejected = None
        try:
            try:
                result = operation(self._embedder, *args)
            except EngineValidationError as error:
                rejected = error  # converted below, outside any `except` block
            except EngineConfigError:
                with self._state_lock:  # before the analysis lock is released, so no request enters a broken engine
                    if self._state is ServiceState.READY:
                        self._state = ServiceState.FAILED
                raise
        finally:
            self._analysis_lock.release()
        if rejected is not None:
            # No exception is being handled here, so neither __cause__ nor __context__ of the new error (nor of a
            # failure inside `_sanitize`) can refer to the engine error, whose message quotes the entries.
            rejection = _sanitize(rejected)
            del rejected
            raise EntriesRejected(*rejection)
        return result


__all__ = ["DEFAULT_MAX_WORDS", "AnalysisService", "ModelInfo", "ModelRef", "PairResult", "ServiceLimits", "ServiceState",
           "SetResult"]
