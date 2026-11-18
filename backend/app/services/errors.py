"""Errors raised by the service layer. No HTTP: the future API maps `code` to a response.

Privacy: no service error holds text sent by the user. `EntriesRejected` keeps positions, reason codes from a closed
set and token counts only; it never keeps the engine's `EntryReport` objects, the engine's message (which quotes the
entries) or the engine exception itself (`__cause__` and `__context__` are None, see `analysis.py`). This guarantee
covers the exception object and its context chain; the local variables of the frames in a traceback can still hold the
request, so tracebacks of validation errors must not be logged.
"""

from __future__ import annotations

from dataclasses import dataclass

# The reasons the engine reports today (validation/deterministic.py and validation/length.py), plus the service's own
# code for any reason it does not recognize. An unknown engine reason is never copied: it could carry text.
ENGINE_REASONS = frozenset({"empty", "multiple_words", "digit_or_symbol", "duplicate", "exceeds_model_context"})
UNRECOGNIZED_REASON = "unrecognized_reason"
SAFE_REASONS = ENGINE_REASONS | {UNRECOGNIZED_REASON}

INVALID_ENTRIES = "invalid_entries"
TOO_FEW_WORDS = "too_few_words"


def _is_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


@dataclass(frozen=True)
class EntryIssue:
    """One invalid entry: its 1-based position, its reason codes and its token count. No text."""

    position: int
    reasons: tuple[str, ...]
    tokens: int | None
    max_tokens: int | None

    def __post_init__(self) -> None:
        if not _is_count(self.position) or self.position < 1:
            raise ValueError("position must be a positive integer")
        if not isinstance(self.reasons, tuple) or not self.reasons or not all(r in SAFE_REASONS for r in self.reasons):
            raise ValueError("reasons must be a non-empty tuple of safe reason codes")
        for value in (self.tokens, self.max_tokens):
            if value is not None and not _is_count(value):
                raise ValueError("token counts must be non-negative integers or None")


class ServiceError(Exception):
    """Base class of the service errors. `code` is a stable identifier for the API."""

    code = "service_error"


class EntriesRejected(ServiceError):
    """The entries failed the engine's validation (P0 rules or model context). Nothing was encoded.

    `code` is `invalid_entries` or `too_few_words`. `issues` holds the invalid entries only, in entry order; it is
    empty for `too_few_words`.
    """

    def __init__(self, code: str, issues: tuple[EntryIssue, ...] = ()) -> None:
        if code not in (INVALID_ENTRIES, TOO_FEW_WORDS):
            raise ValueError(f"unknown rejection code: {code!r}")
        issues = tuple(issues)
        if not all(isinstance(issue, EntryIssue) for issue in issues):
            raise TypeError("issues must be EntryIssue objects")
        super().__init__(f"{code}: {len(issues)} invalid entries" if code == INVALID_ENTRIES else code)
        self.code = code
        self.issues = issues


class TooManyWords(ServiceError):
    """More entries than the service accepts. `received_at_least` is a lower bound, not the exact size."""

    code = "too_many_words"

    def __init__(self, max_words: int, received_at_least: int) -> None:
        super().__init__(f"too many words: at most {max_words}, received at least {received_at_least}")
        self.max_words = max_words
        self.received_at_least = received_at_least


class AnalysisBusy(ServiceError):
    """Another analysis is running. The request was not queued."""

    code = "analysis_busy"

    def __init__(self) -> None:
        super().__init__("another analysis is running")


class ServiceUnavailable(ServiceError):
    """The service does not accept analyses in its current state (`failed` or `stopping`)."""

    code = "service_unavailable"

    def __init__(self, state) -> None:
        super().__init__(f"the service is {getattr(state, 'value', state)}")
        self.state = state


__all__ = [
    "ENGINE_REASONS", "INVALID_ENTRIES", "SAFE_REASONS", "TOO_FEW_WORDS", "UNRECOGNIZED_REASON", "AnalysisBusy",
    "EntriesRejected", "EntryIssue", "ServiceError", "ServiceUnavailable", "TooManyWords",
]
