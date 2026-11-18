"""Errors raised by the semantic engine."""

from __future__ import annotations


class EngineError(Exception):
    """Base class for engine errors."""


class EngineInputError(EngineError, ValueError):
    """Invalid words or vectors given to the engine. Never raised for a valid input.

    Raised directly for problems that are not the user's entries, for example invalid vectors in `distances`.
    Invalid user entries raise the subclass `EngineValidationError`.
    """


class EngineValidationError(EngineInputError):
    """The user's entries failed validation, before anything was encoded.

    `entries` holds one report per entry, valid or not, in entry order: nothing is dropped. `problem` is a stable code,
    `"invalid_entries"` or `"too_few_words"`. Existing code that catches `EngineInputError` keeps working.
    """

    INVALID_ENTRIES = "invalid_entries"
    TOO_FEW_WORDS = "too_few_words"

    def __init__(self, message: str, entries: tuple = (), problem: str = INVALID_ENTRIES) -> None:
        super().__init__(message)
        self.entries = tuple(entries)
        self.problem = problem

    @property
    def invalid(self) -> tuple:
        """The reports of the invalid entries only, in entry order."""
        return tuple(entry for entry in self.entries if not entry.eligible)


class EngineConfigError(EngineError, RuntimeError):
    """The loaded model does not match the configuration the engine expects."""
